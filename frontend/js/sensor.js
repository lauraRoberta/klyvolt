// js/sensor.js - regra específica da tela de sensor (carregar antes de crud.js).
window.crudHooks = {
  // Espelha o validar_datas do schema SensorCreate.
  validar(corpo) {
    if (corpo.data_instalacao && corpo.data_ultima_calibracao
        && corpo.data_ultima_calibracao < corpo.data_instalacao) {
      return 'A data da última calibração não pode ser anterior à data de instalação.';
    }
    return null;
  }
};
