/* KLYVOLT · registrar-consumo.js — formulário rápido "Novo registro" (POST/PUT /consumos)
   Cadastrar → cria o consumo · Salvar Alterações → atualiza o registro criado (ou ?id=)
   Consumo em branco → calculado pela soma das leituras do período. */
(function () {
  'use strict';
  const { requisicao, fmt, toast, ocupado } = KV;
  const $ = id => document.getElementById(id);
  let idAtual = null;

  // Aceita "AAAA-MM-DD" (campo de data) ou "DD/MM/AAAA" (digitado)
  function lerData(valor) {
    const v = String(valor || '').trim();
    let m = v.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
    m = v.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
    return null;
  }
  // O período cobre os dias inteiros: início 00:00:00 até fim 23:59:59
  function periodo() {
    const ini = lerData($('data_inicio').value), fim = lerData($('data_fim').value);
    if (!ini || !fim) return null;
    const f = new Date(fim); f.setHours(23, 59, 59, 0);
    return { inicio: KV.toLocalISO(ini), fim: KV.toLocalISO(f), iniDate: ini, fimDate: f };
  }

  async function carregar() {
    try {
      const m = await requisicao('/maquinas');
      KV.preencherSelect($('maquina'), m, { valor: x => x.id_maquina, rotulo: x => x.nome_maquina, vazio: 'Selecionar máquina cadastrada' });
      $('maquina').options[0].disabled = true;
      if (!m.length) toast('Nenhuma máquina cadastrada. Cadastre uma em Máquinas antes de registrar consumo.', 'aviso', 8000);
      const id = Number(new URLSearchParams(location.search).get('id'));
      if (id) await abrir(id);
      atualizarBotoes();
    } catch (erro) { toast(erro.message, 'erro'); }
  }

  async function abrir(id) {
    try {
      const c = await requisicao(`/consumos/${id}`);
      idAtual = c.id_consumo;
      $('id_consumo').value = fmt.id(c.id_consumo);
      $('data_inicio').value = fmt.inputDate(c.data_inicio);
      $('data_fim').value = fmt.inputDate(c.data_fim);
      $('consumo').value = fmt.num(c.consumo_kwh);
      $('maquina').value = String(c.id_maquina);
    } catch (erro) { toast(erro.message, 'erro'); }
  }

  function atualizarBotoes() {
    $('btnSalvar').disabled = !idAtual;
    $('btnSalvar').title = idAtual ? 'Salvar alterações do consumo ' + fmt.id(idAtual) : 'Cadastre um consumo para poder editá-lo';
  }

  async function valores() {
    const p = periodo(), idMaquina = Number($('maquina').value);
    if (!p || !idMaquina) { toast('Informe data início, data fim e máquina.', 'aviso'); return null; }
    if (p.fimDate <= p.iniDate) { toast('A data final deve ser igual ou posterior à data inicial.', 'aviso'); return null; }
    let kwh = KV.numero($('consumo').value);
    if ($('consumo').value.trim() === '') {
      const r = await requisicao('/consumos/calcular?' + new URLSearchParams({ id_maquina: idMaquina, inicio: p.inicio, fim: p.fim }));
      if (!r.leituras) { toast('Informe o consumo em kWh: não há leituras desta máquina no período para calcular.', 'aviso'); return null; }
      kwh = Number(r.total_kwh);
      $('consumo').value = fmt.num(kwh);
      toast(`Consumo calculado a partir de ${r.leituras} leituras do período.`, 'info');
    }
    if (!Number.isFinite(kwh) || kwh < 0) { toast('Consumo inválido. Use um número maior ou igual a zero, ex: 12,45.', 'aviso'); return null; }
    return { data_inicio: p.inicio, data_fim: p.fim, consumo_kwh: kwh, id_maquina: idMaquina };
  }

  async function salvar(novo, botao) {
    if (!KV.podeOperar()) return toast('Seu perfil (Visualizador) permite apenas consultas.', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      const dados = await valores();
      if (!dados) return;
      const r = await requisicao(novo ? '/consumos' : `/consumos/${idAtual}`, novo ? 'POST' : 'PUT', dados);
      idAtual = r.id_consumo;
      $('id_consumo').value = fmt.id(idAtual);
      toast(novo ? `Consumo ${fmt.id(idAtual)} cadastrado. Leituras do período foram agregadas.` : `Consumo ${fmt.id(idAtual)} atualizado.`);
      if (r.decisoes_acionadas && r.decisoes_acionadas.length) toast('Regra de decisão acionada: ' + r.decisoes_acionadas.join(', ') + '.', 'aviso', 7000);
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); atualizarBotoes(); }
  }

  $('btnCadastrar').addEventListener('click', e => salvar(true, e.currentTarget));
  $('btnSalvar').addEventListener('click', e => { if (idAtual) salvar(false, e.currentTarget); });
  $('btnVoltar').addEventListener('click', () => {
    if (history.length > 1 && document.referrer && new URL(document.referrer).origin === location.origin) history.back();
    else location.href = 'consumos.html';
  });
  document.querySelector('.form-content').addEventListener('submit', e => e.preventDefault());

  KV.pronto.then(carregar).catch(() => {});
})();
