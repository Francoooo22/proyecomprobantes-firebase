// Utilidades compartidas: perfil, sucursales, estados, logout.

const SUCURSALES = [
  'Lantier',
  'Aramendi',
  'Wolf',
  'Family Group',
  'HyT',
  'Alce',
  'Limite Vertical',
];

const ESTADOS = {
  pendiente: { label: 'Pendiente OCR', clase: 'badge-pendiente' },
  procesado: { label: 'Procesado', clase: 'badge-procesado' },
  aprobado: { label: 'Aprobado', clase: 'badge-aprobado' },
  rechazado: { label: 'Rechazado', clase: 'badge-rechazado' },
};

function obtenerPerfil() {
  try {
    return JSON.parse(localStorage.getItem('usuario'));
  } catch (e) {
    return null;
  }
}

function esSupervisor() {
  const p = obtenerPerfil();
  return p && p.rol === 'supervisor';
}

function pintarHeader() {
  const p = obtenerPerfil();
  const nameEl = document.getElementById('user-name');
  const adminLink = document.getElementById('link-admin');
  if (nameEl) nameEl.textContent = p ? p.nombre || p.email : '';
  if (adminLink) adminLink.hidden = !(p && p.rol === 'supervisor');
}

function estadoBadge(estado) {
  const e = ESTADOS[estado] || ESTADOS.pendiente;
  return `<span class="badge ${e.clase}">${e.label}</span>`;
}

function formatFecha(ts) {
  if (!ts) return '—';
  const d = ts.toDate ? ts.toDate() : new Date(ts);
  return d.toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' });
}

function formatMonto(m) {
  if (m == null || isNaN(m)) return '—';
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(m);
}

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-logout');
  if (btn) btn.addEventListener('click', () => {
    localStorage.removeItem('usuario');
    auth.signOut().then(() => { window.location.href = 'index.html'; });
  });
});
