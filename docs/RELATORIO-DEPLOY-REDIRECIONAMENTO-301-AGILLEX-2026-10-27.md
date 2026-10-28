# Relatório de Deploy — Redirecionamento 301 das Rotas Legadas /agillex e /experimente

**Data:** 27/10/2026 22:07 (BRT) / 28/10/2026 01:07 (UTC)  
**Projeto:** AllLogic Scheduler (Agillex Agenda) — `~/AllLogic/Projetos/app-agendamento`  
**Host de Produção:** Oracle Cloud Infrastructure (`136.248.113.145`)  
**Commit Publicado:** `061c94b` (`origin/main`)  
**Status da Operação:** **DEPLOY CONCLUÍDO COM SUCESSO — TESTES DE FUMAÇA APROVADOS EM PRODUÇÃO**

---

## 1. Objetivo da Alteração

Desativar o formulário antigo de auto-cadastro em `/agillex` e redirecionar permanentemente (HTTP 301) o tráfego de quem acessar `https://agenda.alllogiconline.com.br/agillex` ou `/experimente` diretamente para a página institucional oficial do produto:
`https://alllogiconline.com.br/agillex-agenda/`

---

## 2. Modificações no Código

- **`app.py`:**
  - Substituição da rota do antigo formulário `/agillex` e de `/experimente` por redirecionamento HTTP 301 para `https://alllogiconline.com.br/agillex-agenda/`.
  - Inclusão do decorador `@csrf.exempt` para garantir que submissões legadas em POST (ou bots) sejam imediatamente redirecionadas via 301 em vez de bloqueadas com 400 Bad Request por ausência de token CSRF.

---

## 3. Publicação em Produção

1. **Commit e Push:**
   - Commit `061c94b`: `feat(routes): redirecionar rotas legadas /agillex e /experimente para /agillex-agenda/ via HTTP 301`.
   - Enviado para `origin/main`.
2. **Sincronização na VPS Oracle Cloud:**
   - `git pull origin main` em `/opt/alllogic/stacks/scheduler`.
3. **Rebuild e Reinício do Container:**
   - `docker compose build scheduler`
   - `docker compose up -d scheduler` (`Container alllogic-scheduler Recreated / Started`).

---

## 4. Validação em Produção (Smoke Tests)

| Endpoint Testado | Código HTTP | Destino (Location) / Status |
| :--- | :---: | :--- |
| `https://agenda.alllogiconline.com.br/agillex` | **301** | `https://alllogiconline.com.br/agillex-agenda/` (Aprovado) |
| `https://agenda.alllogiconline.com.br/experimente` | **301** | `https://alllogiconline.com.br/agillex-agenda/` (Aprovado) |
| Follow redirect de `/agillex` | **200 OK** | Página de destino responde com sucesso |
| `https://agenda.alllogiconline.com.br/` (Home) | **200 OK** | Operacional |
| `https://agenda.alllogiconline.com.br/barbearia` (Demo) | **200 OK** | Operacional |
| `https://agenda.alllogiconline.com.br/admin/login` | **200 OK** | Operacional |
| `https://agenda.alllogiconline.com.br/api/services` | **200 OK** | Operacional |
