# KLYVOLT: relatório final da reconstrução full stack

Data: 29/10/2026. Base: `KLYVOLT.zip`, com o design aprovado e a integração anterior, mais o
backend original e o banco no Supabase do projeto.

## 1. Resultado

O sistema segue o padrão exigido. O frontend (HTML/CSS/JS) chama, via JavaScript, a API FastAPI em
Python, que acessa o Supabase via HTTPS, que por sua vez grava no PostgreSQL.

* O JavaScript não acessa mais o Supabase diretamente. A versão anterior usava `supabase-js` no
  navegador. Toda leitura e gravação passa pela API.
* As credenciais ficam somente em `backend/.env`, que não vai para o Git. Não há chave privilegiada
  em lugar nenhum.
* A identidade visual foi preservada. A comparação pixel a pixel com o design aprovado está no
  item 6.

## 2. Estrutura definitiva

Veja o item 3 do `README.md`. O resumo: `backend/` tem `main.py`, `database.py`, `seguranca.py`,
`controller/` e `models/`. `frontend/` tem `index.html`, `pages/`, `static/` e `js/`. `database/`
tem o schema completo e as migrações. `testes/` e `docs/` completam o projeto.

## 3. Arquivos

### Criados

| Arquivo | Função |
|---|---|
| `backend/main.py` | App FastAPI, CORS por variável de ambiente, rotas e tratamento de erros (503 se o Supabase cair) |
| `backend/database.py` | Clientes Supabase (público e com o token do usuário) e tradução de erros do banco para HTTP |
| `backend/seguranca.py` | Lê o token, carrega usuário, empresa e perfil, e aplica as permissões por perfil |
| `backend/controller/*.py` (11) | auth, empresa, usuario, setor, maquina, sensor, leitura, consumo, decisao, tomada_decisao, relatorio |
| `backend/models/*.py` (11) | Modelos Pydantic de entrada, atualização e resposta, com validações (CNPJ, e-mail, telefone, MAC, IP, valores ≥ 0, datas) |
| `backend/simulador_sensores.py` | Gerador de leituras de teste, separado e identificado |
| `backend/requirements.txt` | Dependências com versões fixas |
| `database/klyvolt_schema.sql` | Script único para criar o banco do zero (equivalência com o banco real verificada) |
| `database/migracoes/20261029_05_api_fastapi_equipe.sql` | Perfil do usuário para a API, convites de equipe e permissões de edição e exclusão |
| `frontend/pages/painel.html` + `js/painel.js` | Painel de indicadores e relatórios, com exportação CSV |
| `frontend/pages/entrar.html` + `js/auth.js` | Cadastro, login, recuperação e nova senha |
| `frontend/pages/maquinas.html` + `js/maquinas.js` | CRUD de máquinas, com consumo e custo por máquina |
| `frontend/js/api.js` | Comunicação com a API, sessão, renovação de token e proteção das páginas |
| `frontend/js/main.js` | Comportamento do design (tema, menu, animações) e componentes (avisos, confirmação, listas, gráfico) |
| `frontend/js/<página>.js` | Uma por página, todas via API |
| `testes/backend/test_api.py`, `testes/e2e/*`, `testes/supabase_local/*`, `testes/subir_ambiente.sh` | Testes automatizados e ambiente isolado |
| `README.md`, `.env.example`, `.gitignore`, `docs/RELATORIO-FINAL.md`, `docs/evidencias/` | Documentação e evidências |

### Modificados (reorganizados para o padrão da escola)

| Antes | Agora |
|---|---|
| `frontend/assets/design.css` | `frontend/static/style.css`. Conteúdo igual, mais os estilos dos componentes novos (avisos, confirmação, painel) e a correção dos ícones (item 6) |
| `frontend/pages/<pagina>/index.html` | `frontend/pages/<pagina>.html`. Mesmo HTML, com os caminhos ajustados e os links "Painel" e "Máquinas" no menu |
| `frontend/pages/<pagina>/style.css` | `frontend/static/paginas/<pagina>.css`, sem alteração |
| `frontend/assets/site.js` | Incorporado em `frontend/js/main.js` |
| `frontend/index.html` | Caminhos ajustados; o link "Painel" e os botões levam ao cadastro e ao login |
| `backend/migrations/*` | Movidos para `database/migracoes/` |
| `backend/pendente_aprovacao/*` | Movidos para `database/pendente_aprovacao/` |

### Removidos (substituídos, sem duas implementações concorrentes)

| Arquivo | Motivo |
|---|---|
| `frontend/assets/config.js` e `frontend/assets/app.js` | Acessavam o Supabase direto do navegador. Substituídos por `js/api.js` |
| `frontend/assets/pages/*.js` | Reescritos em `frontend/js/*.js` usando a API |
| `frontend/assets/records.js` (design) | Dados de exemplo fixos; os dados agora vêm do banco |
| Backend antigo: `Database/`, `routes/`, `schemas.py`, `models.py`, `deps.py`, `seguranca.py` e o `script_sql` solto | Substituídos pela estrutura `controller/`, `models/`, `database.py` e `seguranca.py` e pelo `database/klyvolt_schema.sql` |
| `LEIA-ME.md`, `RELATORIO-TECNICO.md` e os testes da versão anterior | Substituídos por `README.md`, este relatório e `testes/` |

