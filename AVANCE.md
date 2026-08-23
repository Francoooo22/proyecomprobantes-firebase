# Avance del proyecto

Registro de sesiones de trabajo. Complementa a `PROYECTO-COMPROBANTES.md` (el plan
original) y al `README.md` (cómo poner todo en marcha) — acá va la bitácora de qué
se hizo, qué se probó y qué falta.

## 2026-08-23

### Usuarios
- Alta de `studio.bp.mendoza@gmail.com` como **supervisor**, vía `scripts/create_usuario.py`
  con el service account (`~/.firebase-keys/proyecomprobantes-sa.json` en esta PC).
- Usuarios actuales en Firebase Auth: `franco@grupo.com` (supervisor) y
  `vendedor1@grupo.com` (vendedor demo, seed) + `studio.bp.mendoza@gmail.com` (supervisor,
  nuevo). Todavía **no hay vendedores reales** de las 4 empresas dados de alta.

### Feature: N° de File
Campo opcional `nro_file` agregado al formulario de subida (`dashboard.html`), guardado
en el documento de Firestore, visible en historial del vendedor y en la lista/modal/búsqueda
del panel supervisor. Commit `ce2d14f`.

### Bugs encontrados y corregidos (probando con 12 comprobantes reales)

Se corrió el pipeline completo (`ocr.py` + `parsers.py`) contra 12 capturas de pantalla
reales de comprobantes (Mercado Pago, NaranjaX, Banco Galicia, Santander, BNA,
transferencia bancaria genérica) para validar el parser antes de confiar en él para
conciliación. Aparecieron 4 bugs reales, todos corregidos y re-verificados contra la
misma tanda:

1. **`02d0d53`** — Modal de `admin.html` quedaba visible siempre (bug de CSS: `.modal`
   tenía `display:flex` sin una regla `[hidden]` que lo anule, así que el atributo
   `hidden` del HTML era ignorado por el navegador).

2. **`22b4e10`** — Montos mal calculados:
   - `_normalizar_monto` interpretaba el punto como decimal cuando no había coma
     (`"$142.200"` se leía como `$142,20` en vez de `$142.200`). Convención argentina:
     la coma es el separador decimal, el punto es de miles.
   - `_monto` probaba primero el patrón `$` suelto, así que un `$` de un número de
     cuenta/referencia anterior en el texto (ej. `"CC $ 0237-035286/0"`) ganaba sobre
     el importe real etiquetado como `"Importe:"` más adelante. Ahora los patrones
     con etiqueta (IMPORTE/TOTAL/MONTO) se prueban primero.

3. **`3c25a8e`** — Corrección de orientación rotaba comprobantes que **ya estaban
   derechos**. La heurística vieja (varianza de proyección de filas) no distingue 0°
   de 180° — una fila de texto boca abajo tiene la misma varianza que al derecho. 3 de
   los 12 comprobantes de la tanda de prueba ya estaban bien orientados y el algoritmo
   los rotaba igual, dejándolos ilegibles (uno de ellos ni se reconocía como
   comprobante). Reemplazado por el OSD (orientation/script detection) de Tesseract,
   que sí reconoce la forma de los caracteres. De paso se corrigió el método de
   rotación en sí (`cv2.rotate()` en vez de `warpAffine` con el canvas del tamaño
   original, que recortaba mal las esquinas al rotar 90°/270° en imágenes no
   cuadradas). Al destaparse el texto de esos 3 comprobantes apareció un caso nuevo
   del bug de montos (`"$ 80.000.00"`, el OCR confunde la coma con un punto) — mismo
   commit.

4. **`cf804ef`** — Campo `destino` siempre vacío en comprobantes de Mercado Pago. El
   regex buscaba `DESTINO`/`BENEFICIARIO`, pero los comprobantes reales de Mercado
   Pago usan la etiqueta `"Para"`. Agregado `PARA` y `CUENTA DESTINO` (esta última la
   usan apps como NaranjaX cuando el destino termina en una cuenta de Mercado Pago) +
   `re.IGNORECASE`.

**Resultado:** de los 12 comprobantes de prueba, los 12 quedan legibles y con monto
correcto donde el texto lo contiene (antes: 3 ilegibles + 2 montos mal calculados por
3-4 órdenes de magnitud).

### Setup de este entorno (WSL, esta PC)
- Tesseract 5.3.4 + `tesseract-ocr-spa` + `libzbar0` instalados (requería sudo).
- `ocr-worker/.venv` con las deps de `requirements.txt` instaladas, para poder probar
  el pipeline OCR localmente sin depender del server.
- Service account guardado en `~/.firebase-keys/proyecomprobantes-sa.json`.

### Pendiente
- **Confirmar criterio de CUIT/CBU**: hoy el parser captura los datos del *remitente*
  (quien paga), no del destinatario, porque toma la primera coincidencia en el texto y
  en estos recibos el bloque "De" aparece antes que "Para". Falta decidir si eso es lo
  que se quiere para conciliación.
- Cosmético menor: en comprobantes con etiqueta "Cuenta destino" (NaranjaX), queda un
  ícono mal-OCR'eado como letra suelta al principio del nombre destino (ej. `"S Cristian..."`).
- Correr `ocr-worker/server.py` en el server (todavía no está desplegado ahí).
- Activar el workflow de n8n (`n8n/workflow-procesar-comprobantes.json`).
- Dar de alta a los vendedores reales de las 4 empresas.
- Implementar la conciliación bancaria (matching por monto ±0.3%, últimos 4 dígitos,
  fecha+CUIT, many-to-one) — ver "Próximo paso propuesto" en el README.
