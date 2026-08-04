# Comprobantes — Web Firebase + OCR Tesseract + n8n

Sistema para subir comprobantes bancarios del grupo (Lantier, Aramendi, Wolf, Family Group),
procesarlos automáticamente con **OCR local (Tesseract + QR AFIP)** y conciliarlos.

Sin Google Vision: todo el OCR corre en un worker Python propio, igual que `ticket-extractor`.

## Arquitectura

```
Vendedor (celular/PC)                    Supervisor
     │                                      │
     ▼                                      ▼
  Web Firebase Hosting (login + subir + historial + admin)
     │ auth · storage · firestore
     ▼
  Firebase: Auth (email/pass) · Storage (imágenes) · Firestore (datos)
     │
     ▼
  n8n: trigger nuevo comprobante en Firestore
     │ HTTP POST
     ▼
  OCR worker (Python + Tesseract): descarga imagen → auto-orienta →
     QR AFIP + OCR → parsers BNA/MODO/Mercado Pago → actualiza Firestore
```

## Estructura del repo

```
├── PROYECTO-COMPROBANTES.md   Plan original
├── web/                       Firebase Hosting (frontend vanilla JS)
│   ├── firebase.json          Config de hosting/firestore/storage
│   ├── firestore.rules        Vendedor ve lo suyo; supervisor ve todo
│   ├── storage.rules          Imágenes <10MB
│   └── public/
│       ├── index.html         Login
│       ├── dashboard.html     Subir comprobante + historial (vendedor)
│       ├── admin.html         Panel supervisor (aprobar/rechazar)
│       ├── css/styles.css
│       └── js/                config.js, auth.js, app.js, upload.js, history.js, admin.js
├── ocr-worker/                Servicio OCR local
│   ├── ocr.py                 Pipeline: auto-orientación → QR AFIP → Tesseract (CLAHE)
│   ├── parsers.py             Detección BNA/MODO/Mercado Pago + extracción de campos
│   ├── server.py              Flask: POST /procesar {doc_id}
│   └── requirements.txt
├── n8n/workflow-procesar-comprobantes.json
└── scripts/create_usuario.py  Alta de vendedores/supervisores
```

## Puesta en marcha

### Estado actual (agosto 2026)
El proyecto Firebase **proyecomprobantes** ya está creado y desplegado:

- ✅ Proyecto Firebase: `proyecomprobantes` (nuevo, aislado de los otros proyectos)
- ✅ Hosting: https://proyecomprobantes.web.app
- ✅ Auth Email/Password habilitado
- ✅ Firestore base `(default)` con reglas + índices desplegados
- ✅ App web registrada y `config.js` apuntando al proyecto
- ✅ Usuarios semilla: `franco@grupo.com` (supervisor) y `vendedor1@grupo.com` (vendedor demo)
- ✅ Service account en `~/.firebase-keys/proyecomprobantes-sa.json`
- ✅ **Storage**: bucket `proyecomprobantes.firebasestorage.app` creado (plan Blaze)

### 1. Crear más usuarios
```bash
python3 -m venv .venv && .venv/bin/pip install firebase-admin
export FIREBASE_SA_PATH=/home/pc_wolf_05/.firebase-keys/proyecomprobantes-sa.json
.venv/bin/python scripts/create_usuario.py --email vendedor@grupo.com --password "xxxxx" \
  --nombre "Vendedor" --rol vendedor --sucursal "Aramendi"
```

### 3. OCR worker (en el server)```bash
cd ocr-worker
python3 -m venv venv && venv/bin/pip install -r requirements.txt
sudo apt install -y tesseract-ocr tesseract-ocr-spa libzbar0   # idiomas: spa+eng
export FIREBASE_SA_PATH=/ruta/a/service-account.json
venv/bin/gunicorn -b 0.0.0.0:5003 server:app
```
Probar: `curl http://127.0.0.1:5003/health`

### 4. n8n
1. Importar `n8n/workflow-procesar-comprobantes.json` en n8n.
2. Configurar la credencial **Google Firestore** (service account del mismo proyecto).
3. En el nodo **Llamar OCR worker**, cambiar `url` a la del server (`http://192.168.x.x:5003/procesar`).
4. Activar el workflow. Cada comprobante nuevo en Firestore se procesa solo.

## Flujo end-to-end
1. Vendedor entra → sube foto/PDF → queda en Storage + Firestore (`estado: pendiente`).
2. n8n detecta el doc → llama al worker → worker descarga, hace OCR + QR, parsea y actualiza
   (`estado: procesado`, `texto_ocr`, `datos_extraidos`).
3. Supervisor en `admin.html` aprueba o rechaza.

## Próximo paso propuesto
Conectar la **conciliación** (matching contra el banco) con los criterios del plan:
monto ±0.3%, últimos 4 dígitos, fecha+CUIT, many-to-one.
