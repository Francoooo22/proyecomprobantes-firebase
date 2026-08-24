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

### Emisor y receptor separados (`070d547`)

El usuario pidió capturar **nombre + cuenta del emisor Y del receptor por separado**
(no solo un CUIT/CBU ambiguo) porque a futuro pueden recibir plata en distintas cuentas
propias. Se reemplazaron los campos viejos `tipo`-específicos (`destino`/`origen`/
`cuenta_destino` de BNA/MODO/Mercado Pago) por una extracción bank-agnóstica:
`emisor_nombre`/`emisor_cuit`/`emisor_cuenta` y `receptor_nombre`/`receptor_cuit`/
`receptor_cuenta`. Busca dónde empiezan los datos de cada lado (etiquetas "De"/"Para"/
"Cuenta origen"/"Datos Ordenante"/"Datos Beneficiario"/etc.) y saca nombre+CUIT+cuenta
de cada tramo.

Dos bugs de regex encontrados en el camino (probando otra vez contra los mismos 12
comprobantes):
- Matchear "De"/"Para" sin exigir que fueran casi todo el contenido de su línea hacía
  que `"Comprobante de transferencia"` (preposición normal) o un apellido como
  `"Alejandro De Benedectis"` se confundieran con la etiqueta real del comprobante.
- El separador etiqueta→nombre (`\s*[:.\n]*`) no contemplaba "dos puntos + espacio"
  (ej. `"Titularidad: LAUKE SRL"`), solo funcionaba si el salto de línea venía pegado
  al `:`. Con `[\s:.]*` se arregló.

**Resultado:** 8 de 12 comprobantes con emisor Y receptor completos (antes: el campo
"emisor" no existía como tal, y "destino" nunca traía el remitente). Quedan débiles:
el que no tiene etiquetas "De"/"Para" explícitas (`122225`), el de tabla mezclada por
OCR (`122325`), y el de UI muy cargada de íconos (`122347`) — documentado como límite
conocido, no vale la pena seguir parchando casos cada vez más específicos con regex.

Frontend (`admin.js`/`history.js`) actualizado para mostrar `emisor_nombre`/
`receptor_nombre`/`receptor_cuenta` en vez de los campos viejos.

### Setup de este entorno (WSL, esta PC)
- Tesseract 5.3.4 + `tesseract-ocr-spa` + `libzbar0` instalados (requería sudo).
- `ocr-worker/.venv` con las deps de `requirements.txt` instaladas, para poder probar
  el pipeline OCR localmente sin depender del server.
- Service account guardado en `~/.firebase-keys/proyecomprobantes-sa.json`.

### Pendiente (actualizado 2026-08-24, ver sesión de abajo para detalle)
- ~~Cosmético NaranjaX~~ ✅ arreglado (`b10b82f`).
- ~~Correr `ocr-worker/server.py` en el server~~ ✅ corriendo en PM2, pero **falta el
  paso de nginx+ufw** (requiere sudo, no lo pude correr yo) — ver sesión de abajo.
- n8n: **no estaba instalado en el server** (se creía que sí). Imagen Docker
  descargándose, falta terminar pull + levantar contenedor + credenciales Firestore +
  primer login manual de Franco (owner account) + corregir puerto del OCR worker en
  el workflow (dice 5003, es 5004) + importar/activar.
- Dar de alta a los vendedores reales de las empresas/sucursales (ahora son 7:
  Grupo Lantier, Aramendi, Wolf, Family Group, HyT, Alce, Limite Vertical — no 4).
  Necesito nombres+emails de Franco, no los tengo.
- Conciliación bancaria: diseño en curso (brainstorming), ver sesión de abajo — todavía
  no se escribió la spec final ni se empezó a codear.

## 2026-08-24

### OCR worker desplegado en el server (parcial)
`ocr-worker/.venv` creado con Python 3.14 del server (system pip bloqueado por
PEP 668/externally-managed). `PyMuPDF` pineado a `1.24.10` no tiene wheel para
cp314 y el build desde fuente fallaba (tarball de 54MB, conexión del server muy
lenta/con cortes de DNS intermitentes) — bumpeado a `1.28.2` (misma API de `fitz`
usada: `open`/`Matrix`/`get_pixmap`). Commit `65bb0e5`.

