-- ============================================================
-- Klyvolt - Sistema de Gestão de Consumo de Energia
-- Script de criação do banco de dados (PostgreSQL)
-- Versão revisada: inconsistências corrigidas
-- Ordem de criação respeita as dependências de FK
-- ============================================================

-- ------------------------------------------------------------
-- Limpeza (opcional, útil em ambiente de dev)
-- ------------------------------------------------------------
DROP TABLE IF EXISTS tomada_decisao CASCADE;
DROP TABLE IF EXISTS decisao         CASCADE;
DROP TABLE IF EXISTS leitura         CASCADE;
DROP TABLE IF EXISTS consumo         CASCADE;
DROP TABLE IF EXISTS sensor          CASCADE;
DROP TABLE IF EXISTS maquina         CASCADE;
DROP TABLE IF EXISTS setor           CASCADE;
DROP TABLE IF EXISTS usuario         CASCADE;
DROP TABLE IF EXISTS empresa         CASCADE;

-- ------------------------------------------------------------
-- 1. EMPRESA (topo da hierarquia, sem FK)
-- ------------------------------------------------------------
CREATE TABLE empresa (
    id_empresa        SERIAL PRIMARY KEY,
    cnpj              VARCHAR(18)  NOT NULL UNIQUE,
    nome_empresa      VARCHAR(100) NOT NULL,
    email_empresa     VARCHAR(100) NOT NULL UNIQUE,
    senha_empresa     VARCHAR(255) NOT NULL,
    telefone_empresa  VARCHAR(20)  NOT NULL,
    CONSTRAINT chk_cnpj_formato CHECK (cnpj ~ '^[0-9]{2}\.?[0-9]{3}\.?[0-9]{3}\/?[0-9]{4}-?[0-9]{2}$')
);

COMMENT ON TABLE  empresa IS 'Empresa cliente do sistema Klyvolt';
COMMENT ON COLUMN empresa.senha_empresa IS 'Hash da senha (bcrypt/argon2). Nunca armazenar em texto puro.';

-- ------------------------------------------------------------
-- 2. USUARIO (N:1 empresa)
-- ------------------------------------------------------------
CREATE TABLE usuario (
    id_usuario      SERIAL PRIMARY KEY,
    nome_usuario    VARCHAR(100) NOT NULL,
    email_usuario   VARCHAR(100) NOT NULL UNIQUE,
    senha_usuario   VARCHAR(255) NOT NULL,
    tipo_usuario    VARCHAR(20)  NOT NULL,
    id_empresa      INT NOT NULL REFERENCES empresa(id_empresa) ON DELETE CASCADE,
    CONSTRAINT chk_tipo_usuario CHECK (tipo_usuario IN ('Administrador','Operador','Visualizador'))
);

CREATE INDEX idx_usuario_empresa ON usuario(id_empresa);

-- ------------------------------------------------------------
-- 3. SETOR (N:1 usuario responsável)
--    Renomeado campo para deixar explícito que é o responsável
-- ------------------------------------------------------------
CREATE TABLE setor (
    id_setor              SERIAL PRIMARY KEY,
    nome_setor            VARCHAR(100) NOT NULL,
    divisao_setor         VARCHAR(100),
    id_usuario_responsavel INT NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    CONSTRAINT uq_setor_nome UNIQUE (nome_setor)
);

CREATE INDEX idx_setor_responsavel ON setor(id_usuario_responsavel);

-- ------------------------------------------------------------
-- 4. MAQUINA (N:1 setor)
-- ------------------------------------------------------------
CREATE TABLE maquina (
    id_maquina           SERIAL PRIMARY KEY,
    nome_maquina         VARCHAR(100) NOT NULL,
    descricao_maquina    TEXT NOT NULL,
    potencia_nominal     DECIMAL(10,2),
    numero_serie         VARCHAR(50) UNIQUE,
    id_setor             INT NOT NULL REFERENCES setor(id_setor) ON DELETE CASCADE,
    CONSTRAINT chk_potencia_positiva CHECK (potencia_nominal IS NULL OR potencia_nominal > 0)
);

CREATE INDEX idx_maquina_setor ON maquina(id_setor);

-- ------------------------------------------------------------
-- 5. SENSOR (N:1 maquina) - equipamento físico instalado
-- ------------------------------------------------------------
CREATE TABLE sensor (
    id_sensor              SERIAL PRIMARY KEY,
    numero_serie           VARCHAR(50)  NOT NULL UNIQUE,
    fabricante             VARCHAR(100),
    modelo                 VARCHAR(100),
    tipo_sensor            VARCHAR(100) NOT NULL,
    unidade_medida         VARCHAR(10)  NOT NULL,
    protocolo_comunicacao  VARCHAR(50)  NOT NULL,
    mac_address            VARCHAR(17)  NOT NULL UNIQUE,
    endereco_ip            VARCHAR(45),
    token_autenticacao     VARCHAR(255) UNIQUE,
    status_conexao         VARCHAR(10)  NOT NULL,
    data_instalacao        DATE,
    data_ultima_calibracao DATE,
    status                 VARCHAR(15)  NOT NULL,
    id_maquina             INT NOT NULL REFERENCES maquina(id_maquina) ON DELETE CASCADE,
    CONSTRAINT chk_status_conexao CHECK (status_conexao IN ('online','offline','unknown','erro')),
    CONSTRAINT chk_status_sensor  CHECK (status IN ('ativo','inativo','manutencao')),
    CONSTRAINT chk_mac_formato    CHECK (mac_address ~ '^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'),
    CONSTRAINT chk_ip_formato     CHECK (
        endereco_ip IS NULL
        OR endereco_ip ~ '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        OR endereco_ip ~ '^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
    ),
    CONSTRAINT chk_datas_sensor   CHECK (
        data_instalacao IS NULL
        OR data_ultima_calibracao IS NULL
        OR data_ultima_calibracao >= data_instalacao
    )
);

