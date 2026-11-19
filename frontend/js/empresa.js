// js/empresa.js - dados da empresa de quem está logado.
// Nome, e-mail e telefone podem ser editados (só pelo administrador); o CNPJ não.
// Carregar depois de api.js e nav.js.
(function () {
    const sessao = sessaoAtual();
    const formulario = document.querySelector('#form-empresa');
    const mensagem = document.querySelector('#mensagem');
    const nomeEmpresa = document.querySelector('#nome-empresa');
    const botaoSalvar = document.querySelector('#botao-salvar');
    const botaoDesfazer = document.querySelector('#botao-desfazer');
    const avisoPermissao = document.querySelector('#aviso-permissao');
  
    const campo = nome => formulario.elements[nome];
    const ehAdministrador = Boolean(sessao && sessao.funcao === 'Administrador');
    let original = null;
  
    function avisar(texto, erro) {
      mostrarMensagem(mensagem, texto, erro);
      mensagem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  
    function preencher(empresa) {
      original = empresa;
      campo('nome').value = empresa.nome_empresa;
      campo('cnpj').value = empresa.cnpj;
      campo('email').value = empresa.email_empresa;
      campo('telefone').value = empresa.telefone_empresa;
      nomeEmpresa.textContent = empresa.nome_empresa;
    }
  
    // Quem não é administrador só consulta
    function ajustarPermissao() {
      if (ehAdministrador) return;
      for (const entrada of formulario.querySelectorAll('input[name]')) entrada.readOnly = true;
      document.querySelector('#acoes').hidden = true;
      avisoPermissao.textContent = 'Somente o administrador altera os dados';
    }
  
    function primeiroErro() {
      for (const entrada of formulario.querySelectorAll('input[name]')) {
        if (entrada.name === 'cnpj') continue;
        if (!entrada.checkValidity()) {
          const rotulo = formulario.querySelector(`label[for="${entrada.id}"]`).textContent;
          return `${rotulo}: ${entrada.validationMessage}`;
        }
      }
      const digitos = campo('telefone').value.replace(/\D/g, '').length;
      if (digitos < 10 || digitos > 13) return 'Telefone: informe o DDD e o número.';
      return null;
    }
  
    async function carregar() {
      try {
        preencher(await requisicao(`/empresas/${sessao.empresa.id_empresa}`));
      } catch (erro) {
        mostrarMensagem(mensagem, erro.message, true);
      }
    }
  
    // Ligado primeiro: o envio nativo é sempre bloqueado.
    formulario.addEventListener('submit', async evento => {
      evento.preventDefault();
      if (typeof requisicao !== 'function') {
        avisar('O arquivo js/api.js não foi carregado ou está desatualizado. Recarregue com Ctrl + Shift + R.', true);
        return;
      }
      if (!ehAdministrador || original === null) return;
  
      esconderMensagem(mensagem);
      const erro = primeiroErro();
      if (erro) { avisar(erro, true); return; }
  
      const corpo = {
        nome_empresa: campo('nome').value.trim(),
        cnpj: original.cnpj, // o CNPJ segue o mesmo; a API também ignora qualquer mudança
        email_empresa: campo('email').value.trim(),
        telefone_empresa: campo('telefone').value.trim()
      };
  
      botaoSalvar.disabled = true;
      try {
        const atualizada = await requisicao(`/empresas/${original.id_empresa}`, 'PUT', corpo);
        preencher(atualizada);
        // mantém o nome da empresa certo no cabeçalho e na sessão guardada
        salvarSessao(obterToken(), { ...sessao, empresa: atualizada });
        const subtitulo = document.querySelector('.subtitulo');
        if (subtitulo) subtitulo.textContent = `${atualizada.nome_empresa} · ${sessao.nome} (${sessao.funcao})`;
        avisar('Dados atualizados com sucesso.', false);
      } catch (erroApi) {
        avisar(erroApi.message, true);
      } finally {
        botaoSalvar.disabled = false;
      }
    });
  
    botaoDesfazer.addEventListener('click', () => {
      if (original !== null) preencher(original);
      esconderMensagem(mensagem);
    });
  
    ajustarPermissao();
    carregar();
  })();