/* KLYVOLT · consumos.js — consumos por máquina e período pela API (/consumos)
   Indicadores do mês, custo (tarifa da empresa) e comparação com o mês anterior.
   O kWh pode ser calculado pela soma das leituras do período (GET /consumos/calcular). */
(function () {
  'use strict';
  const { requisicao, fmt, toast, confirmar, ocupado, el } = KV;
  const $ = id => document.getElementById(id);
  const sem = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  // As abas filtram pelo tipo da máquina (nome), tolerando grafias como "overlock"
  const lista = KV.lista($('consumoList'), { vazio: 'Nenhum consumo registrado.', filtro: (c, f) => c.dataset.maquina.includes(f.slice(0, 6)) });
  let consumos = [], maquinas = [], tarifa = null;
  const horas = (a, b) => (KV.parseLocal(b) - KV.parseLocal(a)) / 36e5;

  window.filterList = function (f) { KV.marcarAba(window.event && window.event.target); lista.filtroAtual = f; lista.aplicar(); };
  window.searchConsumo = function () { lista.busca = $('searchInput').value; lista.aplicar(); };

  function barras(valores, inicio) {
    if (!valores || valores.length < 2) return null;
    const n = Math.min(12, valores.length), passo = valores.length / n, soma = [];
    for (let i = 0; i < n; i++) soma.push(valores.slice(Math.floor(i * passo), Math.floor((i + 1) * passo)).reduce((s, x) => s + x, 0));
    return KV.grafico(soma);
  }

  async function carregar() {
    lista.carregando();
    try {
      const [c, m, perfil] = await Promise.all([requisicao('/consumos'), requisicao('/maquinas'), requisicao('/auth/me')]);
      consumos = c; maquinas = m; tarifa = perfil.tarifa_kwh;
      KV.preencherSelect($('idMaquina'), maquinas, { valor: x => x.id_maquina, rotulo: x => x.nome_maquina, vazio: 'Selecione uma máquina cadastrada' });
      lista.render(consumos, r => {
        const nome = r.nome_maquina || 'Máquina ' + fmt.id(r.id_maquina);
        const c = KV.card({ id: r.id_consumo, badge: 'Registrado', dataset: { maquina: sem(nome) } });
        c.linha(nome, 'fa-industry', 'rule-name');
        c.linha(fmt.data(r.data_inicio) + ' → ' + fmt.data(r.data_fim), 'fa-calendar-day');
        c.linha('Duração: ' + fmt.num(r.duracao_h) + ' h', 'fa-clock');
        c.linha(r.leituras_agregadas ? `${r.leituras_agregadas} leituras agregadas` : 'Sem leituras agregadas', 'fa-wave-square');
        const box = el('div', 'consumo-box');
        const head = el('div', 'consumo-header'); head.append(KV.icon('fa-bolt'), ' Consumo Agregado');
        box.append(head, el('div', 'consumo-value', fmt.num(r.consumo_kwh) + ' kWh'));
        const g = barras(r.valores_leituras); if (g) box.append(g);
        c.corpo.append(box);
        if (r.custo_estimado != null) c.linha('Custo estimado: ' + fmt.brl(r.custo_estimado), 'fa-coins', 'kv-cost');
        c.ver.addEventListener('click', () => openModal('view', r));
        return c.card;
      });
      kpis();
    } catch (erro) { lista.erro(erro.message); toast(erro.message, 'erro'); }
  }

  function kpis() {
    document.querySelectorAll('.kpi-grid').forEach(g => g.hidden = consumos.length === 0);
    if (!consumos.length) return;
    const agora = new Date();
    const doMes = (ano, mes) => consumos.filter(r => { const d = KV.parseLocal(r.data_inicio); return d && d.getFullYear() === ano && d.getMonth() === mes; });
    const soma = arr => arr.reduce((n, r) => n + Number(r.consumo_kwh), 0);
    const ant = new Date(agora.getFullYear(), agora.getMonth() - 1, 1);
    const atual = doMes(agora.getFullYear(), agora.getMonth()), anterior = doMes(ant.getFullYear(), ant.getMonth());
    const total = soma(atual), totalAnt = soma(anterior);
    const picos = atual.map(r => Number(r.consumo_kwh) / horas(r.data_inicio, r.data_fim)).filter(Number.isFinite);
    $('kpiTotal').textContent = fmt.num(total);
    $('kpiMedia').textContent = fmt.num(total / agora.getDate());
    $('kpiPico').textContent = fmt.num(picos.length ? Math.max(...picos) : 0);
    $('kpiCusto').textContent = tarifa != null ? fmt.num(total * tarifa) : '—';
    $('kpiCustoUnit').textContent = tarifa != null ? 'R$' : 'Defina a tarifa em Empresa';
    $('kpiAnterior').textContent = fmt.num(totalAnt);
    $('kpiVariacao').textContent = totalAnt > 0 ? 'kWh · ' + fmt.pct((total - totalAnt) / totalAnt * 100) + ' no mês atual' : 'kWh · sem base de comparação';
    $('kpiTarifa').textContent = tarifa != null ? new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(tarifa) : '—';
    $('kpiTarifaUnit').textContent = tarifa != null ? 'R$/kWh' : 'não definida';
  }

  /* ---------- modal ---------- */
  let modo = 'view';
  function resumoModal() {
    const ini = $('dataInicio').value, fim = $('dataFim').value, kwh = KV.numero($('consumoKwh').value);
    const h = ini && fim ? horas(ini, fim) : NaN;
    $('sumKwh').innerText = Number.isFinite(kwh) ? fmt.num(kwh) + ' kWh' : '-- kWh';
    $('sumDuracao').innerText = Number.isFinite(h) && h > 0 ? fmt.num(h) + ' h' : '-- h';
    $('sumMedia').innerText = Number.isFinite(kwh) && h > 0 ? fmt.num(kwh / h) + ' kWh' : '-- kWh';
  }
  function openModal(mode, r = null) {
    modo = mode;
    const inputs = document.querySelectorAll('.modal-body input, .modal-body select');
    const info = $('maquinaInfoGroup'), seletor = $('idMaquina').closest('.input-group');
    if (mode === 'create') {
      if (!KV.podeOperar()) return toast('Seu perfil (Visualizador) permite apenas consultas.', 'aviso');
      if (!maquinas.length) return toast('Cadastre uma máquina antes de registrar consumos.', 'aviso');
      $('modalTitle').innerText = 'Novo Registro de Consumo';
      inputs.forEach(i => { i.value = ''; i.disabled = false; });
      $('idMaquina').value = maquinas.length === 1 ? String(maquinas[0].id_maquina) : '';
      info.style.display = 'none'; seletor.style.display = '';
      KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Salvar Registro', 'btn-confirm', b => saveConsumo(null, b)]]);
    } else {
      $('dataInicio').value = fmt.inputDT(r.data_inicio);
      $('dataFim').value = fmt.inputDT(r.data_fim);
      $('consumoKwh').value = r.consumo_kwh;
      $('idMaquina').value = String(r.id_maquina);
      $('maquinaNome').innerText = r.nome_maquina || fmt.id(r.id_maquina);
      info.style.display = 'block';
      if (mode === 'view') {
        $('modalTitle').innerText = 'Consumo ' + fmt.id(r.id_consumo);
        seletor.style.display = 'none';
        inputs.forEach(i => i.disabled = true);
        KV.botoesModal($('modalActions'), [['Excluir', 'btn-cancel', () => deleteConsumo(r)], ['Editar', 'btn-confirm', () => openModal('edit', r)]]);
      } else {
        $('modalTitle').innerText = 'Editando Consumo ' + fmt.id(r.id_consumo);
        info.style.display = 'none'; seletor.style.display = '';
        inputs.forEach(i => i.disabled = false);
        KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Atualizar', 'btn-confirm', b => saveConsumo(r.id_consumo, b)]]);
      }
    }
    resumoModal();
    $('modalOverlay').style.display = 'flex';
  }
  function closeModal() { $('modalOverlay').style.display = 'none'; }
  window.openModal = openModal; window.closeModal = closeModal;
  KV.prepararModal($('modalOverlay'), closeModal);
  ['dataInicio', 'dataFim', 'consumoKwh'].forEach(id => $(id).addEventListener('input', resumoModal));

  // Consumo do período = soma das leituras dos sensores da máquina (preenche se o campo estiver vazio)
  async function calcularPeriodo() {
    if (modo === 'view') return;
    const idMaquina = Number($('idMaquina').value), ini = $('dataInicio').value, fim = $('dataFim').value;
    if (!idMaquina || !ini || !fim || new Date(fim) <= new Date(ini) || $('consumoKwh').value.trim() !== '') return;
    try {
      const q = new URLSearchParams({ id_maquina: idMaquina, inicio: ini, fim });
      const r = await requisicao('/consumos/calcular?' + q);
      if (r.leituras > 0 && $('consumoKwh').value.trim() === '') {
        $('consumoKwh').value = Number(r.total_kwh).toFixed(2);
        resumoModal();
        toast(`Consumo calculado a partir de ${r.leituras} leituras do período. Você pode ajustar o valor.`, 'info');
      }
    } catch (e) { /* cálculo opcional */ }
  }
  ['idMaquina', 'dataInicio', 'dataFim'].forEach(id => $(id).addEventListener('change', calcularPeriodo));

  async function saveConsumo(id, botao) {
    const inicio = $('dataInicio').value, fim = $('dataFim').value, kwhTxt = $('consumoKwh').value.trim(), kwh = KV.numero(kwhTxt);
    const idMaquina = Number($('idMaquina').value);
    if (!inicio || !fim || kwhTxt === '' || !Number.isFinite(kwh) || !idMaquina) return toast('Preencha todos os campos obrigatórios (*).', 'aviso');
    if (new Date(fim) <= new Date(inicio)) return toast('A data final deve ser posterior à data inicial.', 'aviso');
    if (kwh < 0) return toast('O consumo não pode ser negativo.', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      const salvo = await requisicao(id ? `/consumos/${id}` : '/consumos', id ? 'PUT' : 'POST',
        { data_inicio: inicio, data_fim: fim, consumo_kwh: kwh, id_maquina: idMaquina });
      closeModal();
      toast(id ? 'Consumo atualizado.' : 'Consumo registrado. Leituras do período foram agregadas automaticamente.');
      if (salvo.decisoes_acionadas && salvo.decisoes_acionadas.length) toast('Regra de decisão acionada: ' + salvo.decisoes_acionadas.join(', ') + '.', 'aviso', 7000);
      await carregar();
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  }

  async function deleteConsumo(r) {
    const ok = await confirmar({ titulo: 'Excluir consumo ' + fmt.id(r.id_consumo),
      mensagem: `Excluir o registro de ${fmt.num(r.consumo_kwh)} kWh de ${r.nome_maquina || 'máquina'}?`,
      detalhe: r.leituras_agregadas ? `As ${r.leituras_agregadas} leituras agregadas não serão excluídas: elas voltam ao status "Pendente".` : 'Esta ação não pode ser desfeita.' });
    if (!ok) return;
    try { await requisicao(`/consumos/${r.id_consumo}`, 'DELETE'); closeModal(); toast('Consumo excluído.'); await carregar(); }
    catch (erro) { toast(erro.message, 'erro'); }
  }

  KV.pronto.then(carregar).catch(() => {});
})();