## 4. Funcionalidades

* **Acesso:** a página inicial é pública. Entrar e Cadastrar levam a uma sessão (JWT) e ao painel
  interno. Há logout, renovação automática do token expirado e redirecionamento para o login
  com volta à página pedida. Há recuperação de senha por e-mail e suporte à confirmação de e-mail.
  As senhas ficam com hash no Supabase Auth.
* **Empresas e equipe:** cadastro com validação de CNPJ; edição de dados e tarifa; exclusão
  em cascata, com confirmação. Na equipe, o administrador cadastra Operadores e Visualizadores. As
  permissões são conferidas no backend e no banco (RLS).
* **Isolamento:** cada empresa vê e altera só os próprios dados. Tentativas diretas na API com o
  ID de outra empresa recebem 404 ou 403.
* **CRUD completo:** setores, máquinas, sensores (o token do sensor nunca volta da API), leituras,
  consumos, regras de decisão e acionamentos.
* **Monitoramento:** leituras pela tela ou por sensor físico (`X-Sensor-Token`). As regras de decisão
  são avaliadas pelo banco a cada leitura ou consumo, e os alertas têm status
  (pendente, executada, cancelada).
* **Relatórios:** consumo por período, setor, máquina e dia; custo pela tarifa; média diária; pico;
  comparação com o período anterior; alertas; gráfico e exportação CSV (abre no Excel).
* **Sem dados fictícios:** sem registros, as telas mostram estados vazios. Sem tarifa, aparece o
  aviso "Defina a tarifa em Empresa", e o custo não é inventado.

## 5. Ajustes no Supabase

* **Aplicada no projeto real:** a migração `20261029_05_api_fastapi_equipe.sql`. Antes, ela passou
  por um teste com rollback, com 11 verificações aprovadas.
  * Função `kv_perfil_atual()`.
  * Tabela `convite_usuario`, com RLS restrita a administradores.
  * Cadastro de membros por convite.
  * Políticas e permissões de edição e exclusão de usuários e de exclusão da empresa.
  * Chave `setor.id_usuario_responsavel` com `ON DELETE NO ACTION`, para impedir que um setor fique
    sem responsável.
  * Nenhum dado foi apagado.
* **Já existentes (fase anterior):** as migrações 01 a 04, com multiempresa, Auth, RLS, regras de
  negócio e histórico de decisões.
* **Não executados (aguardam aprovação):** os três scripts de `database/pendente_aprovacao/`.
  * **A** remove as senhas em texto puro de 7 empresas e 7 usuários das tabelas antigas.
  * **B** limpa os dados de teste.
  * **C** cria as tabelas de categoria e produto.

## 6. Testes executados e resultados

| Suíte | Resultado | Evidência |
|---|---|---|
| API (pytest, FastAPI real) | **19/19 aprovados** | `docs/evidencias/testes-api.txt` |
| Navegador (Playwright, página → API → Supabase local → Postgres com RLS) | **44/44 aprovados, 0 erros de console** | `docs/evidencias/testes-navegador.txt` e capturas `.jpg` |
| Comparação visual com o design aprovado (1440 e 390 px, tema escuro e claro) | Diferença máxima de **0,58%** | `docs/evidencias/comparacao-visual.txt` |
| Responsividade em 390 px (todas as páginas) | Nenhuma rolagem horizontal | teste 43 |
| Schema (`klyvolt_schema.sql`) × banco real | 431 itens estruturais idênticos | verificação no Postgres |

**Correção visual, a única alteração de aparência.** O CSS do design tinha a regra
`body.app-page *{font-family:inherit}`. Ela anulava a fonte do Font Awesome, e todos os ícones
previstos no HTML apareciam como quadrados vazios. Agora só a fonte dos ícones é restaurada, e
cores, tipografia, layout e animações continuam iguais. Para voltar ao comportamento anterior, basta
apagar as 3 últimas regras de `static/style.css`.

## 7. Como executar

Veja os itens 4 a 6 do `README.md`:

1. Configure as URLs de redirecionamento no Supabase.
2. Copie `.env.example` para `backend/.env`.
3. Rode `uvicorn main:app --reload` em `backend/`.
4. Abra `frontend/` na porta 5500.

## 8. Limitações

* Os testes ponta a ponta rodaram no Supabase local de testes. A API do Supabase real não era
  acessível do ambiente de desenvolvimento. É preciso um teste manual no projeto real: cadastro,
  login e um CRUD de cada página.
* Um membro removido perde o acesso, mas a conta de login dele continua no Supabase Auth. A exclusão
  definitiva é feita em *Authentication → Users*, porque a API não usa a chave `service_role`.
* O consumo é calculado como a soma das leituras de energia por intervalo. Não há cálculo por
  potência × tempo nem por medidor acumulado.
* A listagem de leituras traz as 500 mais recentes por padrão (até 2000 com `?limite=`).
