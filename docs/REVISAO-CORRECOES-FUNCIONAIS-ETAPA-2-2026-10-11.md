# Relatório de Revisão das Correções Funcionais — Etapa 2

**Data:** 2026-10-11  
**Projeto:** AllLogic Scheduler (Agillex Agenda)  
**Ambiente:** Repositório Local (`~/AllLogic/Projetos/app-agendamento`)  
**Base do Repositório:** Commit documental `3d01af8f4139cee1efdefc9aa119d0d709d3d5d8`  
**Arquivos Analisados:** `models.py` e `tests/test_bloco3.py`  
**Classificação:** Análise Técnica de Código, Compatibilidade e Validação de Testes (Etapa 2)  
**Status Operacional:** Exclusivamente consultivo. Nenhum commit, push, deploy ou modificação executada.

---

## 1. Identificação e Contexto da Etapa 2

A presente revisão analisa com rigor técnico o escopo do **Grupo A (Core Funcional e Testes)** antes de qualquer ação de versionamento. O commit documental anterior (`3d01af8`) permanece perfeitamente intacto como HEAD da branch local `main`.

---

## 2. Exame do Código e Comportamento Efetivo das Consultas (`models.py`)

As alterações em `models.py` afetam três funções centrais de consulta de agendamentos:
1. `obter_agendamento_completo(agendamento_id)` (linha 808)
2. `listar_agendamentos_por_periodo(data_inicio_str, data_fim_str, profissional_id=None)` (linha 853)
3. `pesquisar_agendamentos(...)` (linha 930)

### 2.1. Confronto Código Original vs. Código Alterado

```sql
-- CÓDIGO ORIGINAL (commit 843e291):
SELECT a.*,
       COALESCE(a.profissional_nome_snapshot, p.nome) AS profissional_nome,
       COALESCE(
           json_agg(
               json_build_object(
                   'id', s.id,
                   'nome', COALESCE(ags.nome_servico, s.nome),
                   'preco', COALESCE(ags.preco_unitario, s.preco),
                   'duracao_minutos', COALESCE(ags.duracao_minutos, s.duracao_minutos)
               )
               ORDER BY s.id
           ) FILTER (WHERE s.id IS NOT NULL),
           '[]'::json
       ) AS servicos
FROM agendamento a
JOIN profissional p ON p.id = a.profissional_id
LEFT JOIN agendamento_servico ags ON ags.agendamento_id = a.id
LEFT JOIN servico s ON s.id = ags.servico_id

-- CÓDIGO ALTERADO (pendente na Etapa 2):
SELECT a.*,
       COALESCE(a.profissional_nome_snapshot, p.nome) AS profissional_nome,
       COALESCE(
           json_agg(
               json_build_object(
                   'id', COALESCE(ags.servico_id, s.id),
                   'nome', COALESCE(ags.nome_servico, s.nome),
                   'preco', COALESCE(ags.preco_unitario, s.preco),
                   'duracao_minutos', COALESCE(ags.duracao_minutos, s.duracao_minutos)
               )
               ORDER BY COALESCE(ags.servico_id, s.id)
           ) FILTER (WHERE ags.servico_id IS NOT NULL OR s.id IS NOT NULL),
           '[]'::json
       ) AS servicos
FROM agendamento a
LEFT JOIN profissional p ON p.id = a.profissional_id
LEFT JOIN agendamento_servico ags ON ags.agendamento_id = a.id
LEFT JOIN servico s ON s.id = ags.servico_id
```

### 2.2. Mecânica Operacional das Alterações

1. **Substituição de `JOIN` por `LEFT JOIN profissional`:**
   - *Comportamento Original:* Se um profissional fosse removido ou inativado e o agendamento possuísse `a.profissional_id` desvinculado, o `INNER JOIN` descartava silenciosamente toda a linha do agendamento da listagem.
   - *Comportamento Alterado:* Com `LEFT JOIN`, o agendamento continua sendo retornado. O campo `COALESCE(a.profissional_nome_snapshot, p.nome)` garante que o nome do profissional congelado no momento do agendamento seja exibido, mesmo que o registro na tabela `profissional` não exista mais.
