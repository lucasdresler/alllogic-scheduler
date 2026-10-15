# Relatório de Deploy em Produção — Planos Comerciais, Upgrade no Admin e Alinhamento Visual Agillex

**Data da Implantação:** 15/10/2026 (Local BRT) / 15/10/2026 (UTC)  
**Projetos Envolvidos:**
1. **Site Institucional AllLogic Online:** `~/AllLogic/Site` (Deploy cPanel `177.104.163.165:21008`)
2. **AllLogic Scheduler (Agillex Agenda):** `~/AllLogic/Projetos/app-agendamento` (Deploy VPS KingHost `177.153.203.158`)  
**URLs Oficiais em Produção:**
- `https://alllogiconline.com.br/agillex-agenda/` (Página de vendas e apresentação do produto)
- `https://agenda.alllogiconline.com.br/agillex` (Página de ativação de trial de 14 dias com seleção de planos)
- `https://agenda.alllogiconline.com.br/admin/` (Painel Administrativo com Upgrade de Planos)
**Commit Ativo no Site:** `c69bc9b4b0a48b52a5a5700e57200778c1efc029` (`c69bc9b`)  
**Commit Ativo no Scheduler:** `46699d4808b6119f6c26df09bb212d06258f4371` (`46699d4`)  
**Backup Pré-Deploy Site (cPanel):** `/home2/alllogiconline/backups/public_html-pre-deploy-20261015-081258.tar.gz`  
**Backup Pré-Deploy Scheduler (VPS):** `/opt/alllogic/backups/scheduler/pre-46699d4-20261015T111612Z/`  
**Responsável Técnico:** Antigravity AI Pair Programming  
**Status Final:** **DEPLOY CONCLUÍDO COM SUCESSO**

---

## 1. Contexto e Requisitos Atendidos

Em conformidade com a autorização expressa do fundador, foram implementadas, testadas e publicadas com segurança as seguintes melhorias:

1. **Inserção de Preços e Opções no Site Institucional (`https://alllogiconline.com.br/agillex-agenda/`):**
   - Seção de planos e preços interativa com alternador Mensal/Anual (com desconto de 20% no anual).
   - Card de destaque no plano Intermediário ("Mais Escolhido").
   - CTAs direcionados e parametrizados:
     * `https://agenda.alllogiconline.com.br/agillex?plano=inicial`
     * `https://agenda.alllogiconline.com.br/agillex?plano=intermediario`
     * `https://agenda.alllogiconline.com.br/agillex?plano=avancado`
   - Nota unificada: 14 dias de teste grátis sem cartão de crédito e sem fidelidade.

2. **Refatoração da Página de Cadastro de Trial (`https://agenda.alllogiconline.com.br/agillex`):**
   - Alinhamento integral com a identidade visual da AllLogic Online (`#0a1f44`, `#1f6fff`, `#c9a227`, `#f4f6fa`).
   - Remoção completa do botão "Voltar ao agendamento".
   - Seletor interativo em formato de cards visuais para os 3 planos comerciais (Inicial, Intermediário e Avançado), com pré-seleção automática baseada no parâmetro `?plano=`.
   - Cadastro simplificado com provisionamento de slug, estabelecimento e admin tenant.

3. **Módulo de Upgrade e Controle de Capacidade no Painel Administrativo:**
   - Página `/admin/upgrade` dedicada à visualização da assinatura ativa, capacidade de profissionais e solicitação direta de upgrade via canal oficial do WhatsApp (`(11) 96638-1915`).
   - Validação de limite de profissionais ativos baseada na cota de cada plano:
     * **Inicial:** 1 profissional ativo (R$ 49,90/mês | R$ 39,90 anual).
     * **Intermediário:** Até 5 profissionais ativos (R$ 99,90/mês | R$ 79,90 anual).
     * **Avançado:** Até 10 profissionais ativos (R$ 169,90/mês | R$ 139,90 anual).
   - Inclusão de atalhos e badges no menu lateral, topbar, listagem de profissionais e tela de dados do estabelecimento.

4. **Regra de Produto Homologada:**
   - 100% dos recursos da plataforma estão disponíveis em todos os planos (clientes, serviços e agendamentos ilimitados, página pública, dashboard, relatórios e suporte).
   - Diferenciação de planos estritamente pela quantidade de profissionais ativos cadastrados.

---

## 2. Linha do Tempo da Operação de Deploy

