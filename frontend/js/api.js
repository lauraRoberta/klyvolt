// js/api.js - funções comuns de acesso à API e de aviso na tela.
// Usado por crud.js e pelas telas específicas (sensor.js, tomada_desicao.js...).
// Carregue antes dos outros scripts (com defer, na ordem: api.js, nav.js, crud.js).

// Endereço do backend (uvicorn main:app --reload). Se mudar a porta, mude aqui.
const API_URL = 'http://127.0.0.1:8000';

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
// Devolve o JSON da resposta (ou null se vier vazia) e lança Error com texto legível se falhar.
async function requisicao(rota, metodo = 'GET', corpo = null) {
  const opcoes = { method: metodo, headers: {} };
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