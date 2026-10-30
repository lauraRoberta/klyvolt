# KLYVOLT

Plataforma web de gestão do consumo de energia elétrica para empresas do setor têxtil.
A empresa cadastra setores, máquinas e sensores. Recebe leituras de energia, agrega o consumo
por máquina e período, calcula o custo pela tarifa (R$/kWh) e recebe alertas de regras de decisão.
Tudo isso aparece em um painel de indicadores e relatórios.

---

## 1. Tecnologias

| Camada | Tecnologia |
|---|---|
| Frontend | HTML, CSS e JavaScript puro (sem framework) |
| Backend | Python 3.11+ e FastAPI, com Pydantic para validação e Swagger automático |
| Banco de dados | Supabase (PostgreSQL), acessado pelo backend via HTTPS com a biblioteca `supabase` |
| Autenticação | Supabase Auth (senhas com hash bcrypt, sessão com JWT e renovação automática) |
| Segurança no banco | Row Level Security (RLS): cada empresa só enxerga os próprios dados |

## 2. Arquitetura

```
Navegador (HTML + CSS + JS)
      │  fetch() → JSON  (js/api.js)
      ▼
API FastAPI (backend/main.py, CORS liberado só para o frontend)
      │  controller/*.py → models/*.py (Pydantic) → database.py
      ▼  HTTPS (biblioteca supabase-py)
Supabase (Auth + PostgREST)
      ▼
PostgreSQL (tabelas, RLS, triggers e funções)
```

* O JavaScript **nunca** fala com o Supabase. Ele só chama a API (`API_URL` em `frontend/js/api.js`).
* As credenciais ficam somente em `backend/.env`. O backend usa a chave **pública** (anon/publishable)
  e repassa ao Supabase o token do usuário logado. Assim o RLS do banco funciona como segunda camada
  de proteção. A chave `service_role` não é usada em nenhum lugar.
* Cada requisição autenticada passa por `seguranca.py`, que lê o token (`Authorization: Bearer …`),
  identifica o usuário, a empresa e o perfil (Administrador, Operador ou Visualizador) e
  aplica as permissões antes de acessar o banco.

## 3. Estrutura do projeto

```
klyvolt/
├── README.md
├── .gitignore
├── .env.example                  modelo do arquivo backend/.env (valores fictícios)
├── docs/                         DER, dicionário de dados, relatório final e evidências dos testes
├── database/
│   ├── klyvolt_schema.sql        script completo para criar o banco do zero
│   ├── migracoes/                alterações já aplicadas no Supabase do projeto (em ordem)
│   └── pendente_aprovacao/       scripts que mexem em dados existentes (NÃO executados)
├── backend/
│   ├── main.py                   cria a API, configura CORS e registra as rotas
│   ├── database.py               conexão com o Supabase e tradução de erros para HTTP
│   ├── seguranca.py              autenticação (token) e permissões por perfil
│   ├── requirements.txt
│   ├── simulador_sensores.py     gerador de leituras de TESTE (opcional, identificado)
│   ├── controller/               rotas REST: auth, empresa, usuario, setor, maquina, sensor,
│   │                             leitura, consumo, decisao, tomada_decisao, relatorio
│   └── models/                   modelos Pydantic (entrada, atualização e resposta)
├── frontend/
│   ├── index.html                página inicial pública
│   ├── pages/                    entrar, painel, consumos, registrar-consumo, maquinas,
│   │                             sensores, leituras, setores, decisoes, empresa
│   ├── static/style.css          estilo compartilhado (design aprovado)
│   ├── static/paginas/*.css      estilo específico de cada página (design aprovado)
│   └── js/
│       ├── main.js               tema, menu, animações e componentes de interface
│       ├── api.js                comunicação com a API, sessão e proteção das páginas
│       └── <página>.js           lógica de cada página (CRUD via API)
└── testes/
    ├── backend/test_api.py       testes da API (pytest)
    ├── e2e/                      testes no navegador (Playwright) e comparação visual
    ├── supabase_local/           Supabase local usado só nos testes
    └── subir_ambiente.sh         sobe banco de teste + API + frontend
```

## 4. Configurar o Supabase

1. **Banco.** No *SQL Editor* do Supabase:
   * projeto **novo**: execute `database/klyvolt_schema.sql` inteiro;
   * projeto **atual do KLYVOLT**: nada a fazer. As migrações de `database/migracoes/` já foram aplicadas.
2. **Authentication → URL Configuration:**
   * *Site URL*: `http://127.0.0.1:5500/pages/entrar.html`
   * *Redirect URLs*: adicione `http://127.0.0.1:5500/pages/entrar.html`. Os links de confirmação
     de cadastro e de nova senha voltam para essa página. Use o endereço onde o frontend roda.