| Horário (BRT) | Horário (UTC) | Etapa / Operação | Detalhes / Status |
|:---:|:---:|:---|:---|
| **08:12:58** | 11:12:58 | Backup de salvaguarda do Site Institucional | `/home2/alllogiconline/backups/public_html-pre-deploy-20261015-081258.tar.gz` |
| **08:13:10** | 11:13:10 | Deploy do Site Institucional (Astro SSG) | Upload e extração de `alllogic-site-agillex-c69bc9b.tar.gz` em `/public_html` |
| **08:14:12** | 11:14:12 | Verificação HTTP/2 do Site Institucional | `HTTP/2 200 OK` confirmado em `https://alllogiconline.com.br/agillex-agenda/` |
| **08:15:34** | 11:15:34 | Baseline HTTP da aplicação Scheduler na VPS | `HTTP/2 200 OK` em `/` e `/admin/login` |
| **08:16:12** | 11:16:12 | Execução do Backup de salvaguarda na VPS | Dump PostgreSQL, `compose.yaml`, `.env`, Git Bundle e tag de rollback |
| **08:16:40** | 11:16:40 | Validação dos checksums do Backup na VPS | Todos os 4 artefatos retornaram `OK` (`sha256sum -c SHA256SUMS`) |
| **08:16:50** | 11:16:50 | `git pull --ff-only origin main` na VPS | Atualização para `46699d4` sem divergências |
| **08:16:59** | 11:16:59 | `docker compose build scheduler` na VPS | Imagem Docker reconstruída com sucesso |
| **08:17:04** | 11:17:04 | `docker compose up -d scheduler` na VPS | Container `alllogic-scheduler` recriado atomicamente |
| **08:17:12** | 11:17:12 | Validação do esquema no PostgreSQL | Coluna `plano TEXT NOT NULL DEFAULT 'intermediario'` ativa em `estabelecimento` |
| **08:17:50** | 11:17:50 | Testes HTTP/2 pós-deploy em produção | Validação de `/agillex`, `?plano=inicial`, `?plano=avancado` e `/admin/login` |
| **08:18:00** | 11:18:00 | Auditoria de integridade do banco | 100% dos registros preservados (7 serviços, 2 profissionais, 22 agendamentos, 15 clientes) |

---

## 3. Artefatos de Salvaguarda Criados

### 3.1. Scheduler (VPS KingHost `177.153.203.158`)
- **Diretório:** `/opt/alllogic/backups/scheduler/pre-46699d4-20261015T111612Z/`
- **Artefatos:**
  1. `postgres-alllogic_scheduler.dump` (Dump PostgreSQL formato CUSTOM gzip, 34 KB, 86 entradas TOC validadas).
  2. `compose.yaml` (Configuração do serviço Docker).
  3. `.env` (Configurações de ambiente, modo estrito `chmod 600`).
  4. `source-before.bundle` (Bundle binário completo do Git com histórico do commit anterior).
  5. `SHA256SUMS` (Manifesto assinado de integridade).
- **Tag Docker de Rollback:** `scheduler-scheduler:rollback-cce067d-20261015T111612Z`.

### 3.2. Site Institucional (cPanel `177.104.163.165:21008`)
- **Arquivo:** `/home2/alllogiconline/backups/public_html-pre-deploy-20261015-081258.tar.gz`
- **Checksum SHA-256:** `f7cd5efcaaa40092a84572a1c8595718c704b4c885ebddb6f32a8a91f370f6c3`

---

## 4. Validação Pós-Deploy em Produção

1. **Página de Vendas no Site Institucional:**
   - `https://alllogiconline.com.br/agillex-agenda/` respondendo `HTTP/2 200 OK`.
   - Alternador mensal/anual funcional em JavaScript puro (20% OFF).
   - Tabela de preços clara com 1, até 5 e até 10 profissionais.
   - Links diretos com query param para a página de trial.

2. **Página de Trial no Scheduler:**
   - `https://agenda.alllogiconline.com.br/agillex` respondendo `HTTP/2 200 OK`.
   - Seletor de planos interativo e responsivo.
   - Parâmetro `?plano=inicial` pré-seleciona o card do plano Inicial.
   - Parâmetro `?plano=avancado` pré-seleciona o card do plano Avançado.
   - Botão "Voltar ao agendamento" removido conforme solicitação.
   - Paleta de cores, tipografia, bordas e sombras rigorosamente integradas aos tokens AllLogic.

3. **Painel Administrativo:**
   - `https://agenda.alllogiconline.com.br/admin/login` respondendo `HTTP/2 200 OK`.
   - Rota `/admin/upgrade` ativa com cartões de capacidade, barra de uso de profissionais e botão direto para o WhatsApp de suporte.
   - Validação de cotas ativa na criação/ativação de profissionais.

4. **Logs da Aplicação (Gunicorn):**
   - Zero erros, zero exceções, zero alertas.

---

## 5. Parecer Final

A implantação em produção de ambas as aplicações foi concluída com êxito absoluto, sem indisponibilidade dos serviços, com backups íntegros gerados previamente e validação em tempo real das rotas e do banco de dados.

**Status:** **DEPLOY CONCLUÍDO COM SUCESSO**
