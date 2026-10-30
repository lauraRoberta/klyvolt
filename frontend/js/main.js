/* KLYVOLT · main.js — interface compartilhada por todas as páginas
   1. Tema claro/escuro, menu e animações de entrada (comportamento visual original)
   2. Avisos (toasts), confirmação, estados de botão, formatação e listas de cards
   Não acessa a API: as requisições ficam em js/api.js. */
(function () {
  'use strict';
  const root = document.documentElement;
  const body = document.body;

  /* ================================================================== */
  /* 1. Tema, menu e animações (inalterado em relação ao design aprovado) */
  /* ================================================================== */
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
    try { window.localStorage.setItem('klyvolt.theme', next); } catch (e) { /* navegação privada */ }
    syncThemeUI();
  });
  media.addEventListener?.('change', (event) => {
    try { if (window.localStorage.getItem('klyvolt.theme')) return; } catch (e) { /* sem armazenamento */ }
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
  // Realce progressivo: sem IntersectionObserver ou com movimento reduzido, o conteúdo continua visível.
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const blocks = document.querySelectorAll('.kv-module,.kv-section-heading,.kv-feature-banner');
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) if (entry.isIntersecting) {
        entry.target.classList.remove('kv-pre'); observer.unobserve(entry.target);
      }
    }, { threshold: .05, rootMargin: '0px 0px 40px 0px' });
    for (const element of blocks) { element.classList.add('kv-reveal', 'kv-pre'); observer.observe(element); }
  }

  /* ================================================================== */
  /* 2. Utilitários de interface                                          */
  /* ================================================================== */
  const nf2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const nfBRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const valido = v => v != null && v !== '' && Number.isFinite(Number(v));
  const fmt = {
    num: v => valido(v) ? nf2.format(Number(v)) : '—',
    brl: v => valido(v) ? nfBRL.format(Number(v)) : '—',
    pct: v => valido(v) ? (v > 0 ? '+' : '') + nf2.format(Number(v)) + '%' : '—',
    id: v => '#' + String(v).padStart(2, '0'),
    // A API devolve datas sem fuso (horário de Brasília): interpretar como hora local.
    data(v) { const d = parseLocal(v); return d ? d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'; },
    dia(v) { const d = parseLocal(v); return d ? d.toLocaleDateString('pt-BR') : '—'; },
    inputDT: v => v ? String(v).replace(' ', 'T').slice(0, 16) : '',
    inputDate: v => v ? String(v).slice(0, 10) : ''
  };
  function parseLocal(v) {
    if (!v) return null;
    if (v instanceof Date) return v;
    const s = String(v).replace(' ', 'T').replace(/([+-]\d\d:\d\d|Z)$/, '');
    const d = new Date(s.length === 10 ? s + 'T00:00:00' : s);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  function toLocalISO(d) {
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }
  function numero(texto) {
    if (texto == null) return NaN;
    let s = String(texto).trim().replace(/kwh|r\$|w$/gi, '').trim();
    if (s === '') return NaN;
    if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.');
    return Number(s);
  }
  function el(tag, className, text) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function icon(name) { const i = el('i', 'fa-solid ' + name); i.setAttribute('aria-hidden', 'true'); return i; }

  // Avisos no padrão visual do KLYVOLT (substituem alert() do navegador)
  let toastStack;
  function toast(mensagem, tipo = 'sucesso', duracao) {
    if (!toastStack) {
      toastStack = el('div', 'kv-toast-stack');
      toastStack.setAttribute('role', 'status');
      toastStack.setAttribute('aria-live', 'polite');
      body.append(toastStack);
    }
    const icones = { sucesso: 'fa-circle-check', erro: 'fa-circle-exclamation', aviso: 'fa-triangle-exclamation', info: 'fa-circle-info' };
    const t = el('div', 'kv-toast kv-toast-' + tipo);
    t.append(icon(icones[tipo] || icones.info), el('span', 'kv-toast-text', mensagem));
    const fechar = el('button', 'kv-toast-close');
    fechar.type = 'button'; fechar.setAttribute('aria-label', 'Fechar aviso'); fechar.append(icon('fa-xmark'));
    t.append(fechar);
    const sair = () => { t.classList.add('kv-toast-out'); setTimeout(() => t.remove(), 260); };
    fechar.addEventListener('click', sair);
    toastStack.append(t);
    setTimeout(sair, duracao || (tipo === 'erro' ? 7000 : 4200));
  }

  // Confirmação com os mesmos componentes dos modais (substitui confirm() do navegador)
  function confirmar({ titulo = 'Confirmar ação', mensagem = '', detalhe = '', confirmar: rotulo = 'Excluir', perigo = true } = {}) {
    return new Promise(resolve => {
      const overlay = el('div', 'modal-overlay kv-confirm-overlay');
      overlay.style.display = 'flex';
      overlay.setAttribute('role', 'dialog'); overlay.setAttribute('aria-modal', 'true');
      const box = el('div', 'modal-content kv-confirm');
      const header = el('div', 'modal-header');
      const h = el('h2', null, titulo); h.id = 'kvConfirmTitle'; overlay.setAttribute('aria-labelledby', h.id);
      const x = el('button', 'close-btn'); x.type = 'button'; x.setAttribute('aria-label', 'Fechar'); x.append(icon('fa-xmark'));
      header.append(h, x);
      const corpo = el('div', 'modal-body');
      corpo.append(el('p', 'kv-confirm-text', mensagem));
      if (detalhe) corpo.append(el('p', 'kv-confirm-detail', detalhe));
      const footer = el('div', 'modal-footer');
      const cancelar = el('button', 'btn-modal btn-cancel', 'Cancelar'); cancelar.type = 'button';
      const ok = el('button', 'btn-modal ' + (perigo ? 'btn-delete' : 'btn-confirm'), rotulo); ok.type = 'button';
      footer.append(cancelar, ok);
      box.append(header, corpo, footer); overlay.append(box); body.append(overlay);
      const anterior = document.activeElement;
      const fim = valor => {
        document.removeEventListener('keydown', tecla);
        overlay.remove();
        if (anterior && anterior.focus) anterior.focus();
        resolve(valor);
      };
      const tecla = e => { if (e.key === 'Escape') fim(false); };
      document.addEventListener('keydown', tecla);
      x.addEventListener('click', () => fim(false));
      cancelar.addEventListener('click', () => fim(false));
      ok.addEventListener('click', () => fim(true));
      overlay.addEventListener('click', e => { if (e.target === overlay) fim(false); });
      cancelar.focus();
    });
  }

  // Botão em processamento: evita envio duplicado e mostra o andamento
  function ocupado(botao, ativo, texto) {
    if (!botao) return;
    if (ativo) {
      botao.dataset.kvLabel = botao.dataset.kvLabel || botao.innerHTML;
      botao.disabled = true; botao.setAttribute('aria-busy', 'true');
      if (texto) botao.textContent = texto;
    } else {
      botao.disabled = false; botao.removeAttribute('aria-busy');
      if (botao.dataset.kvLabel != null) { botao.innerHTML = botao.dataset.kvLabel; delete botao.dataset.kvLabel; }
    }
  }

  // Lista de cards (.decision-card) com estado vazio, carregamento, filtro e busca
  function lista(container, { vazio, filtro } = {}) {
    let empty = container.querySelector('.kv-empty-state');
    if (!empty) { empty = el('p', 'kv-empty-state'); empty.setAttribute('role', 'status'); container.append(empty); }
    const textoVazio = vazio || empty.textContent;
    let nota = null;
    const api = {
      filtroAtual: 'todos', busca: '',
      carregando() { api.limpar(); empty.hidden = false; empty.textContent = 'Carregando registros…'; container.setAttribute('aria-busy', 'true'); },
      erro(msg) { api.limpar(); empty.hidden = false; empty.textContent = msg; container.removeAttribute('aria-busy'); },
      limpar() { container.querySelectorAll('.decision-card').forEach(c => c.remove()); if (nota) { nota.remove(); nota = null; } },
      render(itens, construir, rodape) {
        container.removeAttribute('aria-busy');
        api.limpar();
        const frag = document.createDocumentFragment();
        for (const item of itens) { const c = construir(item); if (c) frag.append(c); }
        container.insertBefore(frag, empty);
        if (rodape) { nota = el('p', 'kv-empty-state kv-list-note', rodape); container.append(nota); }
        api.aplicar();
      },
      aplicar() {
        const cards = [...container.querySelectorAll('.decision-card')];
        let visiveis = 0;
        const termo = api.busca.trim().toLowerCase();
        for (const c of cards) {
          const okFiltro = !filtro || api.filtroAtual === 'todos' || api.filtroAtual === 'todas' || filtro(c, api.filtroAtual);
          const okBusca = !termo || c.textContent.toLowerCase().includes(termo);
          const mostra = okFiltro && okBusca;
          c.style.display = mostra ? '' : 'none';
          if (mostra) visiveis++;
        }
        empty.hidden = visiveis > 0;
        if (!visiveis) empty.textContent = cards.length ? 'Nenhum registro corresponde ao filtro ou à busca.' : textoVazio;
      }
    };
    return api;
  }

  function marcarAba(botao) {
    if (!botao) return;
    const grupo = botao.closest('.tabs');
    if (!grupo) return;
    grupo.querySelectorAll('.tab').forEach(t => { t.classList.remove('active'); t.classList.add('inactive'); t.setAttribute('aria-selected', 'false'); });
    botao.classList.remove('inactive'); botao.classList.add('active'); botao.setAttribute('aria-selected', 'true');
  }

  function card({ id, badge, badgeClasse = 'status-executada', dataset = {} }) {
    const c = el('div', 'decision-card');
    for (const [k, v] of Object.entries(dataset)) c.dataset[k] = v == null ? '' : String(v);
    const head = el('div', 'card-header');
    head.append(el('span', 'id-badge', fmt.id(id)), el('span', 'status-badge ' + badgeClasse, badge));
    const corpo = el('div', 'card-body');
    const acoes = el('div', 'card-actions');
    const ver = el('button', 'btn-action btn-view', 'Detalhes'); ver.type = 'button';
    acoes.append(ver);
    c.append(head, corpo, acoes);
    const linha = (texto, iconName, classe) => {
      const p = el('p', classe || '');
      if (iconName) p.append(icon(iconName), ' ');
      p.append(document.createTextNode(texto));
      corpo.append(p); return p;
    };
    return { card: c, corpo, ver, linha };
  }

  // Mini-gráfico de barras (componente .chart do design) com valores reais
  function grafico(valores, rotulos = []) {
    if (!valores || valores.length < 2) return null;
    const max = Math.max(...valores, 0);
    if (max <= 0) return null;
    const ch = el('div', 'chart');
    ch.setAttribute('role', 'img');
    ch.setAttribute('aria-label', 'Valores: ' + valores.map(v => fmt.num(v) + ' kWh').join(', '));
    valores.forEach((v, i) => {
      const b = el('div', 'bar');
      b.style.height = Math.max(6, Math.round((v / max) * 100)) + '%';
      b.title = (rotulos[i] ? rotulos[i] + ' · ' : '') + fmt.num(v) + ' kWh';
      ch.append(b);
    });
    return ch;
  }

  function preencherSelect(select, itens, { valor, rotulo, vazio, selecionado } = {}) {
    if (!select) return;
    const atual = selecionado != null ? String(selecionado) : select.value;
    select.replaceChildren();
    if (vazio) { const o = new Option(vazio, ''); if (vazio.startsWith('Selecione')) o.disabled = true; select.add(o); }
    for (const it of itens) select.add(new Option(rotulo(it), String(valor(it))));
    select.value = atual && [...select.options].some(o => o.value === atual) ? atual : '';
  }

  // Fecha o modal da página ao clicar fora ou pressionar Esc
  function prepararModal(overlay, fechar) {
    overlay.addEventListener('click', function (e) { if (e.target === this) fechar(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && overlay.style.display === 'flex') fechar(); });
  }
  function botoesModal(container, itens) {
    container.replaceChildren();
    for (const [texto, classe, acao] of itens) {
      const b = el('button', 'btn-modal ' + classe, texto); b.type = 'button';
      b.addEventListener('click', () => acao(b)); container.append(b);
    }
  }

  window.KV = Object.assign(window.KV || {}, {
    fmt, numero, parseLocal, toLocalISO, el, icon, toast, confirmar, ocupado,
    lista, marcarAba, card, grafico, preencherSelect, prepararModal, botoesModal
  });
})();
