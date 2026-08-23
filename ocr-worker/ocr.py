"""
OCR de comprobantes (jpg/jpeg/png/pdf) 100% local: QR AFIP (preciso) + Tesseract (texto).

Pipeline por página:
  1. Auto-orientar imagen (corregir fotos giradas)
  2. QR AFIP via cv2 + pyzbar (múltiples estrategias)
  3. OCR via Tesseract (preprocesamiento CLAHE adaptativo)

Adaptado de ticket-extractor (mismo pipeline, sin Google Vision).
"""

import base64
import json
import logging
import urllib.parse

import cv2
import numpy as np
import fitz  # PyMuPDF
from PIL import Image

try:
    import pytesseract
    TESSERACT_OK = True
except ImportError:
    TESSERACT_OK = False

try:
    from pyzbar.pyzbar import decode as _pyzbar_decode
    PYZBAR_OK = True
except ImportError:
    PYZBAR_OK = False

logger = logging.getLogger(__name__)


# ── Lectura de archivos ───────────────────────────────────────────────────────

def pdf_a_imagenes(path: str, dpi: int = 300) -> list[np.ndarray]:
    doc = fitz.open(path)
    imagenes = []
    for page in doc:
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        imagenes.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    doc.close()
    return imagenes


def leer_paginas(path: str) -> list[np.ndarray]:
    """Lista de imágenes: una por página si es PDF, una sola si es imagen."""
    if path.lower().endswith(".pdf"):
        return pdf_a_imagenes(path)
    img = cv2.imread(path)
    if img is None:
        pil = Image.open(path).convert("RGB")
        img = np.array(pil)[:, :, ::-1]
    return [img]


# ── Auto-orientación ──────────────────────────────────────────────────────────

_ROTACIONES_CV2 = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def _detectar_rotacion_osd(img: np.ndarray) -> int | None:
    """Ángulo (0/90/180/270) que hay que rotar para enderezar el texto, según
    el OSD (orientation/script detection) de Tesseract.

    A diferencia de una heurística por varianza de proyección de filas, el
    OSD reconoce la forma de los caracteres — así que sí distingue 0° de
    180° (una fila de texto boca abajo tiene la misma varianza por fila que
    al derecho, con lo cual esa heurística podía "corregir" imágenes que ya
    estaban bien y dejarlas ilegibles). Devuelve None si Tesseract no pudo
    estimar la orientación (poco texto / imagen muy chica).
    """
    if not TESSERACT_OK:
        return None
    try:
        osd = pytesseract.image_to_osd(preprocesar(img), output_type=pytesseract.Output.DICT, config="--psm 0")
        return int(osd.get("rotate", 0)) % 360
    except Exception:
        return None


def _corregir_orientacion(img: np.ndarray) -> np.ndarray:
    """Detecta y corrige la orientación de la imagen (0/90/180/270 grados)."""
    angulo = _detectar_rotacion_osd(img)
    if not angulo:
        return img

    logger.info("Orientación detectada: %s° — corrigiendo", angulo)
    return cv2.rotate(img, _ROTACIONES_CV2[angulo])


# ── Preprocesamiento para OCR ─────────────────────────────────────────────────

