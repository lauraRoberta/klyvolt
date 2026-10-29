/* KLYVOLT: exclusively visual experience layer.
   Never intercepts legacy form submit, filter, search or modal events. */
(function () {
  'use strict';
  const root = document.documentElement;
  const themeButton = document.querySelector('.kv-theme-toggle');
  const media = window.matchMedia('(prefers-color-scheme: light)');
  const themeMeta = document.querySelector('meta[name="theme-color"]');

  function syncThemeUI() {
    const isLight = root.dataset.theme === 'light';
    root.style.colorScheme = isLight ? 'light' : 'dark';
    if (themeButton) {
      themeButton.setAttribute('aria-label', isLight ? 'Alternar para o modo escuro' : 'Alternar para o modo claro');
      themeButton.setAttribute('title', isLight ? 'Ativar modo escuro' : 'Ativar modo claro');
      themeButton.setAttribute('aria-pressed', String(isLight));
    }
    if (themeMeta) themeMeta.setAttribute('content', isLight ? '#F4F7FB' : '#0E1726');
  }
  syncThemeUI();
  if (themeButton) themeButton.addEventListener('click', () => {
    const next = root.dataset.theme === 'light' ? 'dark' : 'light';
    root.dataset.theme = next;
    try { window.localStorage.setItem('klyvolt.theme', next); } catch (e) { /* private browsing */ }
    syncThemeUI();
  });
  media.addEventListener?.('change', (event) => {
    try { if (window.localStorage.getItem('klyvolt.theme')) return; } catch (e) { /* storage unavailable */ }
    root.dataset.theme = event.matches ? 'light' : 'dark'; syncThemeUI();
  });
  window.addEventListener('storage', (event) => {
    if (event.key === 'klyvolt.theme' && (event.newValue === 'dark' || event.newValue === 'light')) {
      root.dataset.theme = event.newValue; syncThemeUI();
    }
  });

  const toggle = document.querySelector('.kv-mobile-toggle');
  const navLinks = document.querySelector('.kv-nav-links');
  if (toggle && navLinks) {
    const setMenu = (open) => {
      navLinks.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    };
    toggle.addEventListener('click', () => setMenu(!navLinks.classList.contains('open')));
    navLinks.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setMenu(false); });
    document.addEventListener('pointerdown', (e) => {
      if (navLinks.classList.contains('open') && !navLinks.contains(e.target) && !toggle.contains(e.target)) setMenu(false);
    });
  }
  // Progressive enhancement only: if no observer or reduced motion, content remains visible.
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const blocks = document.querySelectorAll('.kv-module,.kv-section-heading,.kv-feature-banner');
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) if (entry.isIntersecting) {
        entry.target.classList.remove('kv-pre'); observer.unobserve(entry.target);
      }
    }, {threshold: .05, rootMargin: '0px 0px 40px 0px'});
    for (const element of blocks) {element.classList.add('kv-reveal', 'kv-pre'); observer.observe(element);}
  }
})();
