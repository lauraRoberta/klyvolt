/* KLYVOLT · setores.js — CRUD de setores pela API (GET/POST/PUT/DELETE /setores) */
(function () {
  'use strict';
  const { requisicao, fmt, toast, confirmar, ocupado } = KV;
  const DIVISOES = { corte: 'Corte', costura: 'Costura', acabamento: 'Acabamento', estamparia: 'Estamparia', bordado: 'Bordado' };
  const $ = id => document.getElementById(id);
  const lista = KV.lista($('sectorList'), { vazio: 'Nenhum setor cadastrado.', filtro: (c, f) => c.dataset.divisao === f });
  let setores = [], usuarios = [];

  window.filterList = function (divisao) { KV.marcarAba(window.event && window.event.target); lista.filtroAtual = divisao; lista.aplicar(); };
  window.searchSector = function () { lista.busca = $('searchInput').value; lista.aplicar(); };

  async function carregar() {
    lista.carregando();
    try {
      [setores, usuarios] = await Promise.all([requisicao('/setores'), requisicao('/usuarios')]);
      KV.preencherSelect($('idResponsavel'), usuarios.filter(u => u.ativo !== false), {
        valor: x => x.id_usuario, rotulo: x => `${x.nome_usuario} (${x.tipo_usuario})`, vazio: 'Selecione um usuário da empresa'
      });
      lista.render(setores, s => {
        const div = String(s.divisao_setor || '').toLowerCase();
        const c = KV.card({ id: s.id_setor, badge: DIVISOES[div] || s.divisao_setor || 'Sem divisão', dataset: { divisao: div } });
        c.linha(s.nome_setor, 'fa-industry', 'rule-name');
        c.linha(`Responsável: ${s.nome_responsavel || 'Usuário'} (${fmt.id(s.id_usuario_responsavel)})`, 'fa-id-card');
        c.linha(s.qtd_maquinas === 1 ? '1 máquina vinculada' : `${s.qtd_maquinas} máquinas vinculadas`, 'fa-gears');
        c.ver.addEventListener('click', () => openModal('view', s));
        return c.card;
      });
    } catch (erro) { lista.erro(erro.message); toast(erro.message, 'erro'); }
  }

  function openModal(mode, s = null) {
    const inputs = document.querySelectorAll('.modal-body input, .modal-body select');
    const respInfoGroup = $('respInfoGroup');
    if (mode === 'create') {
      if (!KV.isAdmin()) return toast('Somente administradores cadastram setores.', 'aviso');
      $('modalTitle').innerText = 'Novo Setor';
      $('nomeSetor').value = ''; $('divisaoSetor').value = 'corte';
      $('idResponsavel').value = String((KV.perfil() || {}).id_usuario || '');
      respInfoGroup.style.display = 'none';
      inputs.forEach(i => i.disabled = false);
      KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Salvar Setor', 'btn-confirm', b => saveSector(null, b)]]);
    } else {
      $('nomeSetor').value = s.nome_setor;
      $('divisaoSetor').value = String(s.divisao_setor || '').toLowerCase();
      $('idResponsavel').value = String(s.id_usuario_responsavel);
      $('respNome').innerText = `${s.nome_responsavel || 'Usuário'} · ${fmt.id(s.id_usuario_responsavel)}`;
      respInfoGroup.style.display = 'block';
      if (mode === 'view') {
        $('modalTitle').innerText = 'Detalhes do Setor ' + fmt.id(s.id_setor);
        inputs.forEach(i => i.disabled = true);
        KV.botoesModal($('modalActions'), [['Excluir', 'btn-cancel', () => deleteSector(s)], ['Editar', 'btn-confirm', () => openModal('edit', s)]]);
      } else {
        $('modalTitle').innerText = 'Editando Setor ' + fmt.id(s.id_setor);
        inputs.forEach(i => i.disabled = false);
        KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Atualizar Setor', 'btn-confirm', b => saveSector(s.id_setor, b)]]);
      }
    }
    $('modalOverlay').style.display = 'flex';
  }
  function closeModal() { $('modalOverlay').style.display = 'none'; }
  window.openModal = openModal; window.closeModal = closeModal;
  KV.prepararModal($('modalOverlay'), closeModal);

  async function saveSector(id, botao) {
    const dados = { nome_setor: $('nomeSetor').value.trim(), divisao_setor: $('divisaoSetor').value || null,
      id_usuario_responsavel: Number($('idResponsavel').value) };
    if (!dados.nome_setor || !dados.id_usuario_responsavel) return toast('Por favor, preencha todos os campos obrigatórios.', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      await requisicao(id ? `/setores/${id}` : '/setores', id ? 'PUT' : 'POST', dados);
      closeModal(); toast(id ? 'Setor atualizado.' : 'Setor cadastrado.');
      await carregar();
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  }

  async function deleteSector(s) {
    const n = s.qtd_maquinas;
    const ok = await confirmar({
      titulo: 'Excluir setor ' + fmt.id(s.id_setor), mensagem: `Tem certeza que deseja excluir o setor "${s.nome_setor}"?`,
      detalhe: n ? `${n === 1 ? 'A máquina vinculada' : `As ${n} máquinas vinculadas`} — com seus sensores, leituras e consumos — também serão excluídas.` : 'Esta ação não pode ser desfeita.'
    });
    if (!ok) return;
    try { await requisicao(`/setores/${s.id_setor}`, 'DELETE'); closeModal(); toast('Setor excluído.'); await carregar(); }
    catch (erro) { toast(erro.message, 'erro'); }
  }

  KV.pronto.then(carregar).catch(() => {});
})();