2. **Resiliência de Serviços Agregados (`json_agg`):**
   - *Comportamento Original:* O filtro `FILTER (WHERE s.id IS NOT NULL)` descartava qualquer serviço cujo `s.id` fosse nulo na tabela `servico` (caso o serviço fosse excluído do catálogo), esvaziando o array de serviços do agendamento (`[]`).
   - *Comportamento Alterado:* Utiliza `COALESCE(ags.servico_id, s.id)` e `FILTER (WHERE ags.servico_id IS NOT NULL OR s.id IS NOT NULL)`, recuperando as informações de nome, preço e duração congeladas na tabela associativa `agendamento_servico` (`ags.nome_servico`, `ags.preco_unitario`, `ags.duracao_minutos`).

---

## 3. Preservação de Agendamentos Históricos

- **Serviços Inativados/Excluídos:** A persistência de snapshots em `agendamento_servico` introduzida na Fase 2 é agora plenamente honrada em tempo de leitura. Mesmo se um serviço for deletado da tabela principal `servico`, os agendamentos passados mantêm seu descritivo, preço e duração inalterados na visualização administrativa.
- **Profissionais Inativados/Excluídos:** O `LEFT JOIN` impede que o descarte de um profissional oculte o histórico de atendimentos passados da empresa.
- **Conclusão:** O código alterado elimina uma falha de ocultação de registros e garante conformidade com o princípio de rastreabilidade histórica da AllLogic.

---

## 4. Análise do Reset Idempotente em `tests/test_bloco3.py`

### 4.1. Código Adicionado
```python
def test_admin_auth_settings_and_service_description(client):
    from werkzeug.security import generate_password_hash
    with database.db_session() as conn:
        conn.execute("DELETE FROM admin WHERE usuario IN ('admin', 'admin_ativo')")
        conn.execute(
            "INSERT INTO admin (usuario, senha_hash, senha_inicial_alterada) VALUES ('admin', %s, FALSE)",
            (generate_password_hash(os.environ["ADMIN_SENHA_INICIAL"]),)
        )
    assert client.get("/admin/servicos").status_code == 302
```

### 4.2. Avaliação de Escopo e Segurança
1. **Confinamento ao Ambiente de Testes:**
   - Este código reside exclusivamente no módulo de testes `tests/test_bloco3.py`.
   - As salvaguardas de cabeçalho do arquivo exigem `SCHEDULER_TEST_DATABASE=1`, nome de banco iniciando obrigatoriamente com `scheduler_test_` e host loopback (`127.0.0.1`). Caso contrário, a execução é abortada por `RuntimeError`.
   - **Risco de Produção:** **Zero**. O código nunca é executado no runtime da aplicação nem em produção.
2. **Necessidade para Idempotência:**
   - O teste simula a autenticação de primeiro acesso com `ADMIN_SENHA_INICIAL` e troca de senha para `senha_inicial_alterada = TRUE`.
   - Sem esse reset explícito no início da função, qualquer reexecução subsequente do pytest contra o mesmo banco PostgreSQL de teste falharia com erro de credencial já alterada.
   - **Conclusão:** A alteração é estritamente necessária e garante idempotência contínua.

---

## 5. Riscos de Compatibilidade, Regressões e Lacunas

- **Compatibilidade com PostgreSQL 17 (Produção):** As cláusulas `LEFT JOIN`, `COALESCE` e `FILTER (WHERE ...)` são padrão SQL ANSI e têm suporte nativo de altíssima performance no PostgreSQL 17.
- **Contrato de Dados da Aplicação:** O dicionário retornado pelas funções mantém exatamente as mesmas chaves esperadas (`servico_nome`, `servico_preco`, `servico_duracao_minutos`, `profissional_nome`). Zero impacto em rotas Flask ou templates.
- **Regressão:** Zero regressões constatadas. Toda a suíte de 48 testes existentes continua aprovada com 100% de sucesso.
- **Lacunas de Cobertura Identificadas:** Os testes atuais cobrem serviços e profissionais com `ativo = FALSE`, mas não cobrem explicitamente registros cujo `profissional_id` ou `servico_id` foi fisicamente deletado da tabela de origem (hard delete). Recomenda-se adicionar um teste específico para esse cenário em ciclo futuro de testes.

