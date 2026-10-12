# Plano de Publicação Seletiva e Relatório de Validação — Agillex Agenda

**Data:** 12 de outubro de 2026  
**Projeto:** AllLogic Scheduler (Agillex Agenda)  
**Repositório Local:** `~/AllLogic/Projetos/app-agendamento`  
**Referência de Produção:** Commit `3f225a7` (`origin/main`)  
**Status:** Preparado para revisão (Sem commit, push ou deploy executados)

---

## 1. Contexto e Decisões Estabelecidas

Conforme as diretrizes institucionais da AllLogic (`~/AllLogic/AGENTS.md`, `AGENTS.md` e `FOUNDATION.md`) e as decisões acordadas para esta etapa de publicação seletiva:

1. **Rota `/agillex` descontinuada no produto operacional:** A rota `/agillex` e o fluxo de auto-cadastro automatizado não fazem parte do artefato de produção atual, retornando HTTP `404 Not Found`.
2. **Página comercial `/experimente` definitiva:** A rota `/experimente` renderiza diretamente a interface de conversão comercial com botão de contato direto via WhatsApp (`wa.me/5511966381915`), selo "Sem necessidade de cartão de crédito" e rodapé institucional, sem qualquer redirecionamento HTTP 301.
3. **Rodapé público direcionado a `/experimente`:** A página inicial pública (`/`) exibe link discreto no rodapé direcionando diretamente para a rota interna `/experimente`.
4. **Preservação integral do código de cadastro e provisionamento:** O código de auto-cadastro, tabela `estabelecimento`, funções multi-tenant e templates foram integralmente preservados no repositório no diretório `docs/preservacao-provisionamento-multi-tenant/` com documentação detalhada para futura reativação em contexto SaaS.
5. **Esquema de banco de dados 100% preservado:** O arquivo `database.py` permanece idêntico à versão em produção (`3f225a7`). Nenhuma tabela nova (`estabelecimento`) ou coluna (`admin.estabelecimento_id`) será introduzida na VPS de produção sem necessidade comprovada, evitando multi-tenancy ilusório/parcial.
6. **Preservação de dados existentes:** Nenhum dado foi ou será descartado ou modificado indevidamente. Bancos de homologação locais e de produção permanecem intactos.

---

## 2. Separação Arquitetural e Preservação de Código

### 2.1. O que foi preservado em `docs/preservacao-provisionamento-multi-tenant/`

Para que nenhuma linha de desenvolvimento seja perdida e a retomada futura ocorra com baixo esforço:

| Arquivo Preservado | Conteúdo e Função |
| :--- | :--- |
| `README.md` | Guia completo explicando a arquitetura isolada e os passos para reativação SaaS. |
| `database_extension.py` | DDL da tabela `estabelecimento`, coluna `admin.estabelecimento_id`, migração do ID 1 e funções `criar_estabelecimento_com_admin`, `verificar_status_trial`, `gerar_slug`, etc. |
| `routes_agillex.py` | Implementação completa da rota `/agillex` (GET/POST) com rate limiting (5 POST/min), validações estritas, hashing de senha e rota `/admin/trial-expirado`. |
| `templates/agillex.html` | Template Jinja2 do formulário de auto-cadastro com grid responsivo e termos de serviço. |
| `templates/admin_trial_expirado.html` | Template Jinja2 da tela informativa de trial expirado com canais de suporte e desbloqueio. |
| `styles_agillex.css` | Folha de estilos dedicada aos formulários de cadastro e trial expirado. |
| `tests/test_cadastro_agillex.py` | Suíte com 9 testes automatizados Cobrindo fluxo positivo, duplicidade e rate limit. |

### 2.2. Avaliação de Dependências do Trial

O interceptor de expiração de teste de 14 dias e a rota `/admin/trial-expirado`:
- Eram exclusivos do auto-cadastro `/agillex`.
- O aplicativo operacional atual (instalação single-tenant dedicada em VPS) não possui expiração de trial para o estabelecimento piloto.
- Manter o interceptor no fluxo operacional exigiria consultar a tabela `estabelecimento`, o que forçaria alteração de esquema em produção ou causaria exceções de banco de dados (`UndefinedTable`).
- **Conclusão:** O interceptor foi removido do fluxo operacional ativo de `app.py` e preservado em `docs/preservacao-provisionamento-multi-tenant/routes_agillex.py`.

---

## 3. Lista Exata de Arquivos Selecionados para o Artefato de Produção

### 3.1. Arquivos Modificados (Tracked)

1. `app.py`:
   - Adicionada a rota `@app.route("/experimente")` renderizando `experimente.html` com `_carregar_config_template()`.
   - Limpeza de imports não utilizados (`URL_AGILLEX`, `URL_EXPERIMENTE`, `generate_password_hash`).
   - Reversão do decorador `login_requerido` e de `admin_login` para a verificação padrão de credenciais sem dependência de trial.
2. `templates/index.html`:
   - Atualizado o link do rodapé comercial para `href="{{ url_for('experimente') }}"`.
3. `templates/base_admin.html`:
   - Atualizado o cabeçalho superior (`topbar-page-title` exibe `Agillex Agenda`).
   - Sidebar: rótulo simplificado para `Agenda`.
   - Adicionado o rodapé institucional `.admin-footer` com marca AllLogic Online, slogan e contatos oficiais.
