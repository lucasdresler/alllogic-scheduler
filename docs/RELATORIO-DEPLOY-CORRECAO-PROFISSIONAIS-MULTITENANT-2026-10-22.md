# Relatório de Deploy — Correção da Consulta de Profissionais Multi-tenant

**Data:** 22/10/2026 21:13 (BRT) / 23/10/2026 00:13 (UTC)  
**Projeto:** AllLogic Scheduler (Agillex Agenda) — `~/AllLogic/Projetos/app-agendamento`  
**Host de Produção:** Oracle Cloud Infrastructure (`136.248.113.145`)  
**Commit Publicado:** `16c89c9` (`origin/main`)  
**Status da Operação:** **DEPLOY CONCLUÍDO COM SUCESSO — TESTES DE FUMAÇA APROVADOS EM TODAS AS INSTÂNCIAS**

---

## 1. Contexto e Diagnóstico

Nas 3 instâncias de demonstração criadas para o Agillex Agenda (`/petshop`, `/clinica-odonto`, `/barbearia`), a Etapa 2 de 5 do agendamento ("Escolha o profissional") exibia a mensagem:
> *"Erro ao carregar profissionais. Tente novamente."*

### Causa Raiz
Na função `listar_profissionais_para_servicos` em `models.py`:
- Na cláusula SQL, `{cond_estab}` (`AND p.estabelecimento_id = %s`) precedia a cláusula `AND s.id = ANY(%s)`.
- No código Python anterior, a lista de parâmetros era preenchida via `params.insert(1, estabelecimento_id)`.
- Com isso, a cláusula `p.estabelecimento_id` recebia a lista `servico_ids` e a cláusula `s.id = ANY(%s)` recebia o valor escalar inteiro `estabelecimento_id` (ex: 3, 4, 5).
- O PostgreSQL gerava o erro `ERROR: op ANY/ALL (array) requires array on right side`, retornando HTTP 500 no endpoint `/api/professionals`.

---

## 2. Correções Implementadas

1. **`models.py`:**
   - Reestruturada a montagem de `params` para garantir que `estabelecimento_id` seja posicionado no índice 0 quando `estabelecimento_id != 1`:
     `params = [estabelecimento_id, servico_ids, len(servico_ids)]`.
2. **`tests/test_profissionais_api.py`:**
   - Criada suíte automatizada dedicada validando `models.listar_profissionais_para_servicos` e a resposta JSON do endpoint `/api/professionals` em contexto multi-tenant.
3. **`tests/test_multi_tenant.py`:**
   - Ajustadas asserções de URL pública no dashboard para compatibilidade com URLs curtas `/{slug}`.

---

## 3. Publicação em Produção

1. **Commit e Push:**
   - `16c89c9`: `fix(api): corrigir ordenação de parâmetros SQL em listar_profissionais_para_servicos para multi-tenancy`.
2. **Sincronização na VPS Oracle Cloud:**
   - `git pull origin main` em `/opt/alllogic/stacks/scheduler`.
3. **Rebuild e Reinício:**
   - `docker compose build scheduler`
   - `docker compose up -d scheduler` (`Container alllogic-scheduler Recreated / Started`).

---

## 4. Validação em Produção (Testes de Fumaça)

| Instância / Endpoint | Código HTTP | Profissionais Retornados | Status |
| :--- | :---: | :--- | :---: |
| `https://agenda.alllogiconline.com.br/petshop`<br>`/api/professionals?servico_id=25&estabelecimento_id=3` | **200 OK** | Bruno Santos, Dra. Camila Rocha | **Aprovado** |
| `https://agenda.alllogiconline.com.br/clinica-odonto`<br>`/api/professionals?servico_id=30&estabelecimento_id=4` | **200 OK** | Dr. Marcos Vinícius, Dra. Beatriz Fontana | **Aprovado** |
| `https://agenda.alllogiconline.com.br/barbearia`<br>`/api/professionals?servico_id=35&estabelecimento_id=5` | **200 OK** | Felipe Lima, Gustavo "Dom" Barbeiro, Luis | **Aprovado** |
| `https://agenda.alllogiconline.com.br/` (Padrão) | **200 OK** | Profissionais padrão da instância 1 | **Aprovado** |
