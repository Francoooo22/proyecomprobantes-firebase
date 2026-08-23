"""
Servidor OCR local para el proyecto Comprobantes.

Descarga el comprobante de Firebase Storage, corre Tesseract + QR AFIP,
parsea los campos (BNA/MODO/Mercado Pago) y actualiza el documento en Firestore.

Endpoints:
  POST /procesar   Body: {"doc_id": "<id del comprobante>"}
  GET  /health

Env:
  FIREBASE_SA_PATH   Ruta al JSON de service account (o GOOGLE_APPLICATION_CREDENTIALS)
  FIREBASE_PROJECT_ID  Id del proyecto Firebase
  OCR_PORT           Puerto (default 5003)
"""

import json
import logging
import os
import tempfile

import requests
from flask import Flask, jsonify, request

import ocr as ocr_engine
import parsers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

_firebase = None


def _init_firebase():
    global _firebase
    if _firebase is not None:
        return _firebase

    from firebase_admin import credentials
    from google.cloud import firestore as gcfirestore
    from google.oauth2.service_account import Credentials

    sa_path = os.environ.get("FIREBASE_SA_PATH") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not sa_path or not os.path.exists(sa_path):
        raise RuntimeError("Falta FIREBASE_SA_PATH (service account JSON)")

    sa_credentials = Credentials.from_service_account_file(
        sa_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/datastore"],
    )
    database_id = os.environ.get("FIRESTORE_DATABASE", "(default)")
    _firebase = gcfirestore.Client(
        project=sa_credentials.project_id,
        credentials=sa_credentials,
        database=database_id,
    )
    logger.info("Firebase inicializado (db %s)", database_id)
    return _firebase


def _descargar(url: str, path: str):
    """Descarga el archivo desde la URL de Storage a un path local."""
    logger.info("Descargando %s", url[:80])
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


@app.post("/procesar")
def procesar():
    data = request.get_json(silent=True) or {}
    doc_id = data.get("doc_id")
    if not doc_id:
        return jsonify({"error": "falta doc_id"}), 400

    try:
        db = _init_firebase()
        doc_ref = db.collection("comprobantes").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({"error": "comprobante no encontrado"}), 404

        comprobante = doc.to_dict()
        url = comprobante.get("storage_url")
        if not url:
            return jsonify({"error": "sin storage_url"}), 400

        # Marcar en proceso
        doc_ref.update({"estado_ocr": "procesando"})

        with tempfile.NamedTemporaryFile(suffix="_comprobante", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            _descargar(url, tmp_path)

            texto, qr = ocr_engine.procesar_archivo(tmp_path)
            datos = parsers.parsear_con_qr(texto, qr)

            from google.cloud import firestore as gcfirestore
            doc_ref.update({
                "texto_ocr": texto,
                "datos_extraidos": datos,
                "estado_ocr": "ok",
                "estado": "procesado",
                "fecha_ocr": gcfirestore.SERVER_TIMESTAMP,
            })

            return jsonify({"ok": True, "doc_id": doc_id, "datos": datos})
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        logger.exception("Error procesando %s", doc_id)
        try:
            doc_ref.update({"estado_ocr": "fallo", "error_ocr": str(e)[:500]})
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500


@app.get("/health")
def health():
    return jsonify({"ok": True, "tesseract": ocr_engine.TESSERACT_OK})


@app.get("/")
def raiz():
    # Endpoint sin datos, solo para que monitor-services.sh (que pega a "/"
    # en todos los servicios) pueda confirmar que el proceso responde.
    return jsonify({"servicio": "comprobantes-ocr-worker"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("OCR_PORT", 5003)), debug=False)
