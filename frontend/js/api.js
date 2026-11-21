// js/api.js - acesso à API, sessão (login) e avisos na tela.
// Carregue antes dos outros scripts (com defer, na ordem: api.js, nav.js, crud.js).
// Páginas públicas (início, como funciona, login, cadastro) usam <body data-publica>.
// Todas as outras exigem login: sem sessão, mandam para login.html.

const KLYVOLT_VERSAO = 'perfis-1';

// Endereço do backend (uvicorn main:app --reload). Se mudar a porta, mude aqui.
const API_URL = 'http://127.0.0.1:8000';

// ---------- sessão ----------
const CHAVE_TOKEN = 'klyvolt_token';
const CHAVE_SESSAO = 'klyvolt_sessao';

function obterToken() {
  return localStorage.getItem(CHAVE_TOKEN);
}

// { id_usuario, nome, funcao, empresa: { id_empresa, nome_empresa, ... } } ou null
function sessaoAtual() {
  try { return JSON.parse(localStorage.getItem(CHAVE_SESSAO)); }
  catch (erro) { return null; }
}

function salvarSessao(token, sessao) {
  localStorage.setItem(CHAVE_TOKEN, token);
  localStorage.setItem(CHAVE_SESSAO, JSON.stringify(sessao));
}

function sair() {
  localStorage.removeItem(CHAVE_TOKEN);
  localStorage.removeItem(CHAVE_SESSAO);
  window.location.replace('login.html');
}

// Sem login, volta para o login.
if (!document.body.hasAttribute('data-publica') && !obterToken()) {
  window.location.replace('login.html');
}

// ---------- permissões ----------
// Quem pode criar, editar e apagar em cada cadastro. Aqui só se escondem os botões:
// quem realmente barra é a API (erro 403). Tela fora desta lista = só consulta.
const FUNCOES_QUE_ALTERAM = {
  '/empresas': ['Administrador'],
  '/usuarios': ['Administrador'],
  '/setores': ['Administrador'],
  '/maquinas': ['Administrador'],
  '/sensores': ['Administrador'],
  '/decisoes': ['Administrador'],
  '/consumos': ['Administrador', 'Operador'],
  '/leituras': ['Administrador', 'Operador'],
  '/tomadas-decisao': ['Administrador', 'Operador']
};

function podeAlterar(rota) {
  const sessao = sessaoAtual();
  const permitidas = FUNCOES_QUE_ALTERAM[rota];
  return Boolean(sessao && permitidas && permitidas.includes(sessao.funcao));
}

// ---------- requisições ----------
// O FastAPI devolve erros como {"detail": "texto"} (HTTPException)
// ou {"detail": [{"loc": [...], "msg": "..."}]} (validação do Pydantic, status 422).
function mensagemDeErro(dados, status) {
  const detalhe = dados && dados.detail;
  if (typeof detalhe === 'string') return detalhe;
  if (Array.isArray(detalhe) && detalhe.length > 0) {
    return detalhe.map(item => {
      const caminho = Array.isArray(item.loc) ? item.loc.filter(p => p !== 'body') : [];
      const campo = caminho.length ? caminho[caminho.length - 1] : null;
      const texto = String(item.msg || 'valor inválido').replace(/^Value error, /, '');
      return campo ? `${campo}: ${texto}` : texto;
    }).join(' | ');
  }
  return `Erro ${status} ao falar com a API.`;
}

// requisicao('/maquinas')                      -> GET
// requisicao('/maquinas', 'POST', {...})       -> POST com JSON
// requisicao('/maquinas/3', 'PUT', {...})      -> PUT
// requisicao('/maquinas/3', 'DELETE')          -> DELETE
// Manda o token do login em toda requisição. Se a API responder 401 (sessão vencida),
// encerra a sessão e volta para o login. Lança Error com texto legível se falhar.
async function requisicao(rota, metodo = 'GET', corpo = null) {
  const opcoes = { method: metodo, headers: {} };
  const token = obterToken();
  if (token) opcoes.headers['Authorization'] = `Bearer ${token}`;
  if (corpo !== null && corpo !== undefined) {
    opcoes.headers['Content-Type'] = 'application/json';
    opcoes.body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(API_URL + rota, opcoes);
  } catch (erro) {
    throw new Error('Não foi possível conectar à API. Verifique se o servidor está rodando.');
  }

  let dados = null;
  try { dados = await resposta.json(); } catch (erro) { /* resposta sem corpo (ex.: 204) */ }

  // 401 no login = senha errada (mostra a mensagem); nas demais rotas = sessão vencida
  if (resposta.status === 401 && token && rota !== '/auth/login') {
    sair();
    throw new Error('Sessão expirada. Entre novamente.');
  }
  if (!resposta.ok) throw new Error(mensagemDeErro(dados, resposta.status));
  return dados;
}

// ---------- aviso na tela ----------
// elemento: o <p id="mensagem">; erro = true pinta de vermelho (classe .erro do empresa.css).
function mostrarMensagem(elemento, texto, erro = false) {
  elemento.textContent = texto;
  elemento.classList.toggle('erro', Boolean(erro));
  elemento.hidden = false;
}

function esconderMensagem(elemento) {
  elemento.textContent = '';
  elemento.classList.remove('erro');
  elemento.hidden = true;
}

// ---------- formatação ----------
// "2026-11-14T19:30:00" -> "14/11/2026 19:30:00"
function formatarDataHora(valor) {
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return String(valor);
  return data.toLocaleString('pt-BR');
}