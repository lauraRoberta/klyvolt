# Klyvolt

Sistema de gestão de consumo de energia elétrica para máquinas de costura de uma empresa de facção (confecção). O projeto monitora o consumo de cada máquina através de sensores, registra leituras periódicas, agrega o consumo por período e aciona decisões automáticas do sistema quando limites pré-definidos são ultrapassados.

## Visão geral

O fluxo de dados segue esta cadeia, do cadastro até a tomada de decisão:

```
empresa → usuario → setor → maquina → sensor → leitura → consumo → tomada_decisao ← decisao
```

- **sensor**: equipamento físico instalado em cada máquina, responsável por medir corrente, tensão ou potência.
- **leitura**: cada medição individual capturada por um sensor, em um instante específico.
- **consumo**: agregação das leituras de uma máquina dentro de um período (ex: um turno, um dia).
- **decisao**: catálogo de tipos de decisão possíveis (ex: desligar máquina, enviar alerta, reduzir potência), cada uma com seu critério de acionamento.
- **tomada_decisao**: registro de uma decisão real, acionada automaticamente pelo sistema a partir de uma leitura ou de um consumo agregado que ultrapassou o limite definido.

## Estrutura do repositório

```
klyvolt/
├── README.md
├── docs/                          # documentação e materiais de apoio do projeto
├── database/
│   └── klyvolt_schema.sql         # script de criação do banco (MySQL)
└── src/
    ├── db_config.py                # dados de conexão com o banco
    ├── conexao.py                  # função compartilhada de conexão
    ├── simulador_sensores.py       # gera leituras simuladas para teste/demonstração
    ├── requirements.txt            # dependências Python
    └── modelos/                    # um arquivo por tabela do banco, com CRUD básico
        ├── empresa.py
        ├── usuario.py
        ├── setor.py
        ├── maquina.py
        ├── sensor.py
        ├── consumo.py
        ├── leitura.py
        ├── decisao.py
        └── tomada_decisao.py
```

## Como rodar o projeto

### 1. Criar o banco de dados

Com o MySQL instalado e rodando, execute o script de criação:

```bash
mysql -u root -p < database/klyvolt_schema.sql
```

Isso cria o banco `klyvolt` com as 9 tabelas, já com as chaves primárias e estrangeiras configuradas.

### 2. Instalar as dependências Python

```bash
pip install -r src/requirements.txt
```

### 3. Configurar a conexão

Edite `src/db_config.py` e troque `SUA_SENHA_AQUI` pela senha real do seu usuário MySQL.

> **Atenção:** não suba `db_config.py` com a senha real para o GitHub. Adicione-o ao `.gitignore` se for versionar o projeto com dados sensíveis.

### 4. Rodar o simulador de sensores (opcional)

Para testar o sistema sem sensores físicos instalados, use o simulador — ele gera leituras realistas para os sensores já cadastrados no banco e as insere automaticamente:

```bash
python src/simulador_sensores.py
```

As leituras geradas por ele são marcadas com `observacao_leitura = 'leitura simulada'`, para serem facilmente identificadas e removidas depois:

```sql
DELETE FROM leitura WHERE observacao_leitura = 'leitura simulada';
```

### 5. Usar os modelos no código

Cada tabela tem um modelo Python correspondente em `src/modelos`, com métodos `criar`, `buscar_por_id`, `listar_todos`, `atualizar` e `deletar`. Exemplo:

```python
from modelos.maquina import Maquina

novo_id = Maquina.criar(
    nome_maquina="Máquina de Costura 01",
    descricao_maquina="Reta industrial",
    potencia_nominal=1.2,
    numero_serie="MC-001",
    ID_setor=1
)

maquina = Maquina.buscar_por_id(novo_id)
print(maquina)
```

## Status do projeto

- [x] Modelo de dados (DER) finalizado, com 9 entidades
- [x] Script SQL de criação do banco
- [x] Modelos Python (CRUD) para todas as tabelas
- [x] Simulador de sensores para testes/demonstração
- [ ] Motor de decisão automática (lógica que lê leituras/consumo e cria registros em `tomada_decisao`)
- [ ] Interface/aplicação para visualização dos dados