3. **Authentication → Sign In / Providers → Email:**
   * com *Confirm email* ligado, o usuário precisa clicar no link do e-mail antes do primeiro login;
     o sistema avisa isso na tela;
   * desligado, o login é imediato após o cadastro.
4. **E-mails.** O servidor de e-mail padrão do Supabase tem limite baixo de envios por hora. Para uso
   real, configure um SMTP próprio em *Authentication → Emails → SMTP Settings*.
5. **Chaves.** Copie a URL e a chave pública em *Project Settings → API*. Use a chave `anon` ou a
   `publishable`, **nunca** a `service_role`.

## 5. Configurar o backend (.env)

```bash
cp .env.example backend/.env
```

Edite `backend/.env`:

```
SUPABASE_URL=https://<seu-projeto>.supabase.co
SUPABASE_KEY=<chave pública anon/publishable>
FRONTEND_URL=http://127.0.0.1:5500
CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
```

O arquivo `.env` está no `.gitignore` e **não deve ir para o GitHub**.

## 6. Instalar e executar

**Backend** (terminal 1):

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

* API: http://127.0.0.1:8000
* Swagger (documentação interativa): http://127.0.0.1:8000/docs

**Frontend** (terminal 2), na pasta `frontend`. Use **Live Server** do VS Code (porta 5500) ou:

```bash
cd frontend
python -m http.server 5500 --bind 127.0.0.1
```

Acesse http://127.0.0.1:5500. Se mudar a porta ou o endereço do frontend, atualize `FRONTEND_URL`
e `CORS_ORIGINS` no `.env` e as URLs do Supabase (item 4). Se mudar o endereço da API, atualize
`API_URL` em `frontend/js/api.js`.

> Abra o frontend sempre por um servidor (`http://…`). Aberto como arquivo (`file://`), o navegador
> bloqueia as requisições por CORS.

## 7. Fluxo de uso

1. Na página inicial, clique em **Começar agora** e cadastre a empresa (CNPJ validado). Quem cadastra
   vira **Administrador**.
2. Em **Empresa**, informe a **tarifa (R$/kWh)**. Sem tarifa, o sistema mostra o consumo e avisa
   que o custo não pode ser calculado.
3. Cadastre, nesta ordem: **Setores → Máquinas → Sensores**.
4. Registre **Leituras** pela tela ou por um sensor físico (`POST /leituras/sensor` com o cabeçalho
   `X-Sensor-Token`). Registre **Consumos** por máquina e período. O kWh pode ser calculado
   automaticamente pela soma das leituras.
5. Crie **Regras de decisão**, por exemplo "leitura > 10 kWh". O banco avalia cada leitura e consumo
   e registra os acionamentos, que a equipe marca como executados ou cancelados.
6. Acompanhe tudo no **Painel**: consumo, custo, média diária, pico, comparação com o período
   anterior, consumo por setor, por máquina e por dia, alertas e **exportação em CSV**.
7. Em **Empresa → Equipe**, o administrador cadastra usuários com os perfis:

| Perfil | Pode |
|---|---|
| Administrador | tudo: empresa, equipe, setores, máquinas, sensores, regras, leituras e consumos |
| Operador | registrar e editar leituras e consumos, atualizar acionamentos; consultar o resto |
| Visualizador | somente consultar |

### Cálculos

* Consumo do período (kWh) = soma das leituras de energia dos sensores da máquina no intervalo
  (`GET /consumos/calcular`). Cada leitura representa a energia medida no seu intervalo.
* Duração (h) = data final − data inicial; média (kWh/h) = consumo ÷ duração.
* Custo (R$) = kWh × tarifa da empresa. Sem tarifa, o custo fica em branco, com aviso.
* Variação (%) = (período atual − período anterior de mesma duração) ÷ período anterior × 100.

## 8. Endpoints (CRUD REST)

Todas as rotas, exceto as marcadas como públicas, exigem `Authorization: Bearer <token>`.

| Recurso | Rotas |
|---|---|
| Autenticação | `POST /auth/login` (pública), `POST /auth/refresh` (pública), `POST /auth/logout`, `GET /auth/me`, `POST /auth/recuperar` (pública), `POST /auth/nova-senha` |
| Empresas | `POST /empresas` (cadastro público), `GET /empresas`, `GET/PUT/DELETE /empresas/{id}` |
| Usuários | `GET/POST /usuarios`, `GET/PUT/DELETE /usuarios/{id}` |
| Setores | `GET/POST /setores`, `GET/PUT/DELETE /setores/{id}` |
| Máquinas | `GET/POST /maquinas`, `GET/PUT/DELETE /maquinas/{id}` |
| Sensores | `GET/POST /sensores`, `GET/PUT/DELETE /sensores/{id}` |
| Leituras | `GET/POST /leituras`, `GET/PUT/DELETE /leituras/{id}`, `POST /leituras/sensor` (token do sensor) |
| Consumos | `GET/POST /consumos`, `GET /consumos/calcular`, `GET/PUT/DELETE /consumos/{id}` |
| Regras de decisão | `GET/POST /decisoes`, `GET/PUT/DELETE /decisoes/{id}` |
| Acionamentos | `GET /tomadas-decisao`, `GET/PUT /tomadas-decisao/{id}` |
| Relatórios | `GET /relatorios/resumo?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` |