Corriendo con PM2 (`comprobantes-ocr-worker`, puerto 5004, intérprete del venv) —
`curl 127.0.0.1:5004/health` → `{"ok":true,"tesseract":true}`. **Falta el paso 7 del
script** (`deploy-comprobantes-ocr-worker.sh`): symlink de nginx (8087→5004) y
`nginx -t && systemctl reload nginx`, ambos con `sudo` — mi sesión de Bash en esta
PC no puede autenticar sudo (ver memoria `feedback-github-cli-apt-repo-broken`),
Franco lo tiene que correr a mano. Ojo además: ni 5004 ni 8087 tienen regla en
ufw (`ufw status` no los lista) — si n8n termina corriendo en un contenedor Docker
en esta misma PC, confirmar que llega a `127.0.0.1:5004`/`192.168.30.181:8087` antes
de asumir que va a andar (ufw+Docker tiene sus propias trampas, ver abajo).

### n8n: no existía, decidido instalarlo acá con Docker
Al revisar para "activar el workflow", encontré que **n8n nunca se desplegó** en
este server (ni Docker, ni systemd, ni PM2, puerto 5678 no respondía) — solo
existía el JSON del workflow. Franco confirmó: instalarlo acá mismo con Docker.

Hecho: `docker volume create n8n_data` (persistente, ya existe). `docker pull
docker.n8n.io/n8nio/n8n:latest` se cortó a mitad (`connection reset by peer`,
misma conexión lenta que afectó a pip) — **hay que reintentar el pull**.

Cuidado de seguridad a tener en cuenta al levantar el contenedor: publicar el
puerto con `-p 5678:5678` (bind a `0.0.0.0`) puede saltarse las reglas de ufw
porque Docker manipula iptables directamente (DNAT en la tabla `nat`, antes de
que ufw aplique su cadena INPUT) — el mismo riesgo que ya se documentó para el
OCR worker (no exponer sin auth). Publicar con `-p 192.168.30.181:5678:5678`
(bind a la IP LAN, no a todas las interfaces) para que quede en la misma postura
"solo LAN/Tailscale" que el resto de los servicios de Franco.

Falta después de levantar el contenedor:
1. Franco crea la cuenta owner (login inicial) en `http://192.168.30.181:5678` —
   no lo puedo hacer yo (requiere elegir su propio email/password).
2. Cargar credencial de Firestore en n8n usando el service account
   (`~/.firebase-keys/proyecomprobantes-sa.json`) para el nodo "Nuevo comprobante
   en Firestore".
3. Corregir la URL del nodo "Llamar OCR worker": el JSON trae
   `http://127.0.0.1:5003/procesar` (puerto viejo/incorrecto — 5003 es
   `dashboard-ns`, un proyecto totalmente distinto, coincidencia de puerto). Debe
   ser `5004` (o `192.168.30.181:8087` una vez armado el proxy de nginx).
4. Importar `n8n/workflow-procesar-comprobantes.json` y activar.
5. Verificar si el nodo `n8n-nodes-base.googleFirestoreTrigger` existe como nodo
   built-in en la versión actual de n8n o si hace falta instalar un nodo
   community — no lo pude confirmar todavía (nunca until llegué a tener el
   contenedor corriendo).

### Google Sheet de conciliación: acceso confirmado
El service account de Firebase (`firebase-adminsdk-fbsvc@proyecomprobantes.iam.gserviceaccount.com`)
**ya tiene acceso** al sheet de movimientos bancarios (probado con un JWT firmado a
mano + scope `spreadsheets.readonly`, sin depender de librerías de Google — esas
recién se instalaron en el venv del OCR worker). Sheet ID:
`15VPiJOwFtWKqY8yLu6-pCLdKNFdcDChqbmNA4tY6skA`.

Pestañas reales (ojo con los espacios, son parte del nombre):
- `"trf , cheque y cobros"` (15.442 filas) — según Franco, columnas: `0, banco,
  empresa, fecha, nº de comprobante, detalle banco, monto, hs de acreditación,
  descripción`. **Falta confirmar el encabezado real leyendo la fila 1** (se cortó
  por un problema del clasificador de seguridad de Bash, no llegué a reintentarlo).
- `"MP "` (con espacio al final, 3.029 filas) — columnas: `BANCO, EMPRESA, FECHA,
  DETALLE BANCO, MONTO, HS ACREDITACIÓN, DESCRIPCIÓN` (sin nº de comprobante).
