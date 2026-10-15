# Relatório de Deploy em Produção — Multi-Tenancy com Isolamento de Dados, Páginas Públicas por Slug e Seed de Serviços

**Data da Implantação:** 15/10/2026 (Local BRT) / 15/10/2026 (UTC)  
**Projeto:** AllLogic Scheduler (Agillex Agenda) — `~/AllLogic/Projetos/app-agendamento`  
**Servidor de Produção:** VPS KingHost (`177.153.203.158`)  
**URLs Oficiais em Produção:**
- `https://agenda.alllogiconline.com.br/` (Página pública padrão / Estabelecimento 1)
- `https://agenda.alllogiconline.com.br/agendar/<slug>` (Página pública isolada por estabelecimento)
- `https://agenda.alllogiconline.com.br/<slug>` (Alias público direto amigável com proteção de rotas reservadas)
- `https://agenda.alllogiconline.com.br/agillex` (Onboarding de trial com seed automático de 2 serviços)
- `https://agenda.alllogiconline.com.br/admin/` (Painel com banner e botão "Copiar Link do Agendamento")
**Commit de Deploy:** `45b6323`  
**Backup Pré-Deploy na VPS:** `/opt/alllogic/backups/scheduler/pre-45b6323-20261015T192815Z/`  
**Tag Docker de Rollback:** `scheduler-scheduler:rollback-5f0412c-20261015T192815Z`  
**Suíte de Testes Automatizados:** 68/68 testes aprovados (100% de sucesso)  
**Status Final:** **DEPLOY CONCLUÍDO COM SUCESSO**

---

## 1. Contexto e Requisitos Atendidos

1. **Isolamento Completo Multi-Tenant:**
   - Adicionada coluna `estabelecimento_id` e índices de alta performance nas tabelas:
     * `servico` (com índice `idx_servico_estabelecimento_id`)
     * `profissional` (com índice `idx_profissional_estabelecimento_id`)
     * `agendamento` (com índice `idx_agendamento_estabelecimento_id`)
     * `cliente` (com índice `idx_cliente_estabelecimento_id`)
   - Expansão da tabela `estabelecimento` para armazenar de modo independente:
     * Dados cadastrais: `nome_fantasia`, `razao_social`, `logotipo`, endereço completo.
     * Parâmetros operacionais da agenda: `horario_abertura`, `horario_fechamento`, `intervalo_slot_minutos`, `dias_funcionamento`, `dias_antecedencia_agendamento`.
   - Compatibilidade estrita preservada para o estabelecimento piloto (ID 1), mantendo a precedência das configurações globais legadas.

2. **Rotas Públicas por Slug e Prevenção de Colisão:**
   - Implementada rota explícita `/agendar/<slug>` para agendamento online do estabelecimento.
   - Implementado alias amigável `/<slug>` protegido pela lista `ROTAS_RESERVADAS` (bloqueando colisões com `admin`, `api`, `agillex`, `static`, etc.).
   - Rota `/` mantida com estabelecimento padrão (ID 1).
   - Injeção contextual das variáveis JavaScript `window.ESTABELECIMENTO_ID` e `window.ESTABELECIMENTO_SLUG` no template público `index.html`.
   - Adaptação das chamadas assíncronas do frontend (`/api/services`, `/api/professionals`, `/api/availability`, `/api/appointments`) para repassar o tenant selecionado.

3. **Link de Agendamento no Dashboard Administrativo:**
   - Banner de destaque no topo do Dashboard Administrativo com o endereço público oficial da agenda (`https://agenda.alllogiconline.com.br/agendar/<slug>`).
   - Botão interativo "Copiar Link" com feedback visual de confirmação e fallback robusto para navegadores sem suporte à Clipboard API moderna.
   - Botão "Visualizar Página" com abertura em nova aba (`target="_blank"`).
   - Menu lateral administrativo atualizado com o link dinâmico da página pública.

