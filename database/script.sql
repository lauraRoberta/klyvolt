-- ============================================================
-- SISTEMA DE GESTÃO ENERGÉTICA - SCRIPT POSTGRESQL
-- ============================================================

-- Criar banco de dados (se não existir)
-- CREATE DATABASE gestao_energetica;
-- \c gestao_energetica;

-- ============================================================
-- 1. TABELA EMPRESA
-- ============================================================
CREATE TABLE IF NOT EXISTS EMPRESA (
    Id_empresa SERIAL PRIMARY KEY,
    cnpj VARCHAR(18) UNIQUE NOT NULL,
    nome_empresa VARCHAR(100) NOT NULL,
    email_empresa VARCHAR(100) UNIQUE NOT NULL,
    senha_empresa VARCHAR(255) NOT NULL,
    telefone_empresa VARCHAR(20),
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. TABELA USUARIO
-- ============================================================
CREATE TABLE IF NOT EXISTS USUARIO (
    Id_usuario SERIAL PRIMARY KEY,
    nome_usuario VARCHAR(100) NOT NULL,
    email_usuario VARCHAR(100) NOT NULL,
    senha_usuario VARCHAR(255) NOT NULL,
    tipo_usuario VARCHAR(20) NOT NULL DEFAULT 'Operador',
    Id_empresa INT NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_empresa) REFERENCES EMPRESA(Id_empresa) ON DELETE CASCADE,
    CONSTRAINT chk_tipo_usuario CHECK (tipo_usuario IN ('Admin', 'Operador', 'Visualizador'))
);

-- ============================================================
-- 3. TABELA LOCALIZACAO
-- ============================================================
CREATE TABLE IF NOT EXISTS LOCALIZACAO (
    Id_localizacao SERIAL PRIMARY KEY,
    nome_localizacao VARCHAR(100) NOT NULL,
    endereco_localizacao TEXT,
    cep_localizacao VARCHAR(10),
    concessionaria VARCHAR(100),
    Id_empresa INT NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_empresa) REFERENCES EMPRESA(Id_empresa) ON DELETE CASCADE
);

-- ============================================================
-- 4. TABELA SETOR
-- ============================================================
CREATE TABLE IF NOT EXISTS SETOR (
    Id_setor SERIAL PRIMARY KEY,
    nome_setor VARCHAR(100) NOT NULL,
    divisao_setor VARCHAR(100),
    Id_localizacao INT NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_localizacao) REFERENCES LOCALIZACAO(Id_localizacao) ON DELETE CASCADE
);

-- ============================================================
-- 5. TABELA MAQUINA
-- ============================================================
CREATE TABLE IF NOT EXISTS MAQUINA (
    Id_maquina SERIAL PRIMARY KEY,
    nome_maquina VARCHAR(100) NOT NULL,
    descricao_maquina TEXT NOT NULL,
    potencia_nominal DECIMAL(10,2),
    numero_serie VARCHAR(50),
    Id_setor INT NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_setor) REFERENCES SETOR(Id_setor) ON DELETE CASCADE
);

-- ============================================================
-- 6. TABELA TARIFA
-- ============================================================
CREATE TABLE IF NOT EXISTS TARIFA (
    Id_tarifa SERIAL PRIMARY KEY,
    valor_tarifa DECIMAL(10,4) NOT NULL,
    data_inicio_vigencia DATE NOT NULL,
    data_fim_vigencia DATE NOT NULL,
    descricao_tarifa VARCHAR(100) NOT NULL,
    tipo_tarifa VARCHAR(20) NOT NULL DEFAULT 'Convencional',
    Id_localizacao INT NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_localizacao) REFERENCES LOCALIZACAO(Id_localizacao) ON DELETE CASCADE,
    CONSTRAINT chk_tipo_tarifa CHECK (tipo_tarifa IN ('Convencional', 'Horossazonal', 'Bandeira')),
    CONSTRAINT chk_datas_tarifa CHECK (data_fim_vigencia >= data_inicio_vigencia)
);

-- ============================================================
-- 7. TABELA LEITURA
-- ============================================================
CREATE TABLE IF NOT EXISTS LEITURA (
    Id_leitura SERIAL PRIMARY KEY,
    data_leitura TIMESTAMP NOT NULL,
    valor_medido_kwh DECIMAL(12,2) NOT NULL,
    observacao_leitura TEXT,
    Id_maquina INT NOT NULL,
    Id_usuario INT NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_maquina) REFERENCES MAQUINA(Id_maquina) ON DELETE CASCADE,
    FOREIGN KEY (Id_usuario) REFERENCES USUARIO(Id_usuario)
);

