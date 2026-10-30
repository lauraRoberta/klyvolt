/* KLYVOLT · auth.js — página Entrar: cadastro da empresa, login, recuperação de senha
   e tratamento dos links enviados por e-mail (confirmação e nova senha). */
(function () {
  'use strict';
  const { requisicao, salvarSessao, lerSessao, toast, ocupado } = KV;
  const $ = id => document.getElementById(id);
  const FORMS = ['formCadastro', 'formLogin', 'formRecuperar', 'formNovaSenha'];
  const PAGINAS = new Set(['painel', 'consumos', 'sensores', 'leituras', 'setores', 'maquinas', 'decisoes', 'empresa', 'registrar-consumo']);
  const params = new URLSearchParams(location.search);
  const hash = new URLSearchParams(location.hash.replace(/^#/, ''));
  const voltar = PAGINAS.has(params.get('voltar')) ? params.get('voltar') : null;
  const destino = () => (voltar || 'painel') + '.html';
  let modoAtual = 'cadastro';
  let linkRecuperacao = null;

  /* ---------- validações (mesmas regras do backend) ---------- */
  const digitos = s => String(s || '').replace(/\D/g, '');
  function cnpjValido(v) {
    const d = digitos(v);
    if (d.length !== 14 || /^(\d)\1{13}$/.test(d)) return false;
    const calc = n => {
      const pesos = n === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
      const s = pesos.reduce((acc, p, i) => acc + Number(d[i]) * p, 0) % 11;
      return s < 2 ? 0 : 11 - s;
    };
    return calc(12) === Number(d[12]) && calc(13) === Number(d[13]);
  }
  function telefoneValido(v) {
    let d = digitos(v);
    if ((d.length === 12 || d.length === 13) && d.startsWith('55')) d = d.slice(2);
    return d.length === 10 || d.length === 11;
  }
  const emailValido = v => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(v || '').trim());
  const senhaValida = v => String(v || '').length >= 8 && /[A-Za-z]/.test(v) && /\d/.test(v);

  /* ---------- máscaras ---------- */
  $('cnpj').addEventListener('input', e => {
    const d = digitos(e.target.value).slice(0, 14);
    e.target.value = d.replace(/^(\d{2})(\d)/, '$1.$2').replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/\.(\d{3})(\d)/, '.$1/$2').replace(/(\d{4})(\d)/, '$1-$2');
  });
  $('telefone').addEventListener('input', e => {
    const d = digitos(e.target.value).slice(0, 11);
    e.target.value = d.length > 10 ? d.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, '($1) $2-$3')
      : d.replace(/^(\d{2})(\d{0,4})(\d{0,4}).*/, (m, a, b, c) => `(${a}) ${b}${c ? '-' + c : ''}`).replace(/^\(\) ?$/, '');
  });

  /* ---------- troca de telas ---------- */
  function mostrar(id) {
    for (const f of FORMS) $(f).hidden = f !== id;
    const primeiro = $(id).querySelector('input:not([readonly])');
    if (primeiro) primeiro.focus({ preventScroll: true });
  }
  function abas(rotuloA, rotuloB, ativa) {
    $('tabA').textContent = rotuloA; $('tabB').textContent = rotuloB;
    KV.marcarAba(ativa === 'A' ? $('tabA') : $('tabB'));
  }
  function modo(m) {
    modoAtual = m;
    const titulos = { cadastro: 'Cadastro da empresa', login: 'Acesse sua empresa', recuperar: 'Recuperar acesso', 'nova-senha': 'Criar nova senha' };
    $('empresaTitulo').textContent = titulos[m];
    if (m === 'nova-senha') abas('Nova Senha', 'Cancelar', 'A');
    else abas('Nova Empresa', 'Já sou cadastrado', m === 'cadastro' ? 'A' : 'B');
    mostrar({ cadastro: 'formCadastro', login: 'formLogin', recuperar: 'formRecuperar', 'nova-senha': 'formNovaSenha' }[m]);
  }
  $('tabA').addEventListener('click', () => { if (modoAtual !== 'nova-senha') modo('cadastro'); });
  $('tabB').addEventListener('click', () => { linkRecuperacao = null; modo('login'); });
  $('linkRecuperar').addEventListener('click', () => { $('recEmail').value = $('loginEmail').value; modo('recuperar'); });
  $('linkVoltarLogin').addEventListener('click', () => modo('login'));

  async function entrarComSessao(sessao, mensagem) {
    salvarSessao(sessao);
    try {
      const perfil = await requisicao('/auth/me');
      salvarSessao({ ...sessao, perfil });
      if (mensagem) sessionStorage.setItem('klyvolt.aviso', mensagem);
      location.href = destino();
      return true;
    } catch (erro) {
      salvarSessao(null);
      toast(erro.message, 'erro', 9000);
      return false;
    }
  }

  /* ---------- cadastro: POST /empresas ---------- */
  $('formCadastro').addEventListener('submit', async e => {
    e.preventDefault();
    const botao = $('formCadastro').querySelector('[type=submit]');
    const dados = {
      cnpj: $('cnpj').value, nome_empresa: $('nome').value.trim(), nome_usuario: $('responsavel').value.trim(),
      email: $('email').value.trim().toLowerCase(), telefone: $('telefone').value, senha: $('senha').value
    };
    if (Object.values(dados).some(v => !v)) return toast('Preencha todos os campos para cadastrar a empresa.', 'aviso');
    if (!cnpjValido(dados.cnpj)) return toast('CNPJ inválido. Confira os 14 dígitos.', 'aviso');
    if (!emailValido(dados.email)) return toast('E-mail inválido.', 'aviso');
    if (!telefoneValido(dados.telefone)) return toast('Telefone inválido. Informe DDD + número (10 ou 11 dígitos).', 'aviso');
    if (!senhaValida(dados.senha)) return toast('A senha deve ter ao menos 8 caracteres, com letras e números.', 'aviso');
    ocupado(botao, true, 'Cadastrando…');
    try {
      const r = await requisicao('/empresas', 'POST', dados, { autenticar: false });
      $('formCadastro').reset();
      if (r.sessao) {
        await entrarComSessao(r.sessao, 'Empresa cadastrada. Bem-vindo ao KLYVOLT!');
      } else {
        toast(r.mensagem + ' Confirme o e-mail para entrar.', 'sucesso', 12000);
        $('loginEmail').value = dados.email;
        modo('login');
      }
    } catch (erro) {
      toast(erro.message, 'erro');
    } finally { ocupado(botao, false); }
  });

  /* ---------- login: POST /auth/login ---------- */
  $('formLogin').addEventListener('submit', async e => {
    e.preventDefault();
    const botao = $('formLogin').querySelector('[type=submit]');
    const email = $('loginEmail').value.trim().toLowerCase(), senha = $('loginSenha').value;
    if (!email || !senha) return toast('Informe e-mail e senha.', 'aviso');
    ocupado(botao, true, 'Entrando…');
    try {
      const sessao = await requisicao('/auth/login', 'POST', { email, senha }, { autenticar: false });
      salvarSessao(sessao);
      location.href = destino();
    } catch (erro) {
      $('loginSenha').value = '';
      toast(erro.message, 'erro');
    } finally { ocupado(botao, false); }
  });

  /* ---------- recuperação: POST /auth/recuperar ---------- */
  $('formRecuperar').addEventListener('submit', async e => {
    e.preventDefault();
    const botao = $('formRecuperar').querySelector('[type=submit]');
    const email = $('recEmail').value.trim().toLowerCase();
    if (!emailValido(email)) return toast('Informe um e-mail válido.', 'aviso');
    ocupado(botao, true, 'Enviando…');
    try {
      const r = await requisicao('/auth/recuperar', 'POST', { email }, { autenticar: false });
      toast(r.mensagem, 'sucesso', 10000);
      $('loginEmail').value = email;
      modo('login');
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  });

  /* ---------- nova senha (link do e-mail): POST /auth/nova-senha ---------- */
  $('formNovaSenha').addEventListener('submit', async e => {
    e.preventDefault();
    const botao = $('formNovaSenha').querySelector('[type=submit]');
    const s1 = $('novaSenha').value, s2 = $('novaSenha2').value;
    if (!senhaValida(s1)) return toast('A senha deve ter ao menos 8 caracteres, com letras e números.', 'aviso');
    if (s1 !== s2) return toast('As senhas não coincidem.', 'aviso');
    if (!linkRecuperacao) return toast('Abra novamente o link recebido por e-mail.', 'erro');
    ocupado(botao, true, 'Salvando…');
    try {
      await requisicao('/auth/nova-senha', 'POST', { ...linkRecuperacao, senha: s1 }, { autenticar: false });
      $('formNovaSenha').reset();
      await entrarComSessao(linkRecuperacao, 'Senha alterada com sucesso.');
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  });

  /* ---------- início ---------- */
  async function iniciar() {
    // Links do Supabase chegam no #hash: #access_token=...&refresh_token=...&type=recovery|signup
    if (hash.get('error_code') || hash.get('error')) {
      history.replaceState(null, '', location.pathname + location.search);
      toast(/expired/i.test(hash.get('error_code') + hash.get('error_description')) ? 'O link expirou ou já foi usado. Solicite um novo.'
        : 'Não foi possível validar o link recebido por e-mail.', 'erro', 9000);
      return modo('login');
    }
    if (hash.get('access_token') && hash.get('refresh_token')) {
      const sessaoLink = { access_token: hash.get('access_token'), refresh_token: hash.get('refresh_token') };
      history.replaceState(null, '', location.pathname + location.search);
      if (hash.get('type') === 'recovery') { linkRecuperacao = sessaoLink; return modo('nova-senha'); }
      return entrarComSessao(sessaoLink, 'E-mail confirmado. Bem-vindo ao KLYVOLT!');
    }
    if (params.get('motivo') === 'sessao') toast('Sua sessão expirou. Entre novamente.', 'info');
    if (params.get('motivo') === 'sem-empresa') toast('Esta conta não está vinculada a uma empresa ativa.', 'erro', 9000);
    // Já autenticado: segue para a plataforma (a área Empresa não é uma etapa de cadastro repetida)
    if (lerSessao() && !params.get('motivo')) {
      try {
        const perfil = await requisicao('/auth/me');
        salvarSessao({ ...lerSessao(), perfil });
        location.replace(destino());
        return;
      } catch (e) { salvarSessao(null); }
    }
    if (params.get('cadastro')) modo('cadastro');
    else if (params.get('entrar') || voltar) {
      modo('login');
      if (voltar && !params.get('motivo')) toast('Entre com sua conta para acessar esta área.', 'info');
    } else modo('cadastro');
  }
  iniciar();
})();
