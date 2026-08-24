"""
Parsers de comprobantes bancarios por patrón (regex) sobre el texto del OCR.

Detecta el tipo de comprobante (BNA, MODO, Mercado Pago) y extrae monto, fecha,
número de operación, y los datos de emisor/receptor por separado (nombre, CUIT,
cuenta/CBU/alias de cada lado).

Los valores vienen de OCR, así que el matching es tolerante a ruido.
"""

import re

# ── Helpers ───────────────────────────────────────────────────────────────────

def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def _monto(texto: str) -> float | None:
    """Busca el monto en pesos en el texto. Tolerante a puntos y comas.

    Los patrones con etiqueta (IMPORTE/TOTAL/MONTO) van primero porque son
    inequívocos; un "$" suelto puede aparecer antes en un número de cuenta
    o de referencia (ej. "CC $ 0237-035286/0") y no es el importe real.
    """
    patrones = [
        r"IMPORTE\s*[:]?\s*\$?\s*([\d.]+(?:[.,]\d{2})?)",
        r"TOTAL\s*[:]?\s*\$?\s*([\d.]+(?:[.,]\d{2})?)",
        r"MONTO\s*[:]?\s*\$?\s*([\d.]+(?:[.,]\d{2})?)",
        r"\$\s*([\d.]+(?:[.,]\d{2})?)",
        r"ARS\s*([\d.]+(?:[.,]\d{2})?)",
    ]
    for pat in patrones:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            return _normalizar_monto(m.group(1))
    return None


def _normalizar_monto(raw: str) -> float | None:
    """Convierte '1.234,56' / '1.234' / '3.101.600,00' / '80.000.00' a float.

    Convención argentina: la coma es el separador decimal, el punto es
    separador de miles — salvo que el último grupo separado por "." tenga
    exactamente 2 dígitos, en cuyo caso son centavos (típico cuando el OCR
    confunde la coma decimal con un punto, ej. "80.000.00" = $80.000,00,
    no $8.000.000). Un grupo de miles real siempre tiene 3 dígitos.
    """
    raw = raw.strip()
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "." in raw and len(raw.rsplit(".", 1)[1]) == 2:
        entero, centavos = raw.rsplit(".", 1)
        raw = entero.replace(".", "") + "." + centavos
    else:
        raw = raw.replace(".", "")
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


# ── Emisor / receptor ─────────────────────────────────────────────────────────
# Bank-agnóstico: en vez de un regex de "destino" por banco, se busca dónde
# empiezan los datos de cada lado (emisor = quien manda la plata, receptor =
# quien la recibe) y se extrae nombre/CUIT/cuenta de cada tramo por separado.
# Necesario porque hoy el CUIT/CBU "único" del parser viejo era en realidad
# siempre el del emisor (el bloque "De" aparece antes que "Para" en el texto),
# y a futuro pueden recibir plata en más de una cuenta propia.