-- ============================================================
-- 8. TABELA CONSUMO
-- ============================================================
CREATE TABLE IF NOT EXISTS CONSUMO (
    Id_consumo SERIAL PRIMARY KEY,
    data_inicio TIMESTAMP NOT NULL,
    data_fim TIMESTAMP NOT NULL,
    consumo_kwh DECIMAL(12,2) NOT NULL,
    Id_maquina INT NOT NULL,
    Id_leitura_inicial INT NOT NULL,
    Id_leitura_final INT NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_maquina) REFERENCES MAQUINA(Id_maquina) ON DELETE CASCADE,
    FOREIGN KEY (Id_leitura_inicial) REFERENCES LEITURA(Id_leitura),
    FOREIGN KEY (Id_leitura_final) REFERENCES LEITURA(Id_leitura),
    CONSTRAINT chk_datas_consumo CHECK (data_fim >= data_inicio),
    CONSTRAINT chk_leituras_diferentes CHECK (Id_leitura_inicial != Id_leitura_final)
);

-- ============================================================
-- 9. TABELA CUSTO
-- ============================================================
CREATE TABLE IF NOT EXISTS CUSTO (
    Id_custo SERIAL PRIMARY KEY,
    data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valor_total DECIMAL(12,2) NOT NULL,
    Id_consumo INT NOT NULL,
    Id_tarifa INT NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_consumo) REFERENCES CONSUMO(Id_consumo) ON DELETE CASCADE,
    FOREIGN KEY (Id_tarifa) REFERENCES TARIFA(Id_tarifa)
);

-- ============================================================
-- ÍNDICES PARA OTIMIZAR CONSULTAS
-- ============================================================
CREATE INDEX idx_empresa_cnpj ON EMPRESA(cnpj);
CREATE INDEX idx_empresa_email ON EMPRESA(email_empresa);
CREATE INDEX idx_usuario_email ON USUARIO(email_usuario);
CREATE INDEX idx_usuario_empresa ON USUARIO(Id_empresa);
CREATE INDEX idx_localizacao_empresa ON LOCALIZACAO(Id_empresa);
CREATE INDEX idx_setor_localizacao ON SETOR(Id_localizacao);
CREATE INDEX idx_maquina_setor ON MAQUINA(Id_setor);
CREATE INDEX idx_tarifa_localizacao ON TARIFA(Id_localizacao);
CREATE INDEX idx_tarifa_vigencia ON TARIFA(data_inicio_vigencia, data_fim_vigencia);
CREATE INDEX idx_leitura_maquina ON LEITURA(Id_maquina);
CREATE INDEX idx_leitura_usuario ON LEITURA(Id_usuario);
CREATE INDEX idx_leitura_data ON LEITURA(data_leitura);
CREATE INDEX idx_consumo_maquina ON CONSUMO(Id_maquina);
CREATE INDEX idx_consumo_leituras ON CONSUMO(Id_leitura_inicial, Id_leitura_final);
CREATE INDEX idx_consumo_datas ON CONSUMO(data_inicio, data_fim);
CREATE INDEX idx_custo_consumo ON CUSTO(Id_consumo);
CREATE INDEX idx_custo_tarifa ON CUSTO(Id_tarifa);

-- ============================================================
-- TRIGGER: Calcular Consumo Automaticamente
-- ============================================================
CREATE OR REPLACE FUNCTION calcular_consumo()
RETURNS TRIGGER AS $$
DECLARE
    ultima_leitura RECORD;
    consumo_calculado DECIMAL(12,2);
BEGIN
    -- Buscar a última leitura da mesma máquina
    SELECT Id_leitura, valor_medido_kwh, data_leitura
    INTO ultima_leitura
    FROM LEITURA
    WHERE Id_maquina = NEW.Id_maquina
      AND Id_leitura < NEW.Id_leitura
    ORDER BY Id_leitura DESC
    LIMIT 1;
    
    -- Se existir leitura anterior, calcular consumo
    IF FOUND THEN
        consumo_calculado = NEW.valor_medido_kwh - ultima_leitura.valor_medido_kwh;
        
        -- Validar se o consumo é positivo
        IF consumo_calculado >= 0 THEN
            INSERT INTO CONSUMO (
                data_inicio,
                data_fim,
                consumo_kwh,
                Id_maquina,
                Id_leitura_inicial,
                Id_leitura_final
            ) VALUES (
                ultima_leitura.data_leitura,
                NEW.data_leitura,
                consumo_calculado,
                NEW.Id_maquina,
                ultima_leitura.Id_leitura,
                NEW.Id_leitura
            );
        ELSE
            RAISE EXCEPTION 'ERRO: A leitura não pode ser menor que a leitura anterior!';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_calcular_consumo
AFTER INSERT ON LEITURA
FOR EACH ROW
EXECUTE FUNCTION calcular_consumo();

-- ============================================================
-- TRIGGER: Calcular Custo Automaticamente
-- ============================================================
CREATE OR REPLACE FUNCTION calcular_custo()
RETURNS TRIGGER AS $$
DECLARE
    tarifa_record RECORD;
    local_maquina INT;
    custo_total DECIMAL(12,2);
