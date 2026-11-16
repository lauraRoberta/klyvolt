// js/crud.js - código comum das telas de cadastro (usuário, setor, máquina, sensor...).
// O HTML da página diz o que existe nela:
//   <main data-rota="/setores" data-chave="id_setor" data-nome="setor"
//         data-editar="sim|nao" data-excluir="sim|nao">
//   campo do formulário:  data-campo="nome_do_campo_na_api"
//   coluna da tabela:     <th data-campo="..." data-formato="data|datahora|numero">
//   select ligado a outra tabela: data-origem="/rota" data-valor="chave" data-texto="{nome} (#{id})"
// Depende de api.js (requisicao, mostrarMensagem, formatarDataHora), carregado antes com defer.
// Regras específicas de uma tela (opcional), em outro arquivo carregado antes deste:
//   window.crudHooks = { validar(corpo, editando), transformarRegistro(registro, ctx) }

(async function () {
  const principal = document.querySelector('main[data-rota]');
  const ROTA = principal.dataset.rota;
  const CHAVE = principal.dataset.chave;
  const NOME = principal.dataset.nome;
  const PODE_EDITAR = principal.dataset.editar === 'sim';
  const PODE_EXCLUIR = principal.dataset.excluir === 'sim';
  const hooks = window.crudHooks || {};

  const formulario = document.querySelector('#form-registro');
  const tituloForm = document.querySelector('#titulo-formulario');
  const botaoSalvar = document.querySelector('#botao-salvar');
  const botaoCancelar = document.querySelector('#botao-cancelar');
  const lista = document.querySelector('#lista-registros');
  const mensagemEl = document.querySelector('#mensagem');

  const campos = [...formulario.querySelectorAll('[data-campo]')];
  const colunas = [...document.querySelectorAll('thead th')].map(th => ({
    campo: th.dataset.campo,
    formato: th.dataset.formato
  }));

  // Id do registro em edição; null = modo de cadastro.
  let idEdicao = null;
  // Registros das tabelas de origem (campo -> lista) e textos para exibir (campo -> Map id -> texto).
  const listas = {};
  const rotulos = {};

  for (const c of campos) {
    if (c.type === 'password') c.dataset.placeholderOriginal = c.placeholder;
  }

  // ---------- auxiliares ----------
  function rotuloDe(campo) {
    const label = document.querySelector(`label[for="${campo.id}"]`);
    return label ? label.textContent : campo.dataset.campo;
  }

  // "{nome} (#{id})" vira "Máquina 1 (#3)"; sem chaves, usa o campo direto.
  function textoOpcao(modelo, registro) {
    if (modelo.includes('{')) {
      return modelo.replace(/\{(\w+)\}/g, (_, chave) => registro[chave] ?? '');
    }
    return String(registro[modelo] ?? '');
  }

  // ---------- selects ligados a outras tabelas ----------
  async function carregarOrigens() {
    const selects = campos.filter(c => c.dataset.origem);
    await Promise.all(selects.map(async select => {
      const campo = select.dataset.campo;
      const atual = select.value;
      const registros = await requisicao(select.dataset.origem);
      listas[campo] = registros;
      const mapa = new Map();

      select.replaceChildren();
      const padrao = document.createElement('option');
      padrao.value = '';
      if (select.required) {
        padrao.disabled = true;
        padrao.textContent = registros.length ? 'Selecione...' : 'Nenhum cadastro disponível: cadastre antes';
      } else {
        padrao.textContent = '(nenhum)';
      }
      padrao.setAttribute('selected', '');
      select.append(padrao);

      for (const r of registros) {
        const valor = String(r[select.dataset.valor]);
        const texto = textoOpcao(select.dataset.texto, r);
        mapa.set(valor, texto);
        const opcao = document.createElement('option');
        opcao.value = valor;
        opcao.textContent = texto;
        select.append(opcao);
      }
      rotulos[campo] = mapa;
      if (atual && mapa.has(atual)) select.value = atual;
    }));
  }

  // ---------- modo cadastro / edição ----------
  function definirModo(editando) {
    tituloForm.textContent = editando ? `Editar ${NOME} #${idEdicao}` : `Cadastrar ${NOME}`;
    botaoSalvar.textContent = editando ? 'Salvar alterações' : 'Cadastrar';
    botaoCancelar.hidden = !editando;
    for (const c of campos) {
      // Senha: obrigatória só no cadastro; na edição, em branco = manter a atual.
      if (c.dataset.obrigatorioCadastro === 'sim') c.required = !editando;
      if (c.type === 'password') {
        c.placeholder = editando ? 'Deixe em branco para manter' : c.dataset.placeholderOriginal;
      }
    }
  }

  function limparFormulario() {
    formulario.reset();
    idEdicao = null;
    definirModo(false);
  }

  function editar(registro) {
    let aviso = null;
    const contexto = { listas, avisar: texto => { aviso = texto; } };
    const dados = hooks.transformarRegistro ? hooks.transformarRegistro(registro, contexto) : registro;
    idEdicao = registro[CHAVE];
    for (const c of campos) {
      if (c.type === 'password') { c.value = ''; continue; } // a API nunca devolve senha ou token
      let valor = dados[c.dataset.campo];
      if (valor === null || valor === undefined) valor = '';
      if (c.type === 'datetime-local') valor = String(valor).slice(0, 16);
      c.value = String(valor);
    }
    definirModo(true);
    if (aviso) mostrarMensagem(mensagemEl, aviso, true); else esconderMensagem(mensagemEl);
    campos[0].focus();
  }

  // ---------- leitura e validação do formulário ----------
  function primeiroInvalido() {
    for (const c of campos) {
      if (!c.checkValidity()) {
        const texto = c.validity.patternMismatch && c.title ? c.title : c.validationMessage;
        return { campo: c, texto: `${rotuloDe(c)}: ${texto}` };
      }
    }
    return null;
  }

  function montarCorpo() {
    const corpo = {};
    for (const c of campos) {
      const chave = c.dataset.campo;
      const bruto = c.type === 'password' ? c.value : c.value.trim();
      if (bruto === '') {
        if (c.dataset.omitirVazio === 'sim') continue; // não envia (senha/token em branco)
        corpo[chave] = null;                           // campo opcional vazio
        continue;
      }
      if (c.type === 'number' || c.dataset.numerico === 'sim') corpo[chave] = Number(bruto);
      else if (c.type === 'datetime-local') corpo[chave] = bruto.length === 16 ? bruto + ':00' : bruto;
      else corpo[chave] = bruto;
    }
    return corpo;
  }

  // ---------- tabela ----------
  function textoCelula(registro, coluna) {
    const valor = registro[coluna.campo];
    if (valor === null || valor === undefined || valor === '') return '—';
    const mapa = rotulos[coluna.campo];
    if (mapa && mapa.has(String(valor))) return mapa.get(String(valor));
    if (coluna.formato === 'data') return String(valor).split('-').reverse().join('/');
    if (coluna.formato === 'datahora') return formatarDataHora(valor);
    if (coluna.formato === 'numero') {
      return Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return String(valor);
  }

  function criarBotao(texto, classe, aoClicar) {
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = classe;
    botao.textContent = texto;
    botao.addEventListener('click', () => aoClicar(botao));
    return botao;
  }

  function exibir(registros) {
    lista.replaceChildren();
    document.querySelector('#total-registros').textContent = `${registros.length} registro(s) exibido(s)`;
    if (registros.length === 0) {
      const linha = lista.insertRow();
      const celula = linha.insertCell();
      celula.colSpan = colunas.length;
      celula.className = 'vazio';
      celula.textContent = 'Nenhum registro cadastrado.';
      return;
    }
    for (const registro of registros) {
      const linha = lista.insertRow();
      for (const coluna of colunas) {
        if (coluna.campo) { linha.insertCell().textContent = textoCelula(registro, coluna); }
      }
      const acoes = linha.insertCell();
      if (PODE_EDITAR) acoes.append(criarBotao('Editar', 'botao botao-secundario', () => editar(registro)));
      if (PODE_EXCLUIR) acoes.append(criarBotao('Excluir', 'botao botao-secundario', botao => excluir(registro, botao)));
    }
  }

  async function listar() {
    const registros = await requisicao(ROTA);
    registros.sort((a, b) => a[CHAVE] - b[CHAVE]);
    exibir(registros);
  }

  async function excluir(registro, botao) {
    const id = registro[CHAVE];
    if (!confirm(`Excluir o registro #${id}?`)) return;
    botao.disabled = true;
    try {
      await requisicao(`${ROTA}/${id}`, 'DELETE');
      if (idEdicao === id) limparFormulario();
      mostrarMensagem(mensagemEl, 'Registro excluído com sucesso.');
      try { await listar(); }
      catch (erro) { mostrarMensagem(mensagemEl, `Registro excluído, mas a lista não foi atualizada: ${erro.message}`, true); }
    } catch (erro) {
      mostrarMensagem(mensagemEl, erro.message, true);
    } finally {
      botao.disabled = false;
    }
  }

  // ---------- eventos ----------
  formulario.addEventListener('submit', async evento => {
    evento.preventDefault();
    esconderMensagem(mensagemEl);
    const invalido = primeiroInvalido();
    if (invalido) {
      mostrarMensagem(mensagemEl, invalido.texto, true);
      invalido.campo.focus();
      return;
    }
    const editando = idEdicao !== null;
    const corpo = montarCorpo();
    const erroRegra = hooks.validar ? hooks.validar(corpo, editando) : null;
    if (erroRegra) {
      mostrarMensagem(mensagemEl, erroRegra, true);
      return;
    }
    botaoSalvar.disabled = true;
    try {
      await requisicao(editando ? `${ROTA}/${idEdicao}` : ROTA, editando ? 'PUT' : 'POST', corpo);
      limparFormulario();
      mostrarMensagem(mensagemEl, editando ? 'Registro atualizado com sucesso.' : 'Cadastro realizado com sucesso.');
      try { await listar(); }
      catch (erro) { mostrarMensagem(mensagemEl, `Registro salvo, mas a lista não foi atualizada: ${erro.message}`, true); }
    } catch (erro) {
      mostrarMensagem(mensagemEl, erro.message, true);
    } finally {
      botaoSalvar.disabled = false;
    }
  });

  document.querySelector('#botao-limpar').addEventListener('click', limparFormulario);
  botaoCancelar.addEventListener('click', limparFormulario);
  document.querySelector('#botao-listar').addEventListener('click', async () => {
    try {
      await carregarOrigens();
      await listar();
      mostrarMensagem(mensagemEl, 'Lista atualizada.');
    } catch (erro) { mostrarMensagem(mensagemEl, erro.message, true); }
  });

  // ---------- início ----------
  definirModo(false);
  try { await carregarOrigens(); }
  catch (erro) { mostrarMensagem(mensagemEl, erro.message, true); }
  try { await listar(); }
  catch (erro) {
    exibir([]);
    mostrarMensagem(mensagemEl, erro.message, true);
  }
})();
