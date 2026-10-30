/* KLYVOLT · api.js — comunicação com a API FastAPI e sessão do usuário
   O navegador conversa SOMENTE com a FastAPI. Não coloque chaves do Supabase aqui. */

// Endereço da API (backend/main.py). Em produção, troque pelo endereço publicado.
const API_URL = 'http://127.0.0.1:8000';

(function () {
  'use strict';
  const root = document.documentElement;
  const body = document.body;
  const modulo = body.dataset.module || (body.classList.contains('kv-home') ? 'home' : '');
  const PUBLICAS = new Set(['home', 'entrar']);
  const privada = !PUBLICAS.has(modulo);
  const CHAVE = 'klyvolt.sessao';

  /* ---------------- Sessão (tokens recebidos no login) ---------------- */
  function lerSessao() {
    try { return JSON.parse(localStorage.getItem(CHAVE)) || null; } catch (e) { return null; }
  }
  function salvarSessao(sessao) {
    try {
      if (sessao) localStorage.setItem(CHAVE, JSON.stringify({
        access_token: sessao.access_token, refresh_token: sessao.refresh_token, perfil: sessao.perfil || null
      }));
      else localStorage.removeItem(CHAVE);
    } catch (e) { /* navegação privada: a sessão vale só nesta página */ }
  }
  const caminho = nome => modulo === 'home' ? `pages/${nome}.html` : `${nome}.html`;
  function irParaLogin(motivo) {
    const voltar = privada ? `&voltar=${encodeURIComponent(modulo)}` : '';
    location.replace(caminho('entrar') + '?entrar=1' + voltar + (motivo ? `&motivo=${motivo}` : ''));
  }

  /* ---------------- Requisição central (padrão do material 3) ---------------- */
  let renovando = null;
  async function renovarSessao() {
    const atual = lerSessao();
    if (!atual || !atual.refresh_token) return false;
    renovando = renovando || fetch(API_URL + '/auth/refresh', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: atual.refresh_token })
    }).then(async r => {
      if (!r.ok) return false;
      salvarSessao(await r.json());
      return true;
    }).catch(() => false).finally(() => { renovando = null; });
    return renovando;
  }

  async function requisicao(caminhoApi = '', metodo = 'GET', dados = null, { autenticar = true, tentativa = 0, resposta: devolverResposta = false } = {}) {
    const opcoes = { method: metodo, headers: {} };
    if (dados !== null) {
      opcoes.headers['Content-Type'] = 'application/json';
      opcoes.body = JSON.stringify(dados);
    }
    const sessao = lerSessao();
    if (autenticar && sessao && sessao.access_token) opcoes.headers.Authorization = 'Bearer ' + sessao.access_token;
    let resposta;
    try {
      resposta = await fetch(API_URL + caminhoApi, opcoes);
    } catch {
      throw new Error('Não foi possível acessar a API. Confira se o backend está rodando e a configuração de CORS.');
    }
    // Token expirado: renova uma vez e repete a operação
    if (resposta.status === 401 && autenticar && sessao && tentativa === 0 && await renovarSessao()) {
      return requisicao(caminhoApi, metodo, dados, { autenticar, tentativa: 1, resposta: devolverResposta });
    }
    if (resposta.status === 401 && autenticar && privada) {
      salvarSessao(null);
      irParaLogin('sessao');
      throw new Error('Sua sessão expirou. Entre novamente.');
    }
    // A exclusão retorna 204, sem JSON.
    if (resposta.status === 204) return null;
    let conteudo = null;
    try { conteudo = await resposta.json(); } catch { conteudo = null; }
    if (!resposta.ok) {
      let detalhe = conteudo && conteudo.detail;
      if (Array.isArray(detalhe)) {
        detalhe = detalhe.map(item => `${item.loc.filter(x => x !== 'body').join('.')}: ${item.msg}`).join(' | ');
      }
      const erro = new Error(detalhe || 'Não foi possível concluir a operação.');
      erro.status = resposta.status;
      throw erro;
    }
    return devolverResposta ? { dados: conteudo, resposta } : conteudo;
  }

  /* ---------------- Proteção das páginas internas ---------------- */
  const pronto = (async () => {
    if (!privada) return lerSessao();
    if (!lerSessao()) { irParaLogin(); return new Promise(() => {}); }
    try {
      const perfil = await requisicao('/auth/me');
      const sessao = lerSessao();
      salvarSessao({ ...sessao, perfil });
      root.classList.remove('kv-auth-pending');
      try {
        const aviso = sessionStorage.getItem('klyvolt.aviso');
        if (aviso) { sessionStorage.removeItem('klyvolt.aviso'); KV.toast(aviso); }
      } catch (e) { /* sem armazenamento de sessão */ }
      return { ...sessao, perfil };
    } catch (erro) {
      root.classList.remove('kv-auth-pending');
      if (erro.status === 403) { salvarSessao(null); irParaLogin('sem-empresa'); return new Promise(() => {}); }
      KV.toast(erro.message, 'erro', 10000);
      document.querySelectorAll('.kv-empty-state').forEach(p => { p.hidden = false; p.textContent = erro.message; });
      throw erro;
    }
  })();
  pronto.catch(() => {});

  async function sair() {
    try { await requisicao('/auth/logout', 'POST'); } catch (e) { /* encerra localmente mesmo sem rede */ }
    salvarSessao(null);
    location.href = caminho('entrar') + '?entrar=1';
  }

  /* ---------------- Botão do menu: "Entrar" para visitantes ---------------- */
  const acao = document.querySelector('.kv-nav-right .kv-action');
  if (acao && !lerSessao()) {
    acao.href = caminho('entrar') + '?entrar=1';
    acao.replaceChildren();
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'kv-nav-plus'); svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('width', '15'); svg.setAttribute('height', '15');
    svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round'); svg.setAttribute('aria-hidden', 'true');
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', 'M10 17l5-5-5-5M15 12H3M15 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4');
    svg.append(p);
    acao.append(svg, document.createTextNode(' Entrar'));
  }

  const perfil = () => (lerSessao() || {}).perfil || null;
  window.KV = Object.assign(window.KV || {}, {
    API_URL, requisicao, pronto, sair, lerSessao, salvarSessao, irParaLogin, modulo, caminho,
    perfil,
    isAdmin: () => (perfil() || {}).tipo_usuario === 'Administrador',
    podeOperar: () => ['Administrador', 'Operador'].includes((perfil() || {}).tipo_usuario)
  });
})();
