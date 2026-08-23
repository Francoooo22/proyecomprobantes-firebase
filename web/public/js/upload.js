// Subida de comprobantes: storage + Firestore (estado: pendiente_ocr)

(function () {
  document.body.dataset.page = document.body.dataset.page || 'dashboard';

  const form = document.getElementById('upload-form');
  if (!form) return;

  const selectSucursal = document.getElementById('sucursal');
  SUCURSALES.forEach((s) => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    selectSucursal.appendChild(opt);
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById('file');
    const file = fileInput.files[0];
    if (!file) return;

    const msgEl = document.getElementById('upload-msg');
    const errEl = document.getElementById('upload-error');
    const btn = document.getElementById('btn-upload');
    const bar = document.getElementById('upload-progress-bar');
    const progress = document.getElementById('upload-progress');

    msgEl.hidden = true;
    errEl.hidden = true;

    if (file.size > 10 * 1024 * 1024) {
      errEl.textContent = 'El archivo supera los 10MB.';
      errEl.hidden = false;
      return;
    }

    const user = auth.currentUser;
    const perfil = obtenerPerfil();
    if (!user || !perfil) return;

    btn.disabled = true;
    btn.textContent = 'Subiendo…';
    progress.hidden = false;
    bar.style.width = '0%';

    const id = db.collection('comprobantes').doc().id;
    const path = `comprobantes/${user.uid}/${id}_${Date.now()}`;

    try {
      const task = storage.ref(path).put(file);
      task.on('state_changed',
        (snap) => { bar.style.width = `${(snap.bytesTransferred / snap.totalBytes) * 100}%`; },
        null,
        async () => {
          const url = await task.snapshot.ref.getDownloadURL();
          await db.collection('comprobantes').doc(id).set({
            id,
            vendedor_uid: user.uid,
            vendedor_nombre: perfil.nombre || perfil.email,
            sucursal: selectSucursal.value,
            tipo: document.getElementById('tipo').value,
            nro_file: document.getElementById('nro_file').value.trim() || '',
            nota: document.getElementById('nota').value || '',
            storage_path: path,
            storage_url: url,
            nombre_archivo: file.name,
            contenido_tipo: file.type,
            estado: 'pendiente',
            estado_ocr: 'pendiente',
            fecha_subida: firebase.firestore.FieldValue.serverTimestamp(),
          });

          msgEl.textContent = 'Comprobante subido. Se va a procesar automáticamente.';
          msgEl.hidden = false;
          form.reset();
          bar.style.width = '0%';
        }
      );
    } catch (err) {
      console.error(err);
      errEl.textContent = 'No se pudo subir el comprobante.';
      errEl.hidden = false;
    } finally {
      btn.disabled = false;
      btn.textContent = 'Subir';
      progress.hidden = true;
    }
  });
})();