# "De"/"Para" cuentan como etiqueta real solo si son (casi) todo el contenido
# de su línea — así no se confunden con la preposición normal ("Comprobante
# de transferencia", en cualquier parte del texto) ni con un "De" que es
# parte de un apellido ("Alejandro De Benedectis"): ninguna de las dos
# aparece sola en su línea, a diferencia de la etiqueta real del comprobante
# ("De:", "* De", "e Para").
_ETIQUETA_EMISOR = re.compile(
    r"(?i:DATOS\s+ORDENANTE|CUENTA\s+ORIGEN)|^.{0,3}?\bDE\b\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_ETIQUETA_RECEPTOR = re.compile(
    r"(?i:DATOS\s+BENEFICIARIO|TITULAR\s+CUENTA\s+DESTINO|CUENTA\s+DESTINO|DESTINATARIO|BENEFICIARIO)"
    r"|^.{0,3}?\bPARA\b\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Etiquetas que preceden directamente al nombre de una persona/empresa dentro
# de un bloque ya recortado (más específicas que las de arriba: evitan capturar
# "n° de referencia" como si fuera el nombre).
_ETIQUETA_NOMBRE = re.compile(
    r"(?i:TITULAR\s+CUENTA\s+DESTINO|TITULARIDAD|APELLIDO\s+Y\s+NOMBRE|CUENTA\s+ORIGEN|CUENTA\s+DESTINO"
    r"|DESTINATARIO|BENEFICIARIO)|^.{0,3}?\bDE\b\s*:?\s*$|^.{0,3}?\bPARA\b\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _bloques_emisor_receptor(texto: str) -> tuple[str, str]:
    """Recorta el texto en el tramo de datos del emisor y el del receptor.

    Cada tramo va desde su etiqueta hasta que empieza la del otro lado (o
    hasta el final del texto). Si no se encuentra una etiqueta, ese tramo
    queda vacío en vez de adivinar.
    """
    m_emisor = _ETIQUETA_EMISOR.search(texto)
    m_receptor = _ETIQUETA_RECEPTOR.search(texto)
    inicio_emisor = m_emisor.start() if m_emisor else None
    inicio_receptor = m_receptor.start() if m_receptor else None

    if inicio_emisor is not None and inicio_receptor is not None:
        if inicio_emisor < inicio_receptor:
            return texto[inicio_emisor:inicio_receptor], texto[inicio_receptor:]
        return texto[inicio_emisor:], texto[inicio_receptor:inicio_emisor]
    if inicio_emisor is not None:
        return texto[inicio_emisor:], ""
    if inicio_receptor is not None:
        return "", texto[inicio_receptor:]
    return "", ""


def _nombre_de_bloque(bloque: str) -> str | None:
    # [\s:.]* (no "\s*[:.\n]*") porque el separador entre etiqueta y nombre
    # puede ser "\n" pegado (De:\nJuan) o ": " con espacio (Titularidad: LAUKE) —
    # con \s* primero y [:.\n]* después, el espacio tras los dos puntos
    # quedaba sin consumir y la captura fallaba entera.
    # El grupo opcional de "Apellido y Nombre" salta ese sub-encabezado cuando
    # aparece entre la etiqueta y el valor real (formato de la app del BNA).
    # El grupo opcional siguiente salta un ícono mal-OCR'eado como letra suelta
    # (1-2 mayúsculas + espacio, ej. "S Cristian...", "NX Gustavo...") que
    # NaranjaX deja pegado antes del nombre en "Cuenta destino"/"Cuenta origen".
    m = re.search(
        r"(?:" + _ETIQUETA_NOMBRE.pattern + r")[\s:.]*(?:APELLIDO\s+Y\s+NOMBRE[\s:.]*)?"
        r"(?:[A-ZÑ]{1,2}\s+(?=[A-ZÁÉÍÓÚÑ]))?"
        r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ a-zñáéíóú]{2,59})",
        bloque,
        re.IGNORECASE | re.MULTILINE,
    )
    return m.group(1).strip() if m else None


def _cuenta_de_bloque(bloque: str) -> str | None:
    """CBU/CVU (22 dígitos) si hay; si no, alias; si no, un número de cuenta
    genérico tipo "4039028-3" (formato que usan los bancos para CA/CC)."""
    cbu = _cbu(bloque)
    if cbu:
        return cbu
    alias = _alias(bloque)
    if alias:
        return alias
    m = re.search(r"\b(\d[\d/\-]{4,20}\d)\b", bloque)
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
        "nro_operacion": _nro_operacion(texto_limpio),
    }

    # Emisor (quién manda la plata) y receptor (quién la recibe), cada uno con
    # su propio nombre/CUIT/cuenta — no un solo CUIT/CBU ambiguo como antes.
    bloque_emisor, bloque_receptor = _bloques_emisor_receptor(texto)
    if bloque_emisor:
        campos["emisor_nombre"] = _nombre_de_bloque(bloque_emisor)
        campos["emisor_cuit"] = _cuit(bloque_emisor)
        campos["emisor_cuenta"] = _cuenta_de_bloque(bloque_emisor)
    if bloque_receptor:
        campos["receptor_nombre"] = _nombre_de_bloque(bloque_receptor)
        campos["receptor_cuit"] = _cuit(bloque_receptor)
        campos["receptor_cuenta"] = _cuenta_de_bloque(bloque_receptor)

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
