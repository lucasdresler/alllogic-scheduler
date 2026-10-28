# Relatório de Deploy — Painel de Personalização de Cores do Estabelecimento

**Data:** 27/10/2026 22:45 (BRT) / 28/10/2026 01:45 (UTC)  
**Projeto:** AllLogic Scheduler (Agillex Agenda) — `~/AllLogic/Projetos/app-agendamento`  
**Host de Produção:** Oracle Cloud Infrastructure (`136.248.113.145`)  
**Commit Publicado:** `d1b320e` (`origin/main`)  
**Status da Operação:** **DEPLOY CONCLUÍDO COM SUCESSO — TESTES DE FUMAÇA APROVADOS EM PRODUÇÃO**

---

## 1. Objetivo da Alteração

Disponibilizar ao administrador do estabelecimento, na página `/admin/estabelecimento`, a capacidade de personalizar a paleta de cores da sua marca com aplicação automática em tempo real tanto no **painel administrativo** quanto na **vitrine pública de agendamento**.

---

## 2. Funcionalidades Entregues

1. **Presets com 1 Clique:**
   - *Agillex Clássico* (`#14213D`, `#E5C78B`, `#F6F1E8`)
   - *Elegance Gold* (`#0F172A`, `#D4AF37`, `#F8FAFC`)
   - *Esmeralda & Saúde* (`#064E3B`, `#10B981`, `#F0FDF4`)
   - *Royal Blue* (`#1E3A8A`, `#38BDF8`, `#F0F9FF`)
   - *Roxo Imperial* (`#4C1D95`, `#F59E0B`, `#FAF5FF`)

2. **Ajuste Fino Manual:**
   - Seleção interativa via color picker nativo e entrada manual hexadecimal (`#RRGGBB`).
   - Campos: Cor Primária (Principal), Cor Secundária (Destaque) e Cor de Fundo da Aplicação.

3. **Demonstração em Tempo Real (Live Preview Duplo):**
   - Miniatura do painel administrativo (sidebar, avatar, menu ativo e botão de ação).
   - Miniatura da página de agendamento (banner hero, card de serviço com preço e botão de agendamento).

4. **Botão Restaurar Padrão:**
   - Permite retornar às cores oficiais originais a qualquer momento.

---

## 3. Publicação em Produção

1. **Commit e Push:**
   - Commit `d1b320e`: `feat(admin): disponibilizar painel de personalizacao de cores do estabelecimento`.
2. **Sincronização na VPS Oracle Cloud:**
   - `git pull origin main` em `/opt/alllogic/stacks/scheduler`.
3. **Rebuild e Reinício:**
   - `docker compose build scheduler`
   - `docker compose up -d scheduler` (`Container alllogic-scheduler Recreated / Started`).
4. **Migração do Banco:**
   - Execução automática de `init_db()` garantindo a existência das colunas `cor_primaria`, `cor_secundaria` e `cor_fundo` na tabela `estabelecimento`.

---

## 4. Validação em Produção (Smoke Tests)

| Endpoint Testado | Código HTTP | Status |
| :--- | :---: | :--- |
| `https://agenda.alllogiconline.com.br/` (Home / Vitrine Padrão) | **200 OK** | Aprovado |
| `https://agenda.alllogiconline.com.br/admin/login` | **200 OK** | Aprovado |
| `https://agenda.alllogiconline.com.br/barbearia` (Demonstração) | **200 OK** | Aprovado |
| `https://agenda.alllogiconline.com.br/api/services` | **200 OK** | Aprovado |
| Consulta SQL das colunas na VPS | **OK** | Colunas criadas e populadas com sucesso |