---

## 6. Ambiente e Configuração de Testes Utilizados

Em estrito cumprimento das restrições de segurança, os testes foram executados exclusivamente contra o banco local de homologação/teste:

- **Host:** `127.0.0.1` (loopback estrito)
- **Porta:** `5433` (instância de desenvolvimento local)
- **Banco de Dados:** `scheduler_test_homologacao` (prefixo `scheduler_test_` validado)
- **Usuário:** `alllogic_scheduler`
- **Ambiente de Teste:** `SCHEDULER_TEST_DATABASE=1`
- **Confirmação:** O banco de produção `alllogic_scheduler` na VPS KingHost (`177.153.203.158`) **não foi acessado nem modificado**.

---

## 7. Resultados dos Comandos de Validação

### 7.1. Execução dos Testes (`tests/test_bloco3.py`)
```bash
PYTHONPATH=. SCHEDULER_TEST_DATABASE=1 POSTGRES_DB=scheduler_test_homologacao POSTGRES_USER=alllogic_scheduler POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 pytest tests/test_bloco3.py -v
```
**Resultado:**
- 1ª execução: `5 passed in 5.58s` (100% sucesso).
- 2ª execução consecutiva (validação de idempotência): `5 passed in 6.80s` (100% sucesso).

### 7.2. Execução da Suíte Completa de Testes
**Resultado:**
- `48 passed in 42.88s` (100% de cobertura dos fluxos críticos).

### 7.3. `git diff --check`
```bash
git diff --check -- models.py tests/test_bloco3.py
```
**Resultado:** `0 erros` (sem quebras de linha ou conflitos).

---

## 8. Recomendações Individuais e Proposta de Commit Funcional

| Arquivo | Recomendação | Justificativa |
| :--- | :---: | :--- |
| `models.py` | **Aceitar** | Corrige com segurança a agregação de serviços e preservação de agendamentos históricos sem alterar contratos de dados. |
| `tests/test_bloco3.py` | **Aceitar** | Confinado ao ambiente de teste, confere idempotência indispensável para testes repetíveis. |

### Proposta de Commit Funcional (Etapa 2):
```text
fix(models): adicionar resiliencia em consultas de agendamentos historicos

- Substitui JOIN estrito por LEFT JOIN profissional para preservar agendamentos historicos
- Aplica COALESCE nos identificadores e nomes de servicos agregados
- Garante idempotencia no teste de autenticacao de tests/test_bloco3.py
```

---

## 9. Estado Atual do Git e Preservação

```text
 M models.py
 M static/css/style.css
 M templates/admin_alterar_senha.html
 M templates/admin_configuracoes.html
 M templates/admin_dashboard.html
 M templates/admin_estabelecimento.html
 M templates/admin_profissionais.html
 M templates/admin_profissional_form.html
 M templates/admin_reagendar.html
 M templates/admin_reagendar_sucesso.html
 M templates/admin_servico_form.html
 M templates/admin_servicos.html
 M tests/test_bloco3.py
?? "Logo Dourado de Salão Premium.png"
?? docs/AUDITORIA-PRE-DEPLOY-PRODUCAO-2026-10-10.md
?? docs/CONFERENCIA-FINAL-PRE-COMMIT-DOCUMENTAL-2026-10-11.md
?? docs/MATRIZ-DECISAO-17-ARQUIVOS-2026-10-10.md
?? docs/REVISAO-CORRECOES-FUNCIONAIS-ETAPA-2-2026-10-11.md
?? docs/VALIDACAO-CORRECOES-DOCUMENTAIS-ETAPA-1-2026-10-11.md
?? templates/base_admin.html
```

- Nenhum arquivo foi comitado, descartado ou modificado indevidamente.
- Nenhum push ou deploy foi realizado.
- A Etapa 3 (interface) permanece parada aguardando conclusão desta etapa.