4. **Seed Automático no Onboarding (`/agillex`):**
   - Criação automática de 2 serviços iniciais ("Atendimento Especial" e "Serviço Completo") no momento do cadastro de trial.
   - Preservação da cota de profissionais do plano (não auto-cadastra profissional provisório), permitindo que o gestor cadastre sua equipe real sem atingir limite precoce.

---

## 2. Linha do Tempo da Operação de Deploy

| Horário (UTC) | Etapa / Operação | Detalhes / Status |
|:---:|:---|:---|
| 19:25:53 | Execução da suíte completa de testes | 68 testes executados com 100% de aprovação (pytest) |
| 19:26:22 | Commit no repositório git local | `45b6323` |
| 19:26:28 | Push para o repositório remoto | `origin main` atualizado com sucesso |
| 19:27:40 | Baseline HTTP de produção | `HTTP/2 200 OK` confirmado em `/` e `/admin/login` |
| 19:27:50 | Execução do Backup de Salvaguarda | Dump PostgreSQL, `compose.yaml`, `.env`, Git Bundle e tag de rollback |
| 19:27:50 | Validação dos checksums SHA-256 | 4 artefatos com checksums verificados com `OK` |
| 19:27:56 | `git pull --ff-only origin main` na VPS | Fast-forward para `45b6323` |
| 19:28:04 | `docker compose build scheduler` | Imagem Docker reconstruída com sucesso |
| 19:28:04 | `docker compose up -d scheduler` | Container `alllogic-scheduler` reiniciado |
| 19:28:12 | Migração automática do schema (`init_db`) | Colunas, índices e foreign keys criados no PostgreSQL |
| 19:28:17 | Verificação de integridade dos registros | 100% dos dados pré-existentes preservados intactos |
| 19:28:56 | Smoke tests HTTP/2 pós-deploy | 200 OK em todas as rotas públicas, administrativas e API |

---

## 3. Artefatos de Salvaguarda Criados na VPS

- **Diretório:** `/opt/alllogic/backups/scheduler/pre-45b6323-20261015T192815Z/`
- **Conteúdo:**
  1. `postgres-alllogic_scheduler.dump` (Dump PostgreSQL custom gzip).
  2. `compose.yaml` (Definição de serviço Docker).
  3. `.env` (Variáveis de ambiente, modo estrito `chmod 600`).
  4. `source-before.bundle` (Bundle completo do repositório Git no commit anterior `5f0412c`).
  5. `SHA256SUMS` (Manifesto assinado de integridade SHA-256).
- **Tag Docker de Rollback:** `scheduler-scheduler:rollback-5f0412c-20261015T192815Z`

---

## 4. Validação Pós-Deploy em Produção

1. **Rotas Públicas:**
   - `https://agenda.alllogiconline.com.br/` — `HTTP/2 200 OK`
   - `https://agenda.alllogiconline.com.br/agendar/default` — `HTTP/2 200 OK`
   - `https://agenda.alllogiconline.com.br/default` — `HTTP/2 200 OK`
   - `https://agenda.alllogiconline.com.br/agillex` — `HTTP/2 200 OK`
2. **Painel Administrativo:**
   - `https://agenda.alllogiconline.com.br/admin/login` — `HTTP/2 200 OK`
3. **APIs Assíncronas:**
   - `/api/services?estabelecimento_id=1` — `HTTP/2 200 OK`
   - `/api/professionals?estabelecimento_id=1` — `HTTP/2 200 OK`
4. **Integridade de Dados:**
   - Estabelecimentos: 1 (preservado)
   - Serviços: 7 (preservados)
   - Profissionais: 2 (preservados)
   - Agendamentos: 22 (preservados)
   - Clientes: 15 (preservados)
5. **Gunicorn / Docker:**
   - 2 workers ativos, logs limpos sem exceções.

---

## 5. Parecer Final

A atualização multi-tenant do **AllLogic Scheduler (Agillex Agenda)** está oficialmente publicada e operacional em produção na VPS KingHost, com total isolamento de dados por estabelecimento, páginas de agendamento por slug, seed inicial de serviços no trial e banner de compartilhamento no dashboard.