BEGIN
    -- Buscar a localização da máquina
    SELECT s.Id_localizacao
    INTO local_maquina
    FROM MAQUINA m
    JOIN SETOR s ON m.Id_setor = s.Id_setor
    WHERE m.Id_maquina = NEW.Id_maquina;
    
    -- Buscar a tarifa vigente na data do consumo
    SELECT Id_tarifa, valor_tarifa
    INTO tarifa_record
    FROM TARIFA
    WHERE Id_localizacao = local_maquina
      AND data_inicio_vigencia <= NEW.data_inicio
      AND data_fim_vigencia >= NEW.data_fim
    ORDER BY data_inicio_vigencia DESC
    LIMIT 1;
    
    -- Calcular custo
    IF FOUND THEN
        custo_total = NEW.consumo_kwh * tarifa_record.valor_tarifa;
        
        INSERT INTO CUSTO (
            data_calculo,
            valor_total,
            Id_consumo,
            Id_tarifa
        ) VALUES (
            NOW(),
            custo_total,
            NEW.Id_consumo,
            tarifa_record.Id_tarifa
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_calcular_custo
AFTER INSERT ON CONSUMO
FOR EACH ROW
EXECUTE FUNCTION calcular_custo();

-- ============================================================
-- DADOS DE TESTE
-- ============================================================

-- Inserir uma empresa
INSERT INTO EMPRESA (cnpj, nome_empresa, email_empresa, senha_empresa, telefone_empresa)
VALUES ('12.345.678/0001-90', 'Indústria ABC', 'contato@abc.com.br', 'senha123', '(11) 99999-9999');

-- Inserir um usuário
INSERT INTO USUARIO (nome_usuario, email_usuario, senha_usuario, tipo_usuario, Id_empresa)
VALUES ('João Silva', 'joao@abc.com.br', 'senha123', 'Admin', 1);

-- Inserir uma localização
INSERT INTO LOCALIZACAO (nome_localizacao, endereco_localizacao, cep_localizacao, concessionaria, Id_empresa)
VALUES ('Filial SP', 'Av. Paulista, 1000', '01310-100', 'ENEL SP', 1);

-- Inserir um setor
INSERT INTO SETOR (nome_setor, divisao_setor, Id_localizacao)
VALUES ('Produção', 'Linha A', 1);

-- Inserir uma máquina
INSERT INTO MAQUINA (nome_maquina, descricao_maquina, potencia_nominal, numero_serie, Id_setor)
VALUES ('Prensa Hidráulica', 'Prensa de 50 toneladas', 45.5, 'SN-2026-001', 1);

-- Inserir uma tarifa
INSERT INTO TARIFA (valor_tarifa, data_inicio_vigencia, data_fim_vigencia, descricao_tarifa, tipo_tarifa, Id_localizacao)
VALUES (0.85, '2026-01-01', '2026-12-31', 'Bandeira Verde 2026', 'Convencional', 1);

-- Inserir primeira leitura
INSERT INTO LEITURA (data_leitura, valor_medido_kwh, observacao_leitura, Id_maquina, Id_usuario)
VALUES ('2026-08-01 08:00:00', 1000.00, 'Leitura inicial do mês', 1, 1);

-- Inserir segunda leitura (vai gerar consumo e custo automaticamente)
INSERT INTO LEITURA (data_leitura, valor_medido_kwh, observacao_leitura, Id_maquina, Id_usuario)
VALUES ('2026-08-15 08:00:00', 1250.00, 'Leitura quinzenal', 1, 1);

-- ============================================================
-- CONSULTAS PARA TESTAR
-- ============================================================

-- Ver todas as leituras
SELECT * FROM LEITURA;

-- Ver todos os consumos
SELECT * FROM CONSUMO;

-- Ver todos os custos
SELECT * FROM CUSTO;

-- Relatório: Consumo por máquina
SELECT 
    m.nome_maquina,
    COUNT(c.Id_consumo) AS total_consumos,
    SUM(c.consumo_kwh) AS consumo_total_kwh,
    AVG(c.consumo_kwh) AS consumo_medio_kwh
FROM MAQUINA m
LEFT JOIN CONSUMO c ON m.Id_maquina = c.Id_maquina
GROUP BY m.Id_maquina;

-- Relatório: Custo total por localização
SELECT 
    l.nome_localizacao,
    COUNT(cu.Id_custo) AS total_custos,
    SUM(cu.valor_total) AS custo_total_reais
FROM LOCALIZACAO l
LEFT JOIN SETOR s ON l.Id_localizacao = s.Id_localizacao
LEFT JOIN MAQUINA m ON s.Id_setor = m.Id_setor
LEFT JOIN CONSUMO c ON m.Id_maquina = c.Id_maquina
LEFT JOIN CUSTO cu ON c.Id_consumo = cu.Id_consumo
GROUP BY l.Id_localizacao;

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================