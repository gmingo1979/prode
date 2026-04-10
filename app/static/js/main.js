/* main.js — JS principal de la app
   Maneja sidebar toggle, pantalla completa y helpers globales. */

(function () {
  'use strict';

  /* ── Detectar mobile ─────────────────────────────────────── */
  function esMobile() {
    return window.innerWidth <= 768;
  }

  /* ── Sidebar ─────────────────────────────────────────────── */
  const sidebar  = document.getElementById('appSidebar');
  const toggle   = document.getElementById('sidebarToggle');
  const overlay  = document.getElementById('sidebarOverlay');
  const main     = document.getElementById('appMain');
  const footer   = document.getElementById('appFooter');

  function abrirSidebar() {
    if (esMobile()) {
      sidebar && sidebar.classList.add('mobile-open');
      overlay && overlay.classList.add('visible');
    } else {
      document.body.classList.remove('sidebar-collapsed');
    }
  }

  function cerrarSidebar() {
    if (esMobile()) {
      sidebar && sidebar.classList.remove('mobile-open');
      overlay && overlay.classList.remove('visible');
    } else {
      document.body.classList.add('sidebar-collapsed');
    }
  }

  function toggleSidebar() {
    if (esMobile()) {
      const abierto = sidebar && sidebar.classList.contains('mobile-open');
      abierto ? cerrarSidebar() : abrirSidebar();
    } else {
      const colapsado = document.body.classList.contains('sidebar-collapsed');
      colapsado ? abrirSidebar() : cerrarSidebar();
    }
  }

  if (toggle)  toggle.addEventListener('click', toggleSidebar);
  if (overlay) overlay.addEventListener('click', cerrarSidebar);

  /* En resize: limpiar estado móvil al pasar a desktop */
  window.addEventListener('resize', function () {
    if (!esMobile()) {
      sidebar  && sidebar.classList.remove('mobile-open');
      overlay  && overlay.classList.remove('visible');
    }
  });

  /* ── Flash messages: auto-cerrar después de 6s ───────────── */
  document.addEventListener('DOMContentLoaded', function () {
    var flashes = document.querySelectorAll('#flash-messages .alert');
    flashes.forEach(function (el) {
      setTimeout(function () {
        el.classList.remove('show');
        setTimeout(function () { el.remove(); }, 300);
      }, 6000);
    });
  });

})();
