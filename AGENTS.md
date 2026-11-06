# AGENTS.md — AllLogic Scheduler (Agillex Agenda)

## Contexto do Projeto

Este documento orienta os Agentes de IA que atuam no repositório **AllLogic Scheduler (Agillex Agenda)**, subordinado às diretrizes gerais do `~/AllLogic/AGENTS.md` e aos fundamentos de `~/AllLogic/SGA/FOUNDATION.md`.

O **AllLogic Scheduler** é o sistema de agendamento online da **Família Agillex**, projetado para pequenos negócios e prestadores de serviços, com integração a calendário, gestão de equipe, serviços, estabelecimentos, lembretes e fluxo de agendamento mobile-first.

---

## 1. Arquitetura e Tecnologias

- **Domínio de Produção:** `https://agenda.agillex.com.br/` (redirecionamento canônico de `https://agendamento.alllogiconline.com.br/`)
- **Plataforma Base:** Python 3.12 / Flask / Gunicorn
- **Frontend:** Jinja2 templates, Design System Agillex Premium (marfim `#F6F1E8`, navy `#14213D`, champanhe `#B89748`), CSS3 responsivo e Vanilla JS.
- **Banco de Dados:** PostgreSQL 16 (multi-tenant com isolamento lógico)
- **Hospedagem & Infraestrutura:** VPS Hetzner / EVEO, Docker Compose, Traefik v3 (SSL Let's Encrypt automático)
- **Acesso Remoto:** SSH (chave `~/.ssh/id_rsa`)
- **Diretórios Remotos:**
  - Stack Compose: `/opt/alllogic/stacks/scheduler/`
  - Aplicação: `/opt/alllogic/apps/alllogic-scheduler/`

---

## 2. Estrutura do Repositório Local

- `templates/` — Templates Jinja2 organizados por visão:
  - `base_admin.html` — Layout mestre da área administrativa com sidebar e topbar.
  - `admin_*.html` — Telas de gestão (dashboard, serviços, profissionais, configurações, reagendamento).
  - Telas públicas de cliente (agendamento, confirmação, cancelamento).
- `static/` — Ativos estáticos:
  - `css/style.css` — Estilização unificada do Design System Agillex Premium.
  - `js/` — Scripts de interatividade client-side.
- `models.py` / `routes.py` / `app.py` — Lógica de negócios, rotas Flask e persistência relacional.
- `tests/` — Suíte de testes funcionais, de regressão e de integração com Pytest.
- `docs/` — Relatórios de auditoria pré-deploy, especificações e histórico de homologações.

---

## 3. Procedimento Operacional de Deploy

1. Realizar alterações e validações de integridade no ambiente local ou de homologação (`scheduler_test_homologacao`).
2. Executar a suíte de testes automatizados com 100% de sucesso comprovado:
   ```bash
   pytest tests/ -v
   ```
3. **Portão Obrigatório de Aprovação:** Apresentar ao fundador um resumo estruturado com as mudanças efetuadas, arquivos alterados, diffs relevantes e evidências dos testes. Formular explicitamente:
   > *"Testes locais validados com sucesso. Autoriza o commit e a publicação em produção?"*
   Pausar a execução e aguardar a resposta do fundador. Fica terminantemente proibido executar `git commit`, `git push` ou comandos remotos sem autorização expressa.
4. **Execução Contínua Pós-Autorização:** Uma vez concedida a autorização pelo fundador, a execução prossegue de forma contínua e autônoma até a entrega completa das etapas aprovadas, sem pausas para confirmações intermediárias:
   - Criar commit semântico e enviar ao GitHub (`git push origin main`).
   - Conectar à VPS e executar backup da aplicação e das imagens anteriores.
   - Atualizar a aplicação na VPS via `git pull origin main`.
   - Executar recriação controlada do container (`docker compose up -d --force-recreate scheduler`).
   - Executar validações pós-deploy (verificação HTTP 200, entrega de assets e fluxo de agendamento).
