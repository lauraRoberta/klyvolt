/* KLYVOLT · decisoes.js — regras de decisão (/decisoes) e acionamentos (/tomadas-decisao)
   As regras ativas em kWh são avaliadas pelo banco a cada leitura/consumo. O sistema
   registra o alerta; a ação física (ex.: desligar a máquina) é feita pela equipe. */
(function () {
  'use strict';
  const { requisicao, fmt, toast, confirmar, ocupado, el } = KV;
  const $ = id => document.getElementById(id);
  const CRITERIOS = { valor_medido_kwh: 'Leitura individual', consumo_kwh: 'Consumo agregado' };
  const STATUS = { pendente: 'Pendente', executada: 'Executada', cancelada: 'Cancelada', falha: 'Falha' };
  const lista = KV.lista($('decisionList'), {
    vazio: 'Nenhuma regra de decisão cadastrada.',
    filtro: (c, f) => f === '=' ? c.dataset.operador === '=' : c.dataset.operador.startsWith(f)
  });
  let regras = [], tomadas = new Map();

  window.filterList = function (f) { KV.marcarAba(window.event && window.event.target); lista.filtroAtual = f; lista.aplicar(); };
  window.searchRule = function () { lista.busca = $('searchInput').value; lista.aplicar(); };
  const rotuloCriterio = c => CRITERIOS[c] || c;
  const condicao = r => `${rotuloCriterio(r.criterio_acionado)} ${r.operador} ${fmt.num(r.limite_referencia)} ${r.unidade_limite}`;

  async function carregar() {
    lista.carregando();
    try {
      const [d, t] = await Promise.all([requisicao('/decisoes'), requisicao('/tomadas-decisao?limite=1000')]);
      regras = d;
      tomadas = new Map();
      for (const x of t) { const a = tomadas.get(x.id_decisao) || []; a.push(x); tomadas.set(x.id_decisao, a); }
      lista.render(regras, r => {
        const c = KV.card({ id: r.id_decisao, badge: r.ativo ? 'Ativa' : 'Inativa', badgeClasse: r.ativo ? 'status-executada' : 'status-pendente', dataset: { operador: r.operador } });
        c.linha(r.nome_decisao, 'fa-scale-balanced', 'rule-name');
        c.linha('Critério: ' + rotuloCriterio(r.criterio_acionado), 'fa-filter');
        c.linha(r.acionamentos ? `${r.acionamentos} acionamento${r.acionamentos > 1 ? 's' : ''} · último em ${fmt.data(r.ultimo_acionamento)}` : 'Nenhum acionamento registrado', 'fa-bell');
        c.linha('Condição: ' + condicao(r), null, 'ref-value');
        c.ver.addEventListener('click', () => openModal('view', r));
        return c.card;
      });
    } catch (erro) { lista.erro(erro.message); toast(erro.message, 'erro'); }
  }

  function modoFormulario(ativo) {
    document.querySelector('.modal-info').style.display = ativo ? 'none' : '';
    $('descGroup').style.display = ativo ? 'none' : '';
    $('tomadasGroup').style.display = ativo ? 'none' : '';
    $('ruleForm').style.display = ativo ? 'block' : 'none';
  }

  // Lista dos acionamentos com o status registrado pela equipe
  function desenharTomadas(r) {
    const box = $('tomadasLista'); box.replaceChildren();
    const t = (tomadas.get(r.id_decisao) || []).slice(0, 5);
    if (!t.length) box.append(el('p', null, 'Esta regra ainda não foi acionada.'));
    for (const x of t) {
      const p = el('p');
      p.append(el('strong', null, fmt.data(x.data_tomada_decisao)), document.createTextNode(` · ${fmt.num(x.valor_referencia)} kWh · ${STATUS[x.status_execucao] || x.status_execucao}`));
      if (x.status_execucao === 'pendente' && KV.podeOperar()) {
        for (const [novo, rotulo] of [['executada', 'Marcar executada'], ['cancelada', 'Cancelar']]) {
          const b = el('button', 'kv-link-btn', rotulo); b.type = 'button'; b.style.marginLeft = '12px';
          b.addEventListener('click', () => atualizarTomada(x, novo, r, b));
          p.append(b);
        }
      }
      box.append(p);
    }
  }
  async function atualizarTomada(t, status, regra, botao) {
    ocupado(botao, true);
    try {
      const atual = await requisicao(`/tomadas-decisao/${t.id_tomada_decisao}`, 'PUT', { status_execucao: status, observacao: t.observacao });
      Object.assign(t, atual);
      toast(`Acionamento marcado como ${STATUS[status].toLowerCase()}.`);
      desenharTomadas(regra);
    } catch (erro) { toast(erro.message, 'erro'); ocupado(botao, false); }
  }

  function openModal(mode, r = null) {
    if (mode === 'view') {
      modoFormulario(false);
      $('modalTitle').innerText = 'Detalhes da Regra de Decisão';
      $('modalId').innerText = fmt.id(r.id_decisao);
      $('modalNome').innerText = r.nome_decisao + (r.ativo ? '' : ' (inativa)');
      $('modalCriterio').innerText = rotuloCriterio(r.criterio_acionado);
      $('modalCondicao').innerText = condicao(r);
      $('modalLimite').innerText = `${fmt.num(r.limite_referencia)} ${r.unidade_limite}`;
      $('modalDescricao').innerText = r.descricao_decisao || 'Sem descrição.';
      desenharTomadas(r);
      KV.botoesModal($('modalActions'), [['Excluir', 'btn-cancel', () => deleteRule(r)], ['Editar', 'btn-confirm', () => openModal('edit', r)]]);
    } else {
      if (!KV.isAdmin()) return toast('Somente administradores cadastram e alteram regras.', 'aviso');
      modoFormulario(true);
      const editar = mode === 'edit';
      $('modalTitle').innerText = editar ? 'Editando Regra ' + fmt.id(r.id_decisao) : 'Nova Regra de Decisão';
      $('nomeDecisao').value = editar ? r.nome_decisao : '';
      $('descricaoDecisao').value = editar ? (r.descricao_decisao || '') : '';
      $('criterioDecisao').value = editar && CRITERIOS[r.criterio_acionado] ? r.criterio_acionado : 'valor_medido_kwh';
      $('operadorDecisao').value = editar ? r.operador : '>';
      $('limiteDecisao').value = editar ? r.limite_referencia : '';
      $('ativoDecisao').value = editar ? String(r.ativo) : 'true';
      KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], [editar ? 'Atualizar Regra' : 'Salvar Regra', 'btn-confirm', b => saveRule(editar ? r.id_decisao : null, b)]]);
    }
    $('modalOverlay').style.display = 'flex';
  }
  function closeModal() { $('modalOverlay').style.display = 'none'; }
  window.openModal = openModal; window.closeModal = closeModal;
  KV.prepararModal($('modalOverlay'), closeModal);

  async function saveRule(id, botao) {
    const limiteTxt = $('limiteDecisao').value.trim(), limite = KV.numero(limiteTxt);
    const dados = { nome_decisao: $('nomeDecisao').value.trim(), descricao_decisao: $('descricaoDecisao').value.trim() || null,
      criterio_acionado: $('criterioDecisao').value, operador: $('operadorDecisao').value,
      limite_referencia: limite, unidade_limite: 'kWh', ativo: $('ativoDecisao').value === 'true' };
    if (!dados.nome_decisao || limiteTxt === '' || !Number.isFinite(limite)) return toast('Preencha todos os campos obrigatórios (*).', 'aviso');
    if (limite < 0) return toast('O limite não pode ser negativo.', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      await requisicao(id ? `/decisoes/${id}` : '/decisoes', id ? 'PUT' : 'POST', dados);
      closeModal();
      toast(id ? 'Regra atualizada.' : 'Regra cadastrada. Ela será avaliada a cada nova ' + (dados.criterio_acionado === 'consumo_kwh' ? 'medição de consumo.' : 'leitura.'));
      await carregar();
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  }

  async function deleteRule(r) {
    if (r.acionamentos) return toast(`Esta regra possui ${r.acionamentos} acionamento(s) no histórico e não pode ser excluída. Para interromper a avaliação, edite-a e marque como "Inativa".`, 'aviso', 9000);
    const ok = await confirmar({ titulo: 'Excluir regra ' + fmt.id(r.id_decisao), mensagem: `Tem certeza que deseja excluir a regra "${r.nome_decisao}"?`, detalhe: 'Esta ação não pode ser desfeita.' });
    if (!ok) return;
    try { await requisicao(`/decisoes/${r.id_decisao}`, 'DELETE'); closeModal(); toast('Regra excluída.'); await carregar(); }
    catch (erro) { toast(erro.message, 'erro'); }
  }

  KV.pronto.then(carregar).catch(() => {});
})();