**CRUD obrigatório (tabela com chave primária e sem chave estrangeira):** a tabela `empresa` tem CRUD
completo em `backend/controller/empresa.py`, com modelos Pydantic em `backend/models/empresa.py`
(CNPJ, e-mail, telefone e tarifa validados). As demais tabelas também têm CRUD completo.

**Códigos HTTP:**

| Código | Quando |
|---|---|
| 200 | consulta ou atualização |
| 201 | criação |
| 202 | recuperação de senha solicitada |
| 204 | exclusão ou logout |
| 400 | regra de negócio violada |
| 401 | sem login ou sessão expirada |
| 403 | perfil sem permissão |
| 404 | não encontrado ou de outra empresa |
| 409 | duplicado ou registro vinculado |
| 422 | dados inválidos |
| 503 | Supabase fora do ar |

Exemplo:

```bash
curl -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" \
     -d '{"email":"admin@empresa.com.br","senha":"SuaSenha123"}'
curl http://127.0.0.1:8000/maquinas -H "Authorization: Bearer <access_token>"
```

## 9. Simulador de sensores (opcional, somente teste)

`backend/simulador_sensores.py` envia leituras **fictícias** pela mesma rota de um sensor físico.
Ele só roda com `--confirmar`, e cada leitura fica marcada no banco como
"LEITURA SIMULADA (simulador_sensores.py)".

```bash
python simulador_sensores.py --token <token do sensor> --quantidade 10 --confirmar
```

## 10. Testes

A pasta `testes/` tem um ambiente completo e isolado: um Supabase local que reproduz o Auth e o
PostgREST sobre um PostgreSQL com o mesmo `klyvolt_schema.sql`, a API FastAPI real e o frontend real.
Assim os testes não tocam nos dados do Supabase de produção.

```bash
./testes/subir_ambiente.sh                         # requer PostgreSQL local (KV_PGHOST)
python -m pytest testes/backend -v                 # 19 testes da API
cd testes/e2e && npm i playwright @fortawesome/fontawesome-free@6.4.0
node run.js                                        # 44 testes no navegador
node visual.js                                     # comparação com o design aprovado
```

Resultados da última execução (29/10/2026), detalhados em `docs/RELATORIO-FINAL.md`:

* **API:** 19/19 aprovados. Cobrem CRUD de todas as entidades, validações, códigos HTTP, CORS,
  login, logout, sessão expirada, recuperação de senha, perfis, isolamento entre empresas e
  Supabase fora do ar.
* **Navegador:** 44/44 aprovados, sem erros no console. Cobrem cadastro, login, todas as páginas
  com dados reais, cálculos de custo, painel com exportação CSV, equipe, perfis, logout, token
  expirado, recuperação de senha, falhas de rede, layout em 390 px e tema claro.
* **Visual:** diferença máxima de 0,58% dos pixels em relação ao design aprovado. A diferença vem
  apenas dos novos itens de menu (Painel e Máquinas) e dos ícones, que voltaram a aparecer.

## 11. Limitações conhecidas

* Os testes automáticos rodaram contra o Supabase local de testes. No Supabase real foram validadas
  as migrações e as políticas de segurança, com teste de rollback. Falta um teste manual de ponta a
  ponta no Supabase real: o ambiente de desenvolvimento não alcançava a API do Supabase.
* Um membro removido da equipe perde o acesso à empresa, mas a conta de login dele continua no
  Supabase Auth. Excluir contas exige a chave `service_role`, que de propósito não é usada. A remoção
  completa pode ser feita no painel do Supabase (*Authentication → Users*).
* O consumo é calculado como a soma das leituras de energia por intervalo. Não há cálculo por
  potência × tempo de funcionamento nem por medidor acumulado (leitura final − inicial).
* A listagem de leituras traz as 500 mais recentes por padrão (até 2000 com `?limite=`).
* `database/pendente_aprovacao/` contém três scripts **não executados**, que dependem de aprovação:
  remover as senhas em texto puro das tabelas antigas, limpar dados de teste e criar as tabelas de
  categoria e produto.
