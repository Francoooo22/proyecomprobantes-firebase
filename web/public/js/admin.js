// Panel supervisor: ve todos los comprobantes, aprueba/rechaza, abre modal con OCR.

(function () {
  const list = document.getElementById('admin-list');
  if (!list) return;

  const onlyPending = document.getElementById('only-pending');
  const search = document.getElementById('search');

  const q = db.collection('comprobantes')
    .orderBy('fecha_subida', 'desc')
    .limit(200);

  let docs = [];

  function filtrar() {
    const soloPendientes = onlyPending.checked;
    const q = search.value.trim().toLowerCase();
    const visibles = docs.filter((d) => {
      if (soloPendientes && d.estado !== 'pendiente' && d.estado !== 'procesado') return false;
      if (q) {
        const hay = [d.sucursal, d.vendedor_nombre, d.tipo, d.nota]
          .concat(d.datos_extraidos ? Object.values(d.datos_extraidos).map(String) : [])
          .join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    render(visibles);
  }

  function render(visibles) {
    if (!visibles.length) {
      list.innerHTML = '<p class="muted">No hay comprobantes para mostrar.</p>';
      return;
    }
    list.innerHTML = visibles.map((d) => {
      const extra = d.datos_extraidos || {};
      return `
        <article class="item">
          <div class="item-main">
            <div class="item-title">${estadoBadge(d.estado)} ${d.sucursal || '—'} · ${d.tipo || '—'}</div>
            <div class="item-sub muted">${formatFecha(d.fecha_subida)} · ${d.vendedor_nombre || ''}</div>
            <div class="item-sub">
              ${extra.monto ? 'Monto: <b>' + formatMonto(extra.monto) + '</b>' : ''}
              ${extra.cuit ? ' · CUIT: <b>' + extra.cuit + '</b>' : ''}
              ${extra.fecha ? ' · Fecha: <b>' + extra.fecha + '</b>' : ''}
              ${extra.origen ? ' · De: <b>' + extra.origen + '</b>' : ''}
              ${extra.destino ? ' · Para: <b>' + extra.destino + '</b>' : ''}
            </div>
          </div>
          <div class="item-actions">
            <button class="btn-link" onclick="abrirDetalle('${d.id}')">Ver</button>
            ${d.estado === 'pendiente' || d.estado === 'procesado'
              ? `<button class="btn-sm ok" onclick="cambiarEstado('${d.id}', 'aprobado')">Aprobar</button>
                 <button class="btn-sm danger" onclick="cambiarEstado('${d.id}', 'rechazado')">Rechazar</button>`
              : ''}
          </div>
        </article>`;
    }).join('');
  }

  q.onSnapshot((snap) => {
    docs = snap.docs.map((d) => ({ id: d.id, ...d.data() }));
    filtrar();
  }, (err) => {
    console.error(err);
    list.innerHTML = '<p class="error">No se pudo cargar. ¿Tu cuenta es de supervisor?</p>';
  });

  onlyPending.addEventListener('change', filtrar);
  search.addEventListener('input', filtrar);

  // Modal con detalle + OCR + aprobar/rechazar
  const modal = document.getElementById('modal');
  const modalBody = document.getElementById('modal-body');

  window.abrirDetalle = async (id) => {
    const doc = await db.collection('comprobantes').doc(id).get();
    const d = doc.data();
    modalBody.innerHTML = `
      <h3>${d.sucursal || '—'} · ${d.tipo || '—'} ${estadoBadge(d.estado)}</h3>
      <p class="muted">Subido: ${formatFecha(d.fecha_subida)} · ${d.vendedor_nombre || ''}</p>
      ${d.storage_url ? `<a href="${d.storage_url}" target="_blank" class="btn-link">Abrir imagen</a>` : ''}
      ${d.nota ? `<p><b>Nota:</b> ${d.nota}</p>` : ''}
      ${d.datos_extraidos ? `<pre class="pre">${JSON.stringify(d.datos_extraidos, null, 2)}</pre>` : ''}
      <details><summary>Texto OCR</summary><pre class="pre">${d.texto_ocr || 'Sin texto OCR aún.'}</pre></details>
      <label for="obs">Observación</label>
      <input type="text" id="obs" placeholder="Motivo si se rechaza…">
      <div class="modal-actions">
        ${d.estado === 'pendiente' || d.estado === 'procesado'
          ? `<button class="btn-sm ok" onclick="cambiarEstado('${d.id}', 'aprobado')">Aprobar</button>
             <button class="btn-sm danger" onclick="cambiarEstado('${d.id}', 'rechazado')">Rechazar</button>`
          : ''}
      </div>`;
    modal.hidden = false;
  };

  window.cambiarEstado = async (id, estado) => {
    const obs = document.getElementById('obs') ? document.getElementById('obs').value : '';
    await db.collection('comprobantes').doc(id).update({ estado, observacion: obs || '' });
    modal.hidden = true;
  };

  document.getElementById('modal-close').addEventListener('click', () => { modal.hidden = true; });
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.hidden = true; });
})();
