-- ============================================================
-- Klyvolt - Sistema de Gestão de Consumo de Energia
-- Script de criação do banco de dados (MySQL)
-- Ordem de criação respeita as dependências de FK
-- ============================================================

CREATE DATABASE IF NOT EXISTS klyvolt;
USE klyvolt;

-- ------------------------------------------------------------
-- 1. EMPRESA (topo da hierarquia, sem FK)
-- ------------------------------------------------------------
CREATE TABLE empresa (
    IDempresa       INT AUTO_INCREMENT PRIMARY KEY,
    CNPJ            VARCHAR(18)  NOT NULL UNIQUE,
    nome_empresa    VARCHAR(100) NOT NULL,
    email_empresa   VARCHAR(100) NOT NULL UNIQUE,
    senha_empresa   VARCHAR(225) NOT NULL,
    telefone_empresa VARCHAR(20) NOT NULL
);

-- ------------------------------------------------------------
-- 2. USUARIO (N:1 empresa)
-- ------------------------------------------------------------
CREATE TABLE usuario (
    IDusuario       INT AUTO_INCREMENT PRIMARY KEY,
    nome_usuario    VARCHAR(100) NOT NULL,
    email_usuario   VARCHAR(100) NOT NULL UNIQUE,
    senha_usuario   VARCHAR(200) NOT NULL,
    tipo_usuario    ENUM('Administrador','Operador','Visualizador') NOT NULL,
    ID_empresa      INT NOT NULL,
    FOREIGN KEY (ID_empresa) REFERENCES empresa(IDempresa)
);

-- ------------------------------------------------------------
-- 3. SETOR (N:1 usuario)
-- ------------------------------------------------------------
CREATE TABLE setor (
    IDsetor         INT AUTO_INCREMENT PRIMARY KEY,
    nome_setor      VARCHAR(100) NOT NULL,
    divisao_setor   VARCHAR(100),
    ID_usuario      INT NOT NULL,
    FOREIGN KEY (ID_usuario) REFERENCES usuario(IDusuario)
);

-- ------------------------------------------------------------
-- 4. MAQUINA (N:1 setor)
-- ------------------------------------------------------------
CREATE TABLE maquina (
    IDmaquina           INT AUTO_INCREMENT PRIMARY KEY,
    nome_maquina        VARCHAR(100) NOT NULL,
    descricao_maquina   TEXT NOT NULL,
    potencia_nominal    DECIMAL(10,2),
    numero_serie        VARCHAR(50),
    ID_setor            INT NOT NULL,
    FOREIGN KEY (ID_setor) REFERENCES setor(IDsetor)
);

-- ------------------------------------------------------------
-- 5. SENSOR (N:1 maquina) - equipamento físico instalado
-- ------------------------------------------------------------
CREATE TABLE sensor (
    ID_sensor               INT AUTO_INCREMENT PRIMARY KEY,
    numero_serie            VARCHAR(50)  NOT NULL UNIQUE,
    fabricante              VARCHAR(100),
    modelo                  VARCHAR(100),
    tipo_sensor             VARCHAR(100) NOT NULL,
    unidade_medida          VARCHAR(10)  NOT NULL,
    protocolo_comunicacao   VARCHAR(50)  NOT NULL,
    mac_address             VARCHAR(17)  NOT NULL UNIQUE,
    endereco_ip             VARCHAR(45),
    token_autenticacao      VARCHAR(255),
    status_conexao          ENUM('online','offline') NOT NULL,
    data_instalacao         DATE,
    data_ultima_calibracao  DATE,
    status                  ENUM('ativo','inativo','manutencao') NOT NULL,
    ID_maquina              INT NOT NULL,
    FOREIGN KEY (ID_maquina) REFERENCES maquina(IDmaquina)
);

-- ------------------------------------------------------------
-- 6. CONSUMO (N:1 maquina) - agregação de leituras por período
-- ------------------------------------------------------------
CREATE TABLE consumo (
    IDconsumo       INT AUTO_INCREMENT PRIMARY KEY,
    data_inicio     DATETIME NOT NULL,
    data_fim        DATETIME NOT NULL,
    consumo_kwh     DECIMAL(12,2) NOT NULL,
    ID_maquina      INT NOT NULL,
    FOREIGN KEY (ID_maquina) REFERENCES maquina(IDmaquina)
);

-- ------------------------------------------------------------
-- 7. LEITURA (N:1 sensor, N:1 usuario, N:1 consumo)
--    Cada leitura pertence a um sensor; é agregada a um consumo
--    quando o período é fechado.
-- ------------------------------------------------------------
CREATE TABLE leitura (
    IDleitura           INT AUTO_INCREMENT PRIMARY KEY,
    data_leitura        DATETIME NOT NULL,
    valor_medido_kwh    DECIMAL(12,2) NOT NULL,
    observacao_leitura  TEXT,
    ID_sensor           INT NOT NULL,
    ID_usuario          INT,
    ID_consumo          INT,
    FOREIGN KEY (ID_sensor)  REFERENCES sensor(ID_sensor),
    FOREIGN KEY (ID_usuario) REFERENCES usuario(IDusuario),
    FOREIGN KEY (ID_consumo) REFERENCES consumo(IDconsumo),
    UNIQUE (ID_sensor, data_leitura)
);

-- ------------------------------------------------------------
-- 8. DECISAO (catálogo de tipos de decisão, sem FK)
-- ------------------------------------------------------------
CREATE TABLE decisao (
    ID_decisao          INT AUTO_INCREMENT PRIMARY KEY,
    nome_decisao        VARCHAR(100) NOT NULL,
    descricao_decisao   TEXT,
    criterio_acionado   VARCHAR(150) NOT NULL,
    limite_referencia   DECIMAL(12,2) NOT NULL
);

-- ------------------------------------------------------------
-- 9. TOMADA_DECISAO (N:1 decisao, N:1 leitura, N:1 consumo)
--    Evento real de decisão, acionado automaticamente pelo sistema
--    a partir de uma leitura ou de um consumo agregado.
-- ------------------------------------------------------------
CREATE TABLE tomada_decisao (
    ID_tomada_decisao   INT AUTO_INCREMENT PRIMARY KEY,
    data_tomada_decisao DATETIME NOT NULL,
    valor_referencia    DECIMAL(12,2) NOT NULL,
    status_execucao     ENUM('pendente','executada','cancelada') NOT NULL,
    observacao          TEXT,
    ID_decisao          INT NOT NULL,
    ID_leitura          INT,
    ID_consumo          INT,
    FOREIGN KEY (ID_decisao) REFERENCES decisao(ID_decisao),
    FOREIGN KEY (ID_leitura) REFERENCES leitura(IDleitura),
    FOREIGN KEY (ID_consumo) REFERENCES consumo(IDconsumo)
);
