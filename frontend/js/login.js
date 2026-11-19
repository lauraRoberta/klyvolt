// js/login.js - tela de login (login-1).
(function () {
  const formulario = document.querySelector('#form-login');
  const mensagem = document.querySelector('#mensagem');
  const botao = document.querySelector('#botao-entrar');

  function avisar(texto, erro) {
    mensagem.textContent = texto;
    mensagem.classList.toggle('erro', Boolean(erro));
    mensagem.hidden = false;
  }

  // Ligado primeiro: o envio nativo (que põe a senha na URL) é sempre bloqueado.
  formulario.addEventListener('submit', async evento => {
    evento.preventDefault();

    if (typeof requisicao !== 'function') {
      avisar('O arquivo js/api.js não foi carregado ou está desatualizado. Recarregue com Ctrl + Shift + R.', true);
      return;
    }

    mensagem.hidden = true;
    if (!formulario.checkValidity()) {
      avisar('Informe o e-mail e a senha.', true);
      return;
    }

    botao.disabled = true;
    try {
      const resposta = await requisicao('/auth/login', 'POST', {
        email: formulario.email.value.trim(),
        senha: formulario.senha.value
      });
      salvarSessao(resposta.access_token, resposta.sessao);
      window.location.replace('painel.html');
    } catch (erro) {
      avisar(erro.message, true);
      botao.disabled = false;
    }
  });

  // Mostrar / ocultar a senha
  const mostrar = document.querySelector('#f-mostrar');
  if (mostrar) {
    mostrar.addEventListener('change', () => {
      formulario.senha.type = mostrar.checked ? 'text' : 'password';
    });
  }

  // Quem já está logado vai direto para o painel
  if (typeof obterToken === 'function' && obterToken()) {
    window.location.replace('painel.html');
  }
})();