CREATE INDEX idx_sensor_maquina ON sensor(id_maquina);

-- ------------------------------------------------------------
-- 6. CONSUMO (N:1 maquina) - agregação de leituras por período
-- ------------------------------------------------------------
CREATE TABLE consumo (
    id_consumo   SERIAL PRIMARY KEY,
    data_inicio  TIMESTAMP NOT NULL,
    data_fim     TIMESTAMP NOT NULL,
    consumo_kwh  DECIMAL(12,2) NOT NULL,
    id_maquina   INT NOT NULL REFERENCES maquina(id_maquina) ON DELETE CASCADE,
    CONSTRAINT chk_periodo_consumo  CHECK (data_fim > data_inicio),
    CONSTRAINT chk_consumo_positivo CHECK (consumo_kwh >= 0),
    CONSTRAINT uq_consumo_periodo   UNIQUE (id_maquina, data_inicio, data_fim)
);

CREATE INDEX idx_consumo_maquina_periodo ON consumo(id_maquina, data_inicio, data_fim);

-- ------------------------------------------------------------
-- 7. LEITURA (N:1 sensor, N:1 usuario, N:1 consumo)
--    Cada leitura pertence a um sensor; é agregada a um consumo
--    quando o período é fechado.
-- ------------------------------------------------------------
CREATE TABLE leitura (
    id_leitura          SERIAL PRIMARY KEY,
    data_leitura        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valor_medido_kwh    DECIMAL(12,2) NOT NULL,
    observacao_leitura  TEXT,
    id_sensor           INT NOT NULL REFERENCES sensor(id_sensor)  ON DELETE CASCADE,
    id_usuario          INT          REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    id_consumo          INT          REFERENCES consumo(id_consumo) ON DELETE SET NULL,
    CONSTRAINT uq_leitura_sensor_data CHECK (TRUE), -- placeholder p/ clareza
    CONSTRAINT chk_valor_leitura_positivo CHECK (valor_medido_kwh >= 0),
    UNIQUE (id_sensor, data_leitura)
);

CREATE INDEX idx_leitura_data    ON leitura(data_leitura);
CREATE INDEX idx_leitura_sensor  ON leitura(id_sensor);
CREATE INDEX idx_leitura_consumo ON leitura(id_consumo);

-- ------------------------------------------------------------
-- 8. DECISAO (catálogo de tipos de decisão, sem FK)
-- ------------------------------------------------------------
CREATE TABLE decisao (
    id_decisao          SERIAL PRIMARY KEY,
    nome_decisao        VARCHAR(100) NOT NULL UNIQUE,
    descricao_decisao   TEXT,
    criterio_acionado   VARCHAR(150) NOT NULL,
    operador            VARCHAR(2)   NOT NULL,
    limite_referencia   DECIMAL(12,2) NOT NULL,
    unidade_limite      VARCHAR(10)  NOT NULL,
    CONSTRAINT chk_operador CHECK (operador IN ('>','<','>=','<=','='))
);

-- ------------------------------------------------------------
-- 9. TOMADA_DECISAO (N:1 decisao, N:1 leitura, N:1 consumo)
--    Evento real de decisão, acionado automaticamente pelo sistema
--    a partir de uma leitura ou de um consumo agregado.
-- ------------------------------------------------------------
CREATE TABLE tomada_decisao (
    id_tomada_decisao    SERIAL PRIMARY KEY,
    data_tomada_decisao  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valor_referencia     DECIMAL(12,2) NOT NULL,
    status_execucao      VARCHAR(15) NOT NULL,
    observacao           TEXT,
    id_decisao           INT NOT NULL REFERENCES decisao(id_decisao) ON DELETE RESTRICT,
    id_leitura           INT          REFERENCES leitura(id_leitura) ON DELETE SET NULL,
    id_consumo           INT          REFERENCES consumo(id_consumo) ON DELETE SET NULL,
    CONSTRAINT chk_status_execucao CHECK (status_execucao IN ('pendente','executada','cancelada','falha')),
    CONSTRAINT chk_origem_decisao  CHECK (id_leitura IS NOT NULL OR id_consumo IS NOT NULL)
);

CREATE INDEX idx_tomada_decisao_data    ON tomada_decisao(data_tomada_decisao);
CREATE INDEX idx_tomada_decisao_decisao ON tomada_decisao(id_decisao);

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================