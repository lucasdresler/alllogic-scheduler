# Validação da Fase 2 — 2026-09-30

## 1. Objetivo
Implementar o primeiro bloco da Fase 2 (Backend/API + Segurança Core) conforme especificação:
- Advisory lock em `criar_agendamento` para evitar race condition
- Coluna `ativo` em `servico` com filtro nas listagens públicas
- Tabela `profissional_servico` N:M e regra de disponibilidade
- Remoção do auto-update de status para `realizado` no `init_db`
- CSRF protection (Flask-WTF) nos formulários administrativos
- Rate limiting (Flask-Limiter) no `/admin/login`
- Atualização de `REGRAS-AGENDAMENTOS.md` com 4 status e transições

## 2. Arquivos alterados
- `requirements.txt` — adição de Flask-WTF e Flask-Limiter
- `database.py` — coluna `ativo` em `servico`, tabela `profissional_servico`, remoção de `atualizar_agendamentos_realizados`
- `models.py` — advisory lock em `criar_agendamento`, filtro `ativo` em `listar_servicos`/`listar_profissionais`, validação `profissional_servico` em `horarios_disponiveis`
- `app.py` — CSRF protection, rate limiting, exempt nas APIs JSON
- `templates/admin_login.html` — CSRF token no form
- `templates/admin_alterar_senha.html` — CSRF token no form
- `docs/REGRAS-AGENDAMENTOS.md` — 4 status, transições, receita do período, regra crítica

## 3. Alterações realizadas

### requirements.txt
- Adicionado `Flask-WTF==1.2.2` e `Flask-Limiter==3.8.0`

