// js/cadastro.js - cadastro público: empresa + primeiro administrador (login-1).
// Depois de salvar, a pessoa já entra no sistema.
(function () {
  const formulario = document.querySelector('#form-cadastro');
  const mensagem = document.querySelector('#mensagem');
  const botao = document.querySelector('#botao-cadastrar');

  function avisar(texto, erro) {
    mensagem.textContent = texto;
    mensagem.classList.toggle('erro', Boolean(erro));
    mensagem.hidden = false;
    mensagem.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  const campo = nome => formulario.elements[nome];

  function primeiroErro() {
    for (const entrada of formulario.querySelectorAll('input[name]')) {
      if (entrada.type !== 'checkbox' && !entrada.checkValidity()) {
        const rotulo = formulario.querySelector(`label[for="${entrada.id}"]`).textContent;
        return `${rotulo}: ${entrada.validationMessage}`;
      }
    }
    if (campo('cnpj').value.replace(/\D/g, '').length !== 14) return 'CNPJ: informe 14 dígitos.';
    const telefone = campo('telefone').value.replace(/\D/g, '').length;
    if (telefone < 10 || telefone > 13) return 'Telefone: informe o DDD e o número.';
    const senha = campo('senha').value;
    if (!/[A-Za-z]/.test(senha) || !/\d/.test(senha)) return 'Senha: use letras e números.';
    return null;
  }

  // Ligado primeiro: o envio nativo (que põe a senha na URL) é sempre bloqueado.
  formulario.addEventListener('submit', async evento => {
    evento.preventDefault();

    if (typeof requisicao !== 'function') {
      avisar('O arquivo js/api.js não foi carregado ou está desatualizado. Recarregue com Ctrl + Shift + R.', true);
      return;
    }

    mensagem.hidden = true;
    const erro = primeiroErro();
    if (erro) { avisar(erro, true); return; }

    botao.disabled = true;
    try {
      const resposta = await requisicao('/auth/registrar', 'POST', {
        nome_empresa: campo('empresa_nome').value.trim(),
        cnpj: campo('cnpj').value.trim(),
        email_empresa: campo('empresa_email').value.trim(),
        telefone_empresa: campo('telefone').value.trim(),
        nome_admin: campo('admin_nome').value.trim(),
        email_admin: campo('admin_email').value.trim(),
        senha_admin: campo('senha').value
      });
      salvarSessao(resposta.access_token, resposta.sessao);
      window.location.replace('painel.html');
    } catch (erroApi) {
      avisar(erroApi.message, true);
      botao.disabled = false;
    }
  });

  // Mostrar / ocultar a senha
  const mostrar = document.querySelector('#f-mostrar');
  if (mostrar) {
    mostrar.addEventListener('change', () => {
      campo('senha').type = mostrar.checked ? 'text' : 'password';
    });
  }

  if (typeof obterToken === 'function' && obterToken()) {
    window.location.replace('painel.html');
  }
})();