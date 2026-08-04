// Historial del vendedor: solo sus comprobantes, en vivo.

(function () {
  const list = document.getElementById('history-list');
  if (!list) return;

  const user = auth.currentUser;
  if (!user) return;

  const q = db.collection('comprobantes')
    .where('vendedor_uid', '==', user.uid)
    .orderBy('fecha_subida', 'desc')
    .limit(50);

  q.onSnapshot((snap) => {
    if (snap.empty) {
      list.innerHTML = '<p class="muted">Todavía no subiste comprobantes.</p>';
      return;
    }
    list.innerHTML = snap.docs.map((doc) => {
      const d = doc.data();
      const extra = d.datos_extraidos || {};
      return `
        <article class="item">
          <div class="item-main">
            <div class="item-title">
              ${estadoBadge(d.estado)} ${d.sucursal || '—'} · ${d.tipo || '—'}
            </div>
            <div class="item-sub muted">
              ${formatFecha(d.fecha_subida)}
              ${d.vendedor_nombre ? '· ' + d.vendedor_nombre : ''}
            </div>
            <div class="item-sub">
              ${extra.monto ? 'Monto: <b>' + formatMonto(extra.monto) + '</b>' : ''}
              ${extra.fecha ? ' · Fecha: <b>' + extra.fecha + '</b>' : ''}
              ${extra.origen ? ' · De: <b>' + extra.origen + '</b>' : ''}
              ${d.nota ? '<div class="muted">' + d.nota + '</div>' : ''}
            </div>
          </div>
          <div class="item-actions">
            <button class="btn-link" onclick="abrirImagen('${d.storage_url}')">Ver</button>
            <button class="btn-link" onclick="copiarTexto('${d.id}')">OCR</button>
          </div>
        </article>`;
    }).join('') + '<p class="muted small">Mostrando los últimos 50.</p>';
  }, (err) => {
    console.error(err);
    list.innerHTML = '<p class="error">No se pudo cargar el historial.</p>';
  });
})();

async function copiarTexto(id) {
  const doc = await db.collection('comprobantes').doc(id).get();
  const d = doc.data();
  const texto = d.texto_ocr || 'Sin texto OCR todavía.';
  await navigator.clipboard.writeText(texto);
  alert('Texto OCR copiado al portapapeles.');
}

function abrirImagen(url) {
  if (url) window.open(url, '_blank');
}
