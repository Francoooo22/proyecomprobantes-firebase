"""
Parsers de comprobantes bancarios por patrón (regex) sobre el texto del OCR.

Detecta el tipo de comprobante (BNA, MODO, Mercado Pago) y extrae los campos
relevantes: monto, fecha, origen, destino, CBU/alias, CUIT, número de operación.

Los valores vienen de OCR, así que el matching es tolerante a ruido.
"""

import re

# ── Helpers ───────────────────────────────────────────────────────────────────

def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def _monto(texto: str) -> float | None:
    """Busca el primer monto en pesos en el texto. Tolerante a puntos y comas."""
    # $ 1.234,56 | $1234,56 | ARS 1.234,56 | 1.234,56
    patrones = [
        r"\$\s*([\d.]+(?:[.,]\d{2})?)",
        r"ARS\s*([\d.]+(?:[.,]\d{2})?)",
        r"IMPORTE\s*[:]?\s*\$?\s*([\d.]+(?:[.,]\d{2})?)",
        r"TOTAL\s*[:]?\s*\$?\s*([\d.]+(?:[.,]\d{2})?)",
        r"MONTO\s*[:]?\s*\$?\s*([\d.]+(?:[.,]\d{2})?)",
    ]
    for pat in patrones:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            return _normalizar_monto(m.group(1))
    return None


def _normalizar_monto(raw: str) -> float | None:
    """Convierte '1.234,56' o '1234.56' o '1.234' a float."""
    raw = raw.strip()
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return round(float(raw), 2)
    except ValueError:
        return None


def _fecha(texto: str) -> str | None:
    """dd/mm/aaaa o dd-mm-aaaa o dd.mm.aaaa. Devuelve formato ISO aaaa-mm-dd."""
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", texto)
    if not m:
        return None
    dia, mes, anio = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
    return f"{anio}-{mes}-{dia}"


def _cuit(texto: str) -> str | None:
    m = re.search(r"\b(\d{2}[-\s]?\d{8}[-\s]?\d)\b", texto)
    if m:
        return re.sub(r"[-\s]", "", m.group(1))
    m = re.search(r"\b(2[0-9]|3[0-9])[0-9]{9}\b", texto)
    return m.group(0) if m else None


def _cbu(texto: str) -> str | None:
    m = re.search(r"\b(\d{22})\b", texto)
    return m.group(1) if m else None


def _alias(texto: str) -> str | None:
    m = re.search(r"\b([a-z]{3,}\.[a-z]{3,}\.[a-z]{3,})\b", texto, re.IGNORECASE)
    return m.group(1) if m else None


def _nro_operacion(texto: str) -> str | None:
    m = re.search(r"(?:N[°º]?\s*(?:de\s+)?(?:OPERACION|OPERACIÓN|TRANSFERENCIA|OP)\s*[:.\s]*)([\d]{4,12})",
                  texto, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(CINV|CAJA|OP)\s*[\-\s]\s*(\d{4,12})\b", texto, re.IGNORECASE)
    return m.group(1) if m else None


# ── Detección de tipo ─────────────────────────────────────────────────────────

def detectar_tipo(texto: str) -> str:
    t = _limpiar(texto)
    if "MERCADO PAGO" in t.upper() or "MERCADOPAGO" in t.upper():
        return "mercado_pago"
    if "MODO" in t.upper() or "MODO>" in t.upper():
        return "modo"
    if "NACION" in t.upper() and "ARGENTINA" in t.upper():
        return "bna"
    if "BANCO" in t.upper() and "BNA" in t.upper():
        return "bna"
    return "generico"


# ── Parser principal ──────────────────────────────────────────────────────────

def extraer_datos(texto: str) -> dict:
    """Extrae los campos de un texto OCR. Devuelve dict con monto/fecha/etc."""
    tipo = detectar_tipo(texto)
    texto_limpio = _limpiar(texto)

    campos: dict = {
        "tipo": tipo,
        "monto": _monto(texto_limpio),
        "fecha": _fecha(texto_limpio),
        "cuit": _cuit(texto_limpio),
        "cbu": _cbu(texto_limpio),
        "alias": _alias(texto_limpio),
        "nro_operacion": _nro_operacion(texto_limpio),
    }

    # Origen / destino según el tipo
    if tipo == "bna":
        campos["origen"] = "BANCO DE LA NACION ARGENTINA"
        m = re.search(r"(?:DESTINO|BENEFICIARIO|A FAVOR DE)\s*[:.\n]*([A-ZÁÉÍÓÚÑ a-zñáéíóú]{3,40})", texto)
        if m:
            campos["destino"] = m.group(1).strip()
        m2 = re.search(r"CUENTA DESTINO\s*[:.\n]*([\d/]+)", texto)
        if m2:
            campos["cuenta_destino"] = m2.group(1).strip()
    elif tipo == "modo":
        m = re.search(r"(?:A\s+|ALIAS\s+|DESTINO|ENVIADO A)\s*[:.\n]*([A-Za-z0-9_.\-]{3,40})", texto)
        if m:
            campos["destino"] = m.group(1).strip()
        if campos["alias"]:
            campos["destino"] = campos["alias"]
    elif tipo == "mercado_pago":
        m = re.search(r"(?:A\s+|DESTINO|BENEFICIARIO)\s*[:.\n]*([A-ZÁÉÍÓÚÑ a-zñáéíóú]{3,40})", texto)
        if m:
            campos["destino"] = m.group(1).strip()

    # Quitar campos vacíos
    return {k: v for k, v in campos.items() if v not in (None, "", {})}


def parsear_con_qr(texto: str, qr: dict | None) -> dict:
    """Mezcla datos del OCR con los del QR AFIP (que son exactos cuando existen)."""
    datos = extraer_datos(texto)
    if not qr:
        return datos

    # El QR tiene los datos exactos del comprobante fiscal
    qr_datos = {
        "tipo_comprobante": qr.get("tipoCmp", ""),
        "pto_vta": qr.get("ptoVta", ""),
        "nro_comprobante": qr.get("nroCmp", ""),
        "cuit_emisor": qr.get("cuit", ""),
        "fecha_emision": qr.get("fecha", ""),
        "importe": qr.get("importe", ""),
        "moneda": qr.get("moneda", ""),
        "cae": qr.get("cae", ""),
        "cuit_comprador": qr.get("cuitComprador", ""),
    }
    # Priorizar QR cuando el OCR no encontró monto/fecha
    if not datos.get("monto") and qr_datos.get("importe"):
        try:
            datos["monto"] = _normalizar_monto(str(qr_datos["importe"]))
        except Exception:
            pass
    if not datos.get("fecha"):
        datos["fecha"] = qr_datos.get("fecha_emision")
    datos["qr_afip"] = {k: v for k, v in qr_datos.items() if v not in (None, "")}
    return datos
