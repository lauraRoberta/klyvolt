// js/leitura.js - regra específica da tela de leitura (carregar antes de crud.js).
// A leitura manual só registra kWh; vibração, temperatura e umidade vêm do sensor.
window.crudHooks = {
  validar(corpo) {
    const valor = Number(corpo.valor_medido_kwh);
    if (corpo.valor_medido_kwh === '' || corpo.valor_medido_kwh == null || Number.isNaN(valor)) {
      return 'Informe o valor medido em kWh.';
    }
    if (valor < 0) {
      return 'O valor medido não pode ser negativo.';
    }
    return null;
  }
};