- Hay otras pestañas en el mismo sheet (`" 1/9"`, `MODELO`, `USD `, `Hoja 34`,
  `Hoja 36`, …) que NO son relevantes para esto.

No tengo confirmado todavía si el service account tiene permiso de **escritura**
(solo probé `spreadsheets.readonly`) — necesario porque el diseño acordado escribe
de vuelta en el sheet al conciliar (ver abajo).

### Conciliación bancaria: brainstorming en curso (arquitectónico, sin spec escrita aún)
Decisiones ya tomadas con Franco (faltan más preguntas antes de presentar el
diseño completo y escribir la spec en `docs/superpowers/specs/`):

- **Fuente de datos**: el Google Sheet de arriba (no `bank-extractor`, no API
  bancaria).
- **Multi-empresa**: la columna `empresa`/`EMPRESA` del sheet ya identifica a cuál
  empresa/cuenta pertenece cada movimiento.
- **Disparo del matching**: manual — botón "Conciliar" en el panel de supervisor
  (no automático al aprobar un comprobante).
- **Resultado**: se ve en `admin.html` (pestaña nueva) Y se puede exportar a Excel.
- **Al encontrar un match**: escribe de vuelta en la fila del sheet, completando
  dos columnas que hoy se cargan a mano:
  - `HS ACREDITACIÓN` ← hora extraída del comprobante por OCR. **El parser
    (`parsers.py`) todavía NO extrae hora, solo fecha** (`_fecha`) — hay que
    agregar una función `_hora` antes de poder implementar esto.
  - `DESCRIPCIÓN` ← el valor de **`sucursal`** que el vendedor eligió al subir el
    comprobante en `dashboard.html` (campo real, confirmado en código:
    `web/public/js/app.js`, array `SUCURSALES` — no se llama "empresa" en el
    formulario aunque en el sheet la columna sí se llame así). Valores actuales:
    Grupo Lantier, Aramendi, Wolf, Family Group, HyT, Alce, Limite Vertical.
- **Sin filtro obligatorio por sucursal**: el matching busca en TODO el sheet, no
  solo en filas de la misma sucursal elegida al subir — por si el vendedor se
  equivocó de sucursal al cargar.
- **Matching manual**: sí, para los comprobantes sin match automático, el
  supervisor tiene que poder buscar y vincular a mano una fila específica del
  sheet desde el panel (no alcanza con solo listarlos).

Preguntas que faltan antes de cerrar el diseño: tolerancias exactas de monto/fecha
contra estas columnas reales (el plan original hablaba de "últimos 4 dígitos" que
no existen como columna — hay que ver si `nº de comprobante` cumple ese rol, y qué
pasa con la hoja `MP` que ni siquiera tiene esa columna), qué pasa si hay más de
un candidato igual de plausible, y si conviene usar `detalle banco`/`descripción`
como texto libre para matchear contra `emisor_nombre`/`receptor_nombre`.

### Para retomar
1. Reintentar `docker pull docker.n8n.io/n8nio/n8n:latest` (se cortó a mitad).
2. Pedirle a Franco que corra a mano (sudo, no lo puedo hacer yo):
   ```
   sudo ln -sf /home/franco/Proyectos/server-config/nginx/sites-available/comprobantes-ocr-worker /etc/nginx/sites-enabled/comprobantes-ocr-worker
   sudo nginx -t && sudo systemctl reload nginx
   ```
3. Confirmar si hace falta regla de ufw para 8087 (LAN/Tailscale, mismo patrón que
   los demás servicios) antes de que n8n intente pegarle al OCR worker desde un
   contenedor Docker.
4. Levantar el contenedor de n8n con bind a `192.168.30.181` (no `0.0.0.0`), Franco
   crea la cuenta owner, cargar credencial Firestore, corregir puerto 5003→5004 en
   el workflow, importar y activar.
5. Terminar de leer el sheet (encabezados reales fila 1 de ambas pestañas) y
   confirmar permiso de escritura del service account.
6. Seguir el brainstorming de conciliación (quedan preguntas abiertas arriba) hasta
   tener diseño aprobado → spec escrita → plan de implementación.
7. Pedirle a Franco los datos (nombre + email) de los vendedores reales para darlos
   de alta.
