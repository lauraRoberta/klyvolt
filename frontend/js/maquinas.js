/* KLYVOLT · maquinas.js — CRUD de máquinas pela API (GET/POST/PUT/DELETE /maquinas) */
(function () {
  'use strict';
  const { requisicao, fmt, toast, confirmar, ocupado, el } = KV;
  const $ = id => document.getElementById(id);
  const lista = KV.lista($('machineList'), { vazio: 'Nenhuma máquina cadastrada.', filtro: (c, f) => c.dataset.sensor === f });
  let maquinas = [], setores = [];

  window.filterList = function (f) { KV.marcarAba(window.event && window.event.target); lista.filtroAtual = f; lista.aplicar(); };
  window.searchMachine = function () { lista.busca = $('searchInput').value; lista.aplicar(); };

  async function carregar() {
    lista.carregando();
    try {
      [maquinas, setores] = await Promise.all([requisicao('/maquinas'), requisicao('/setores')]);
      KV.preencherSelect($('idSetor'), setores, { valor: x => x.id_setor, rotulo: x => x.nome_setor, vazio: 'Selecione um setor cadastrado' });
      lista.render(maquinas, m => {
        const c = KV.card({ id: m.id_maquina, badge: m.nome_setor || 'Setor', dataset: { sensor: m.qtd_sensores ? 'com' : 'sem' } });
        c.linha(m.nome_maquina, 'fa-industry', 'rule-name');
        c.linha(m.descricao_maquina, 'fa-align-left');
        if (m.potencia_nominal != null) c.linha(`Potência nominal: ${fmt.num(m.potencia_nominal)} W`, 'fa-plug');
        if (m.numero_serie) c.linha(`Série: ${m.numero_serie}`, 'fa-barcode');
        c.linha(m.qtd_sensores === 0 ? 'Nenhum sensor vinculado' : m.qtd_sensores === 1 ? '1 sensor vinculado' : `${m.qtd_sensores} sensores vinculados`, 'fa-microchip');
        if (m.consumo_kwh != null) {
          const box = el('div', 'consumo-box');
          const h = el('div', 'consumo-header'); h.append(KV.icon('fa-bolt'), ' Consumo Registrado');
          box.append(h, el('div', 'consumo-value', fmt.num(m.consumo_kwh) + ' kWh'));
          c.corpo.append(box);
          if (m.custo_estimado != null) c.linha('Custo estimado: ' + fmt.brl(m.custo_estimado), 'fa-coins', 'kv-cost');
        }
        c.ver.addEventListener('click', () => openModal('view', m));
        return c.card;
      });
    } catch (erro) { lista.erro(erro.message); toast(erro.message, 'erro'); }
  }

  function openModal(mode, m = null) {
    const inputs = document.querySelectorAll('.modal-body input, .modal-body select');
    const summary = $('consumoSummary');
    summary.style.display = 'none';
    if (mode === 'create') {
      if (!KV.isAdmin()) return toast('Somente administradores cadastram máquinas.', 'aviso');
      if (!setores.length) return toast('Cadastre um setor antes de adicionar máquinas.', 'aviso');
      $('modalTitle').innerText = 'Nova Máquina';
      inputs.forEach(i => { i.value = ''; i.disabled = false; });
      $('idSetor').value = setores.length === 1 ? String(setores[0].id_setor) : '';
      KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Salvar Máquina', 'btn-confirm', b => saveMachine(null, b)]]);
    } else {
      $('nomeMaquina').value = m.nome_maquina;
      $('descricaoMaquina').value = m.descricao_maquina;
      $('potenciaNominal').value = m.potencia_nominal ?? '';
      $('numeroSerieMaquina').value = m.numero_serie || '';
      $('idSetor').value = String(m.id_setor);
      if (mode === 'view') {
        $('modalTitle').innerText = 'Máquina ' + fmt.id(m.id_maquina);
        $('sumConsumo').innerText = fmt.num(m.consumo_kwh || 0) + ' kWh';
        $('sumCusto').innerText = m.custo_estimado != null ? fmt.brl(m.custo_estimado) : (m.consumo_kwh ? 'Defina a tarifa' : fmt.brl(0));
        $('sumSensores').innerText = String(m.qtd_sensores);
        summary.style.display = 'flex';
        inputs.forEach(i => i.disabled = true);
        KV.botoesModal($('modalActions'), [['Excluir', 'btn-cancel', () => deleteMachine(m)], ['Editar', 'btn-confirm', () => openModal('edit', m)]]);
      } else {
        $('modalTitle').innerText = 'Editando Máquina ' + fmt.id(m.id_maquina);
        inputs.forEach(i => i.disabled = false);
        KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Atualizar', 'btn-confirm', b => saveMachine(m.id_maquina, b)]]);
      }
    }
    $('modalOverlay').style.display = 'flex';
  }
  function closeModal() { $('modalOverlay').style.display = 'none'; }
  window.openModal = openModal; window.closeModal = closeModal;
  KV.prepararModal($('modalOverlay'), closeModal);

  async function saveMachine(id, botao) {
    const potTxt = $('potenciaNominal').value.trim();
    const pot = potTxt === '' ? null : KV.numero(potTxt);
    const dados = { nome_maquina: $('nomeMaquina').value.trim(), descricao_maquina: $('descricaoMaquina').value.trim(),
      potencia_nominal: pot, numero_serie: $('numeroSerieMaquina').value.trim() || null, id_setor: Number($('idSetor').value) };
    if (!dados.nome_maquina || !dados.descricao_maquina || !dados.id_setor) return toast('Preencha todos os campos obrigatórios (*).', 'aviso');
    if (pot !== null && (!Number.isFinite(pot) || pot <= 0)) return toast('A potência nominal deve ser maior que zero.', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      await requisicao(id ? `/maquinas/${id}` : '/maquinas', id ? 'PUT' : 'POST', dados);
      closeModal(); toast(id ? 'Máquina atualizada.' : 'Máquina cadastrada.'); await carregar();
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  }

  async function deleteMachine(m) {
    const n = m.qtd_sensores;
    const ok = await confirmar({ titulo: 'Excluir máquina ' + fmt.id(m.id_maquina), mensagem: `Tem certeza que deseja excluir "${m.nome_maquina}"?`,
      detalhe: `Os consumos registrados${n ? ` e ${n === 1 ? 'o sensor vinculado' : `os ${n} sensores vinculados`} (com suas leituras)` : ''} desta máquina também serão excluídos.` });
    if (!ok) return;
    try { await requisicao(`/maquinas/${m.id_maquina}`, 'DELETE'); closeModal(); toast('Máquina excluída.'); await carregar(); }
    catch (erro) { toast(erro.message, 'erro'); }
  }

  KV.pronto.then(carregar).catch(() => {});
})();
