/* KLYVOLT · empresa.js — dados da empresa, tarifa, equipe (usuários) e encerramento de sessão
   API: GET/PUT/DELETE /empresas/{id} · GET/POST/PUT/DELETE /usuarios */
(function () {
  'use strict';
  const { requisicao, toast, confirmar, ocupado, fmt } = KV;
  const $ = id => document.getElementById(id);
  const PERFIS = { Administrador: 'status-executada', Operador: 'status-executada', Visualizador: 'status-pendente' };
  let empresa = null, usuarios = [], perfil = null;
  const lista = KV.lista($('userList'), { vazio: 'Nenhum usuário encontrado.' });

  /* ---------- abas ---------- */
  function mostrarAba(aba) {
    KV.marcarAba($(aba === 'dados' ? 'tabDados' : 'tabEquipe'));
    $('formPerfil').hidden = aba !== 'dados';
    $('secaoEquipe').hidden = aba !== 'equipe';
    if (aba === 'equipe') carregarEquipe();
  }
  $('tabDados').addEventListener('click', () => mostrarAba('dados'));
  $('tabEquipe').addEventListener('click', () => mostrarAba('equipe'));
  $('tabSair').addEventListener('click', async () => {
    if (await confirmar({ titulo: 'Encerrar sessão', mensagem: 'Deseja sair da sua conta KLYVOLT neste navegador?', confirmar: 'Sair', perigo: false })) KV.sair();
  });

  /* ---------- máscara de telefone ---------- */
  $('perfilTelefone').addEventListener('input', e => {
    const d = e.target.value.replace(/\D/g, '').slice(0, 11);
    e.target.value = d.length > 10 ? d.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, '($1) $2-$3')
      : d.replace(/^(\d{2})(\d{0,4})(\d{0,4}).*/, (m, a, b, c) => `(${a}) ${b}${c ? '-' + c : ''}`).replace(/^\(\) ?$/, '');
  });

  /* ---------- dados da empresa ---------- */
  function preencher() {
    $('perfilCnpj').value = empresa.cnpj;
    $('perfilNome').value = empresa.nome_empresa;
    $('perfilEmail').value = empresa.email_empresa;
    $('perfilTelefone').value = empresa.telefone_empresa;
    $('perfilTarifa').value = empresa.tarifa_kwh == null ? ''
      : new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4, useGrouping: false }).format(empresa.tarifa_kwh);
    const nota = $('perfilNota'); nota.replaceChildren();
    nota.append('Conectado como ', KV.el('strong', null, perfil.nome_usuario), ` (${perfil.email_usuario}) · Perfil: `, KV.el('strong', null, perfil.tipo_usuario));
    const admin = perfil.tipo_usuario === 'Administrador';
    ['perfilNome', 'perfilTelefone', 'perfilTarifa'].forEach(id => $(id).disabled = !admin);
    $('botaoSalvarEmpresa').hidden = !admin;
    $('botaoExcluirEmpresa').hidden = !admin;
    $('botaoNovoUsuario').hidden = !admin;
    if (!admin) nota.append('. Somente administradores alteram os dados da empresa e a equipe.');
  }

  async function carregar() {
    try {
      const empresas = await requisicao('/empresas');
      empresa = empresas[0];
      preencher();
    } catch (erro) { toast(erro.message, 'erro'); }
  }

  $('formPerfil').addEventListener('submit', async e => {
    e.preventDefault();
    const botao = $('botaoSalvarEmpresa');
    const tarifaTxt = $('perfilTarifa').value.trim();
    const tarifa = tarifaTxt === '' ? null : KV.numero(tarifaTxt);
    const dados = { nome_empresa: $('perfilNome').value.trim(), telefone_empresa: $('perfilTelefone').value, tarifa_kwh: tarifa };
    if (!dados.nome_empresa) return toast('Informe o nome da empresa.', 'aviso');
    if (tarifa !== null && (!Number.isFinite(tarifa) || tarifa < 0 || tarifa > 100)) return toast('Tarifa inválida. Ex: 0,8925 (R$ por kWh).', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      empresa = await requisicao(`/empresas/${empresa.id_empresa}`, 'PUT', dados);
      preencher();
      toast('Dados da empresa atualizados.');
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  });

  $('botaoExcluirEmpresa').addEventListener('click', async () => {
    const ok = await confirmar({
      titulo: 'Excluir empresa', confirmar: 'Excluir tudo',
      mensagem: `Excluir "${empresa.nome_empresa}" e TODOS os dados dela?`,
      detalhe: 'Setores, máquinas, sensores, leituras, consumos, regras, acionamentos e usuários serão apagados definitivamente. Esta ação não pode ser desfeita.'
    });
    if (!ok) return;
    try {
      await requisicao(`/empresas/${empresa.id_empresa}`, 'DELETE');
      KV.salvarSessao(null);
      location.href = 'entrar.html?cadastro=1';
    } catch (erro) { toast(erro.message, 'erro'); }
  });

  /* ---------- equipe ---------- */
  window.searchUser = function () { lista.busca = $('searchInput').value; lista.aplicar(); };

  async function carregarEquipe() {
    lista.carregando();
    try {
      usuarios = await requisicao('/usuarios');
      lista.render(usuarios, u => {
        const c = KV.card({ id: u.id_usuario, badge: u.ativo === false ? 'Bloqueado' : u.tipo_usuario,
          badgeClasse: u.ativo === false ? 'status-falha' : PERFIS[u.tipo_usuario] });
        c.linha(u.nome_usuario + (u.id_usuario === perfil.id_usuario ? ' (você)' : ''), 'fa-user', 'rule-name');
        c.linha(u.email_usuario, 'fa-envelope');
        c.linha('Perfil: ' + u.tipo_usuario, 'fa-shield-halved');
        c.ver.addEventListener('click', () => openModal('view', u));
        return c.card;
      });
    } catch (erro) { lista.erro(erro.message); toast(erro.message, 'erro'); }
  }

  function openModal(mode, u = null) {
    const campos = ['nomeUsuario', 'emailUsuario', 'tipoUsuario', 'ativoUsuario', 'senhaUsuario'];
    const admin = perfil.tipo_usuario === 'Administrador';
    $('senhaGroup').style.display = mode === 'create' ? '' : 'none';
    $('ativoGroup').style.display = mode === 'create' ? 'none' : '';
    if (mode === 'create') {
      $('modalTitle').innerText = 'Novo Usuário';
      campos.forEach(id => { $(id).disabled = false; });
      $('nomeUsuario').value = ''; $('emailUsuario').value = ''; $('senhaUsuario').value = '';
      $('tipoUsuario').value = 'Operador';
      KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Cadastrar Usuário', 'btn-confirm', b => salvar(null, b)]]);
    } else {
      $('nomeUsuario').value = u.nome_usuario; $('emailUsuario').value = u.email_usuario;
      $('tipoUsuario').value = u.tipo_usuario; $('ativoUsuario').value = String(u.ativo !== false);
      $('emailUsuario').disabled = true;
      if (mode === 'view') {
        $('modalTitle').innerText = 'Usuário ' + fmt.id(u.id_usuario);
        campos.forEach(id => { $(id).disabled = true; });
        const acoes = [['Fechar', 'btn-cancel', closeModal]];
        if (admin && u.id_usuario !== perfil.id_usuario) acoes.splice(0, 1, ['Remover', 'btn-cancel', () => remover(u)], ['Editar', 'btn-confirm', () => openModal('edit', u)]);
        else if (admin) acoes.push(['Editar', 'btn-confirm', () => openModal('edit', u)]);
        KV.botoesModal($('modalActions'), acoes);
      } else {
        $('modalTitle').innerText = 'Editando Usuário ' + fmt.id(u.id_usuario);
        ['nomeUsuario', 'tipoUsuario', 'ativoUsuario'].forEach(id => { $(id).disabled = false; });
        if (u.id_usuario === perfil.id_usuario) { $('tipoUsuario').disabled = true; $('ativoUsuario').disabled = true; }
        KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Atualizar', 'btn-confirm', b => salvar(u.id_usuario, b)]]);
      }
    }
    $('modalOverlay').style.display = 'flex';
  }
  function closeModal() { $('modalOverlay').style.display = 'none'; }
  window.openModal = openModal; window.closeModal = closeModal;
  KV.prepararModal($('modalOverlay'), closeModal);

  async function salvar(id, botao) {
    const nome = $('nomeUsuario').value.trim(), email = $('emailUsuario').value.trim().toLowerCase();
    if (!nome) return toast('Informe o nome.', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      if (id) {
        await requisicao(`/usuarios/${id}`, 'PUT', { nome_usuario: nome, tipo_usuario: $('tipoUsuario').value, ativo: $('ativoUsuario').value === 'true' });
        toast('Usuário atualizado.');
      } else {
        const senha = $('senhaUsuario').value;
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { ocupado(botao, false); return toast('E-mail inválido.', 'aviso'); }
        if (senha.length < 8 || !/[A-Za-z]/.test(senha) || !/\d/.test(senha)) { ocupado(botao, false); return toast('A senha inicial deve ter 8+ caracteres, com letras e números.', 'aviso'); }
        const novo = await requisicao('/usuarios', 'POST', { nome_usuario: nome, email_usuario: email, tipo_usuario: $('tipoUsuario').value, senha });
        toast(novo.confirmacao_pendente ? `Usuário cadastrado. ${email} precisa confirmar o e-mail antes de entrar.` : 'Usuário cadastrado. Ele já pode entrar com o e-mail e a senha inicial.', 'sucesso', 8000);
      }
      closeModal();
      await carregarEquipe();
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  }

  async function remover(u) {
    const ok = await confirmar({ titulo: 'Remover usuário', mensagem: `Remover ${u.nome_usuario} da empresa?`,
      detalhe: 'A pessoa perde o acesso ao KLYVOLT. Leituras registradas por ela são mantidas, sem o vínculo com o usuário.' });
    if (!ok) return;
    try { await requisicao(`/usuarios/${u.id_usuario}`, 'DELETE'); closeModal(); toast('Usuário removido.'); await carregarEquipe(); }
    catch (erro) { toast(erro.message, 'erro'); }
  }

  KV.pronto.then(s => { perfil = s.perfil; return carregar(); }).catch(() => {});
})();
