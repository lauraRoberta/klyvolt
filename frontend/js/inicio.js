// js/inicio.js - resumo da empresa logada na tela Início.
// Carregar depois de api.js e nav.js. Sem login, não faz nada (a página é pública).
(function () {
    if (!obterToken()) return;
  
    const sessao = sessaoAtual();
    const idEmpresa = sessao && sessao.empresa ? sessao.empresa.id_empresa : null;
    if (idEmpresa === null || idEmpresa === undefined) return;
  
    const mensagem = document.querySelector('#mensagem');
    const conteudo = document.querySelector('#conteudo');
    const titulo = document.querySelector('#titulo-resumo');
    const kpis = document.querySelector('#kpis');
    const porMaquina = document.querySelector('#por-maquina');
    const porSetor = document.querySelector('#por-setor');
  
    const QUANTIDADE_NO_RANKING = 3;
  
    const decimal = valor => Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const inteiro = valor => Number(valor).toLocaleString('pt-BR');
  
    function criar(tag, classe, texto) {
      const elemento = document.createElement(tag);
      if (classe) elemento.className = classe;
      if (texto !== undefined) elemento.textContent = texto;
      return elemento;
    }
  
    const maiorPrimeiro = (a, b) => b.consumo_kwh - a.consumo_kwh;
  
    function desenharNumeros(totais, maquinas, setores) {
      const topoMaquina = maquinas[0];
      const topoSetor = setores[0];
      const itens = [
        ['Consumo total', `${decimal(totais.consumo_kwh)} kWh`, 'registrado'],
        ['Máquina que mais gasta', topoMaquina ? topoMaquina.nome : '—', topoMaquina ? `${decimal(topoMaquina.consumo_kwh)} kWh` : 'sem consumo'],
        ['Setor que mais pesa', topoSetor ? topoSetor.nome : '—', topoSetor ? `${decimal(topoSetor.consumo_kwh)} kWh` : 'sem consumo'],
        ['Sensores online', `${inteiro(totais.sensores_online)} de ${inteiro(totais.sensores)}`, 'conectados agora']
      ];
      kpis.replaceChildren();
      itens.forEach(([rotulo, valor, detalhe]) => {
        const cartao = criar('div', 'kpi');
        cartao.append(criar('span', 'kpi-rotulo', rotulo), criar('strong', 'kpi-valor', valor), criar('span', 'kpi-detalhe', detalhe));
        kpis.append(cartao);
      });
    }
  
    function desenharBarras(lista, itens, textoVazio) {
      lista.replaceChildren();
      if (itens.length === 0) {
        lista.append(criar('li', 'vazio', textoVazio));
        return;
      }
      const maior = Math.max(...itens.map(item => item.consumo_kwh), 0);
      itens.forEach((item, posicao) => {
        const linha = criar('li', posicao === 0 && item.consumo_kwh > 0 ? 'primeiro' : '');
        const nome = item.detalhe ? `${item.nome} · ${item.detalhe}` : item.nome;
        const barra = criar('span', 'barra');
        barra.setAttribute('aria-hidden', 'true');
        const preenchimento = document.createElement('i');
        preenchimento.style.setProperty('--p', maior > 0 ? `${(item.consumo_kwh / maior) * 100}%` : '0%');
        barra.append(preenchimento);
        linha.append(criar('span', null, nome), criar('strong', null, `${decimal(item.consumo_kwh)} kWh`), barra);
        lista.append(linha);
      });
    }
  
    async function carregar() {
      esconderMensagem(mensagem);
      try {
        const dados = await requisicao(`/painel/${idEmpresa}`);
        titulo.textContent = dados.empresa.nome_empresa;
  
        const maquinas = dados.consumo_por_maquina
          .map(m => ({ nome: m.nome, detalhe: m.setor, consumo_kwh: m.consumo_kwh }))
          .sort(maiorPrimeiro);
        const setores = dados.consumo_por_setor
          .map(s => ({ nome: s.nome, consumo_kwh: s.consumo_kwh }))
          .sort(maiorPrimeiro);
  
        desenharNumeros(dados.totais, maquinas, setores);
        desenharBarras(porMaquina, maquinas.slice(0, QUANTIDADE_NO_RANKING), 'Ainda não há máquinas cadastradas.');
        desenharBarras(porSetor, setores.slice(0, QUANTIDADE_NO_RANKING), 'Ainda não há setores cadastrados.');
        conteudo.hidden = false;
      } catch (erro) {
        conteudo.hidden = true;
        mostrarMensagem(mensagem, erro.message, true);
      }
    }
  
    carregar();
  })();