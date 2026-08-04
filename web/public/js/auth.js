// Auth compartido entre páginas.
// Redirige según rol: vendedor → dashboard.html, supervisor → admin.html
(function () {
  const loginForm = document.getElementById('login-form');

  auth.onAuthStateChanged(async (user) => {
    if (user) {
      try {
        const doc = await db.collection('usuarios').doc(user.uid).get();
        if (doc.exists) {
          localStorage.setItem('usuario', JSON.stringify({ uid: user.uid, ...doc.data() }));
        }
      } catch (e) {
        console.warn('No se pudo leer perfil', e);
      }

      const page = document.body.dataset.page || '';
      const perfil = obtenerPerfil();
      if (page === 'login') {
        window.location.href = perfil && perfil.rol === 'supervisor' ? 'admin.html' : 'dashboard.html';
      } else if (page === 'admin' && !(perfil && perfil.rol === 'supervisor')) {
        window.location.href = 'dashboard.html';
      } else {
        pintarHeader();
      }
    } else {
      if (document.body.dataset.page !== 'login') {
        window.location.href = 'index.html';
      }
    }
  });

  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      const errorEl = document.getElementById('login-error');
      const btn = document.getElementById('btn-login');

      errorEl.hidden = true;
      btn.disabled = true;
      btn.textContent = 'Ingresando…';
      try {
        await auth.signInWithEmailAndPassword(email, password);
        const doc = await db.collection('usuarios').doc(auth.currentUser.uid).get();
        const perfil = doc.data();
        localStorage.setItem('usuario', JSON.stringify({ uid: auth.currentUser.uid, ...perfil }));
        window.location.href = perfil && perfil.rol === 'supervisor' ? 'admin.html' : 'dashboard.html';
      } catch (err) {
        errorEl.textContent = err.code === 'auth/user-not-found' || err.code === 'auth/wrong-password'
          ? 'Email o contraseña incorrectos.'
          : 'No se pudo iniciar sesión. Verificá tu conexión.';
        errorEl.hidden = false;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Ingresar';
      }
    });
  }
})();
