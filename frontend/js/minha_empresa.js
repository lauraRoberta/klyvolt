// js/minha-empresa.js - dados e estrutura (setores, máquinas, sensores) da empresa escolhida.
// Carregar depois de api.js, nav.js e empresa-ativa.js.
(function () {
  const mensagem = document.querySelector('#mensagem');
  const conteudo = document.querySelector('#conteudo');
  const nomeEmpresa = document.querySelector('#nome-empresa');
  const kpis = document.querySelector('#kpis');
  const dadosEmpresa = document.querySelector('#dados-empresa');
  const estrutura = document.querySelector('#estrutura');

  const decimal = valor => Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const inteiro = valor => Number(valor).toLocaleString('pt-BR');

  function criar(tag, classe, texto) {
    const elemento = document.createElement(tag);
    if (classe) elemento.className = classe;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function desenharNumeros(totais) {
    const itens = [
      ['Setores', inteiro(totais.setores), 'da empresa'],
      ['Máquinas', inteiro(totais.maquinas), 'em todos os setores'],
      ['Sensores', inteiro(totais.sensores), 'instalados nas máquinas']
    ];
    kpis.replaceChildren();
    itens.forEach(([rotulo, valor, detalhe], posicao) => {
      const cartao = criar('div', 'kpi');
      cartao.style.animationDelay = `${posicao * 0.05}s`;
      cartao.append(criar('span', 'kpi-rotulo', rotulo), criar('strong', 'kpi-valor', valor), criar('span', 'kpi-detalhe', detalhe));
      kpis.append(cartao);
    });
  }

  function desenharDados(empresa) {
    const itens = [
      ['Nome', empresa.nome_empresa],
      ['CNPJ', empresa.cnpj],
      ['E-mail', empresa.email_empresa],
      ['Telefone', empresa.telefone_empresa]
    ];
    dadosEmpresa.replaceChildren();
    for (const [rotulo, valor] of itens) {
      const bloco = document.createElement('div');
      bloco.append(criar('dt', null, rotulo), criar('dd', null, valor || '—'));
      dadosEmpresa.append(bloco);
    }
  }

  function desenharEstrutura(setores) {
    estrutura.replaceChildren();
    if (setores.length === 0) {
      estrutura.append(criar('p', 'vazio', 'Ainda não há setores nesta empresa. Cadastre o primeiro no botão acima.'));
      return;
    }
    setores.forEach((setor, posicao) => {
      const cartao = criar('article', 'setor-cartao');
      cartao.style.animationDelay = `${Math.min(posicao, 8) * 0.05}s`;

      const topo = criar('div', 'setor-topo');
      const titulos = document.createElement('div');
      const partes = [];
      if (setor.divisao) partes.push(setor.divisao);
      partes.push(setor.responsavel ? `Responsável: ${setor.responsavel}` : 'Sem responsável');
      titulos.append(criar('h3', null, setor.nome), criar('p', 'setor-meta', partes.join(' · ')));
      const total = criar('div', 'setor-total', 'consumo');
      total.prepend(criar('strong', null, `${decimal(setor.consumo_kwh)} kWh`));
      topo.append(titulos, total);

      const lista = criar('ul', 'maquinas');
      if (setor.maquinas.length === 0) {
        lista.append(criar('li', 'vazio', 'Nenhuma máquina neste setor.'));
      }
      for (const maquina of setor.maquinas) {
        const linha = document.createElement('li');
        const detalhes = [];
        if (maquina.numero_serie) detalhes.push(`Série ${maquina.numero_serie}`);
        if (maquina.potencia_nominal !== null) detalhes.push(`Potência ${decimal(maquina.potencia_nominal)}`);
        detalhes.push(maquina.sensores === 1 ? '1 sensor' : `${inteiro(maquina.sensores)} sensores`);
        linha.append(
          criar('span', 'maquina-nome', maquina.nome),
          criar('span', 'maquina-meta', detalhes.join(' · ')),
          criar('span', 'maquina-kwh', `${decimal(maquina.consumo_kwh)} kWh`)
        );
        lista.append(linha);
      }

      cartao.append(topo, lista);
      estrutura.append(cartao);
    });
  }

  async function carregar(id) {
    esconderMensagem(mensagem);
    if (id === null) {
      conteudo.hidden = true;
      nomeEmpresa.textContent = '—';
      const erro = window.empresaAtiva.erro;
      mostrarMensagem(
        mensagem,
        erro || 'Nenhuma empresa cadastrada ainda. Cadastre uma na tela Empresa para ver os dados.',
        Boolean(erro)
      );
      return;
    }
    try {
      const dados = await requisicao(`/painel/${id}`);
      nomeEmpresa.textContent = dados.empresa.nome_empresa;
      desenharNumeros(dados.totais);
      desenharDados(dados.empresa);
      desenharEstrutura(dados.estrutura);
      conteudo.hidden = false;
    } catch (erro) {
      conteudo.hidden = true;
      mostrarMensagem(mensagem, erro.message, true);
    }
  }

  window.empresaAtiva.aoMudar(carregar);
})();