4. `templates/admin_dashboard.html`:
   - Atualizados os blocos `titulo_pagina` para `Agillex Agenda` e `subtitulo_topbar` para `Painel Administrativo`.
5. `static/css/style.css`:
   - Estilos da página `/experimente` (`.card-beneficios`, `.btn-iniciar-teste`, `.experimente-selo-sem-cartao`, `.experimente-contatos-canais`, etc.).
   - Estilos do rodapé institucional `.admin-footer` (desktop e mobile).
   - Correção responsiva das abas do dashboard e alinhamento do seletor de profissionais em dispositivos móveis (375px e 360px).
   - Remoção de classes órfãs de auto-cadastro.

### 3.2. Arquivos Novos (Untracked) a Incluir na Publicação

1. `templates/experimente.html`:
   - Página comercial com chamada para teste gratuito de 14 dias.
   - Botão WhatsApp apontando para `https://wa.me/5511966381915?text=Ol%C3%A1!%20Gostaria%20de%20iniciar%20meu%20teste%20gratuito%20de%2014%20dias%20do%20Agillex%20Agenda.`.
   - Selo "Sem necessidade de cartão de crédito".
   - Cards com benefícios operacionais do sistema.
   - Canais de contato direto e rodapé institucional AllLogic Online.

### 3.3. Arquivos Intactos (Não Modificados / Sem Alterações de Esquema)

- `database.py`: 100% idêntico a `3f225a7`.
- `config.py`: 100% idêntico a `3f225a7`.
- `.env`: 100% intacto.

---

## 4. Resultados das Validações e Testes

Todos os testes exigidos na Etapa 4 foram executados localmente:

### 4.1. Compilação de Bytecode Python
```bash
python3 -m compileall app.py config.py database.py models.py email_service.py
```
- **Resultado:** 100% aprovado, zero erros de compilação ou sintaxe.

### 4.2. Verificação de Espaços e Quebras de Linha Git
```bash
git diff --check
```
- **Resultado:** 100% aprovado, zero advertências de whitespace ou caracteres espúrios.

### 4.3. Suíte de Testes Automatizados (Pytest)
Executada contra banco PostgreSQL de teste isolado (`scheduler_test_pytest_isolated`):
```bash
PYTHONPATH=. SCHEDULER_TEST_DATABASE=1 pytest tests/ -v
```
- **Resultado:** **48 testes executados e 48 testes APROVADOS (100% de sucesso)** em 25.02s.
  - `test_ajustes_semana_dashboard.py` (9/9 passados)
  - `test_bloco1.py` (7/7 passados)
  - `test_bloco2.py` (6/6 passados)
  - `test_bloco3.py` (5/5 passados)
  - `test_bloco3_acoes.py` (11/11 passados)
  - `test_pesquisa.py` (10/10 passados)

### 4.4. Testes Automatizados de Rotas e Templates
Executados via Flask Test Client e requisições HTTP locais no servidor:
- `GET /`: Retorna `200 OK`, rodapé público contém link para `/experimente`.
- `GET /experimente`: Retorna `200 OK` (sem redirect 301), contém botão oficial para WhatsApp (`wa.me/5511966381915`), texto "Iniciar 14 dias de teste grátis" e selo "Sem necessidade de cartão de crédito".
- `GET /agillex`: Retorna `404 Not Found` (rota indisponível no artefato operacional).
- `GET /admin/trial-expirado`: Retorna `404 Not Found` (rota indisponível).
- `GET /admin/login`: Retorna `200 OK`.
- `GET /admin` (Dashboard): Retorna `200 OK`, exibe "Agillex Agenda", "Painel Administrativo", abas responsivas e rodapé institucional "AllLogic Online".
- `GET /admin/servicos`, `/admin/profissionais`, `/admin/configuracoes`: Retornam `200 OK` com rodapé institucional validado.

---

## 5. Análise de Riscos e Procedimento de Rollback

| Risco Potencial | Nível | Medida Preventiva Adotada |
| :--- | :--- | :--- |
| Impacto no banco de dados da VPS | Nulo | O schema não é alterado (`database.py` permaneceu idêntico ao commit em produção `3f225a7`). |
| Redirecionamento indevido de `/experimente` | Nulo | Removido o 301 para `/agillex`; a página é renderizada diretamente com HTTP 200. |
| Falha de autenticação admin | Nulo | Removidos os interceptores de trial; rotinas originais de login e troca de senha preservadas e testadas. |
| Regressão visual no mobile | Nulo | Regras CSS testadas para larguras 375px e 360px com grid e overflow prevenidos. |

### Estratégia de Rollback
Caso ocorra qualquer divergência imprevista durante a publicação, o rollback consiste exclusivamente em restaurar o commit `3f225a7` via Git na VPS (`git checkout 3f225a7`), sem necessidade de reversão de migrações DDL de banco de dados.

---

## 6. Próximos Passos

A preparação e a validação estão concluídas com sucesso. O artefato está pronto para revisão final. **Nenhum commit, push ou comando de deploy foi executado nesta etapa**, aguardando autorização expressa do usuário.