def preprocesar(img: np.ndarray) -> Image.Image:
    """Escala de grises + CLAHE + upscale, para mejorar precisión de Tesseract."""
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gris.shape
    factor = 2200 / w
    if factor > 1.0:
        gris = cv2.resize(gris, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gris = clahe.apply(gris)
    gris = cv2.GaussianBlur(gris, (3, 3), 0)
    return Image.fromarray(gris)


# ── OCR ───────────────────────────────────────────────────────────────────────

def ocr_archivo(path: str) -> str:
    """Corre Tesseract sobre todas las páginas del archivo y concatena el texto."""
    if not TESSERACT_OK:
        raise RuntimeError("pytesseract no está instalado.")
    textos = []
    for img in leer_paginas(path):
        img = _corregir_orientacion(img)
        pil = preprocesar(img)
        textos.append(pytesseract.image_to_string(pil, lang="spa+eng", config="--psm 6 --oem 3"))
    return "\n".join(textos)


def procesar_archivo(path: str) -> tuple[str, dict | None]:
    """Lee el archivo una sola vez y extrae texto OCR + QR AFIP (si hay)."""
    if not TESSERACT_OK:
        raise RuntimeError("pytesseract no está instalado.")
    textos = []
    qr_datos = None
    for img in leer_paginas(path):
        img = _corregir_orientacion(img)
        pil = preprocesar(img)
        textos.append(pytesseract.image_to_string(pil, lang="spa+eng", config="--psm 6 --oem 3"))
        if qr_datos is None:
            for qr_string in _intentar_leer_qr(img):
                qr_datos = parsear_qr_afip(qr_string)
                if qr_datos:
                    break
    return "\n".join(textos), qr_datos


# ── QR AFIP ──────────────────────────────────────────────────────────────────

def _qr_detectar_variante(detector, variante: np.ndarray, resultados: list[str]):
    try:
        data, _, _ = detector.detectAndDecode(variante)
        if data and data not in resultados:
            resultados.append(data)
    except cv2.error:
        pass
    try:
        retval, decoded_list, _, _ = detector.detectAndDecodeMulti(variante)
        if retval:
            for d in decoded_list:
                if d and d not in resultados:
                    resultados.append(d)
    except cv2.error:
        pass


def _qr_pyzbar(variante: np.ndarray, resultados: list[str]):
    if not PYZBAR_OK:
        return
    try:
        for obj in _pyzbar_decode(variante):
            texto = obj.data.decode("utf-8", errors="ignore")
            if texto and texto not in resultados:
                resultados.append(texto)
    except Exception:
        pass


def _intentar_leer_qr(img: np.ndarray) -> list[str]:
    """Busca códigos QR con múltiples estrategias (original, umbral, 4 cuadrantes, rotaciones)."""
    detector = cv2.QRCodeDetector()
    resultados = []
    variantes = []

    variantes.append(img)

    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variantes.append(gris)

    umbral = cv2.adaptiveThreshold(
        gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    variantes.append(umbral)

    ampliada = cv2.resize(gris, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    variantes.append(ampliada)

    h, w = gris.shape
    cuadrantes = [
        gris[0:h // 2, 0:w // 2],
        gris[0:h // 2, w // 2:],
        gris[h // 2:, 0:w // 2],
        gris[h // 2:, w // 2:],
    ]
    for cq in cuadrantes:
        if cq.size == 0:
            continue
        variantes.append(cq)
        if cq.shape[0] > 100 and cq.shape[1] > 100:
            variantes.append(cv2.resize(cq, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))

    for angulo in (90, 180, 270):
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angulo, 1.0)
        rotada = cv2.warpAffine(gris, M, (w, h))
        variantes.append(rotada)

    for variante in variantes:
        _qr_detectar_variante(detector, variante, resultados)
        _qr_pyzbar(variante, resultados)
        if resultados:
            break

    return resultados


def parsear_qr_afip(qr_string: str) -> dict | None:
    """Decodifica el payload base64/JSON del QR AFIP/ARCA.

    Valida por contenido (campos esperados), no por dominio.
    """
    try:
        parsed = urllib.parse.urlparse(qr_string)
        params = urllib.parse.parse_qs(parsed.query)
        p = params.get("p", [None])[0]
        if not p:
            return None

        p += "=" * (-len(p) % 4)

        try:
            decoded = base64.b64decode(p)
        except Exception:
            try:
                decoded = base64.urlsafe_b64decode(p)
            except Exception:
                return None

        datos = json.loads(decoded.decode("utf-8"))

        campos_requeridos = {"ver", "fecha", "cuit", "ptoVta", "nroCmp"}
        if not campos_requeridos.issubset(datos.keys()):
            return None

        return datos

    except Exception:
        return None