### database.py
- Tabela `servico`: adicionada coluna `ativo BOOLEAN NOT NULL DEFAULT TRUE` (com `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para compatibilidade)
- Criada tabela `profissional_servico` com FKs para `profissional` e `servico` (ON DELETE CASCADE)
- Removida chamada a `atualizar_agendamentos_realizados(conn)` do `init_db`
- Mantida migração `ALTER TABLE servico ADD COLUMN IF NOT EXISTS ativo` para bancos existentes

### models.py
- `listar_servicos(apenas_ativos=True)`: filtra por `ativo = TRUE` quando solicitado
- `listar_profissionais(apenas_ativos=True)`: mantém filtro existente por `ativo = TRUE`
- `horarios_disponiveis`: adicionada validação de que o profissional realiza TODOS os serviços selecionados (consulta `profissional_servico`)
- `criar_agendamento`: implementado advisory lock `pg_advisory_xact_lock` com chave baseada em `profissional_id * 1000000 + data_int`; revalidação completa de disponibilidade dentro da transação com lock

### app.py
- Inicialização `CSRFProtect(app)` e `Limiter` com storage em memória
- Decorador `@limiter.limit("5 per minute")` na rota `/admin/login`
- `csrf.exempt()` nas 4 rotas de API pública (`api_services`, `api_professionals`, `api_availability`, `api_appointments`)
- APIs `/api/services` e `/api/professionals` passam `apenas_ativos=True`

### templates
- `admin_login.html`: adicionado `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
- `admin_alterar_senha.html`: adicionado `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`

### docs/REGRAS-AGENDAMENTOS.md
- Status expandidos para 4: `agendado`, `realizado`, `nao_compareceu`, `cancelado`
- Adicionadas seções "Agendamento realizado" e "Agendamento não compareceu" com regras
- Adicionada seção "Receita do período" (agendado + realizado)
- Atualizada regra de disponibilidade: cancelados, realizados e não compareceram não bloqueiam
- Adicionada tabela de transições permitidas (8 transições válidas, 4 inválidas)
- Adicionados: Registro de origem, Histórico de status, Regra crítica (não auto-update)
- Mantida seção de antecedência máxima

## 4. Validações executadas

| # | Comando/Teste | Objetivo | Resultado |
|---|---------------|----------|-----------|
| 1 | `models.criar_agendamento` concorrente mesmo profissional+data+horário | Advisory lock impede race condition | **PASSOU** — Primeiro cria, segundo falha com "Horário não disponível" |
| 2 | `models.criar_agendamento` mesmo profissional+data, horário diferente | Lock não bloqueia horários diferentes | **PASSOU** — Cria normalmente |
| 3 | `listar_servicos(apenas_ativos=True/False)` | Filtro por coluna `ativo` | **PASSOU** — Retorna 3 ativos, 3 totais; após desativar um, retorna 2 ativos, 3 totais |
| 4 | `listar_profissionais(apenas_ativos=True/False)` | Filtro por coluna `ativo` (existente) | **PASSOU** — Retorna 2 ativos, 2 totais |
| 5 | `horarios_disponiveis` com profissional_servico | Profissional deve fazer TODOS os serviços | **PASSOU** — Carlos (faz 22,23) tem slots para [22] e [22,23]; Rafael (faz 22,24) tem 0 slots para [22,23] e slots para [24] |
| 6 | `init_db` não chama `atualizar_agendamentos_realizados` | Auto-update removido | **PASSOU** — Verificado no source; agendamento antigo permanece `agendado` após re-run do `init_db` |
| 7 | CSRF token em `/admin/login` e `/admin/alterar-senha` | Formulários protegidos | **PASSOU** — Token presente em ambos os forms |
| 8 | Login admin com CSRF válido | Autenticação funciona | **PASSOU** — Status 302 (redirect para dashboard) |
| 9 | APIs JSON (`/api/services`, `/api/professionals`, `/api/availability`, `/api/appointments`) | Isentas de CSRF | **PASSOU** — Todas respondem 200/201 sem token |
| 10 | API appointment creation | Fluxo público funcional | **PASSOU** — Cria agendamento com data válida (amanhã) |
| 11 | Rate limiting em `/admin/login` | Proteção contra brute-force | **PASSOU** — `@limiter.limit("5 per minute")` aplicado; teste real disparou HTTP 429 na 4ª-5ª tentativa falha; login legítimo funciona em sessão nova (HTTP 302); storage `memory://` usado |
| 12 | Syntax/import de `app`, `models`, `database`, `config` | Código válido | **PASSOU** — Todos importam sem erro |
| 13 | `init_db` re-executável | Migração idempotente | **PASSOU** — Dados preservados (3 serviços, 2 profissionais, 7 agendamentos, 9 configs, 1 admin, 4 profissional_servico) |
| 14 | Documentação `REGRAS-AGENDAMENTOS.md` | 4 status, transições, regras | **PASSOU** — Todos os elementos verificados por busca textual |

## 5. Validação de banco e migração
- **Estrutura**: Coluna `servico.ativo` adicionada com `DEFAULT TRUE` e `ALTER TABLE ... IF NOT EXISTS` — compatível com bancos existentes
- **Tabela `profissional_servico`**: Criada com `CREATE TABLE IF NOT EXISTS` + FKs `ON DELETE CASCADE` — sem impacto em dados existentes
- **Dados preservados**: Após re-run do `init_db`, mantidos 3 serviços, 2 profissionais, 7 agendamentos, 9 configurações, 1 admin, 4 vínculos profissional_servico
- **Sem perda de dados**: Nenhuma coluna removida, nenhuma tabela dropada, nenhuma migração destrutiva
- **Rollback**: Como são apenas `ADD COLUMN IF NOT EXISTS` e `CREATE TABLE IF NOT EXISTS`, rollback natural seria `DROP COLUMN` / `DROP TABLE` se necessário (não testado, mas estrutura permite)

## 6. Validação funcional
- **Fluxo público de agendamento**: API `/api/appointments` cria agendamento com validação de disponibilidade, antecedência, profissional_servico e advisory lock — testado e funcionando
- **Acesso administrativo**: Login `/admin/login` com CSRF token válido redireciona para dashboard; form de alteração de senha também possui CSRF token
- **APIs públicas**: `/api/services` e `/api/professionals` retornam apenas itens ativos; `/api/availability` respeita regra profissional_servico; `/api/appointments` cria agendamento

## 7. Segurança
- **CSRF**: Flask-WTF habilitado globalmente; formulários admin (`login`, `alterar-senha`) possuem token; APIs JSON isentas via `csrf.exempt()`
- **Rate limiting**: Flask-Limiter configurado com `default_limits=["200 per day", "50 per hour"]` e limite específico `@limiter.limit("5 per minute")` em `/admin/login`. Teste real confirmou: HTTP 429 retornado após ~5 tentativas falhas consecutivas; login legítimo em sessão nova funciona (HTTP 302). **Limitação conhecida**: storage `memory://` não compartilha contadores entre workers Gunicorn. Em produção com 2 workers, limite efetivo seria ~10 req/min por IP. Para V1 é aceitável; migrar para Redis quando houver necessidade real.
- **Advisory lock**: `pg_advisory_xact_lock` em `criar_agendamento` previne race condition na criação de agendamentos concorrentes para mesmo profissional+data

## 8. Problemas encontrados e correções
Nenhum problema encontrado.

## 9. Estado final
A implementação está **PRONTA PARA COMMIT**. Todas as validações passaram, dados preservados, funcionalidades testadas.

## 10. Pendências
- **Rate limiting storage**: `memory://` não compartilha contadores entre workers Gunicorn. Em produção com 2 workers, limite efetivo por IP dobra. Documentado como limitação conhecida; migração para Redis apenas quando houver necessidade real (fora do escopo da Fase 2). Nenhuma outra pendência real encontrada nesta validação. As próximas fases (CRUD admin, Cliente, Reagendamento, Token, Estabelecimento, UX, Testes, Backup, Homologação) permanecem conforme roadmap.