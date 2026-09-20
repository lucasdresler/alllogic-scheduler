# Auditoria Técnica — AllLogic Scheduler (V1)

**Data:** 19/09/2026
**Objetivo:** Verificar cada item do relatório de auditoria anterior contra o código atual e a documentação oficial do projeto (AGENTS.md, FOUNDATION.md, V1 Comercial, Plano de Finalização, REGRAS-AGENDAMENTOS.md, ARQUITETURA-BANCO.md, AMBIENTE-DESENVOLVIMENTO.md, INFRAESTRUTURA.md, roadmap).

---

## Classificação dos 17 Itens

| Item | Classificação | Resumo da Verificação |
|------|--------------|----------------------|
| **1. Serviços e profissionais sem CRUD no admin** | **A** | Não existe CRUD no painel admin. Apenas APIs públicas de listagem (`/api/services`, `/api/professionals`). Admin dashboard apenas lista agendamentos. |
| **2. Configurações não persistidas no banco** | **A** | `config.py` define `HORARIO_ABERTURA`, `HORARIO_FECHAMENTO`, `INTERVALO_SLOT_MINUTOS`, `DIAS_FUNCIONAMENTO`, `DIAS_ANTECEDENCIA_AGENDAMENTO` hardcoded. Documentação (V1 Comercial §11, Plano §2.1) exige persistência no PostgreSQL. |
| **3. Limite de antecedência validado apenas no frontend** | **A** | Frontend (`agendamento.js:4,140`) usa `DIAS_ANTECEDENCIA` para gerar dias. Backend `models.data_permitida()` (linha 50-58) **não valida** o limite de 14 dias — só verifica se não é passado e se dia da semana permitido. |
| **4. Ausência de alteração de senha** | **A** | Não existe rota, template ou lógica para mudança de senha. Documentação (V1 Comercial §1.2-1.6, Plano §4) exige: validar senha atual, nova senha, confirmação, hash, invalidação imediata. |
| **5. Ausência de reagendamento** | **A** | Só existe cancelamento (`admin_cancelar_agendamento` em `app.py:186-190` e `models.cancelar_agendamento`). Documentação (V1 Comercial §5, REGRAS §70-75, Plano §12) exige fluxo completo de reagendamento preservando histórico. |
| **6. Ausência de entidade Cliente e histórico de clientes** | **A** | Cliente armazenado direto no agendamento (`cliente_nome`, `cliente_telefone`). Não há tabela `cliente` nem consulta de histórico por cliente. Documentação (V1 Comercial §8, AGENTS.md §11, Plano §13) prevê entidade própria. |
| **7. Cancelamento sem ação correspondente na interface** | **A** | Rota backend existe, mas **não há botão de cancelar** no `admin_dashboard.html` (tabela mostra status mas sem ação). |
| **8. Ausência de testes automatizados** | **A** | Nenhum arquivo de teste no projeto (apenas em `.venv/`). Plano §16 exige testes para serviços, profissionais, disponibilidade, agendamento, cancelamento, reagendamento, antecedência, configurações, auth, alteração de senha. |
| **9. Ausência de procedimento de backup/recuperação** | **A** | Não implementado nem documentado. Plano §17 e V1 Comercial §16 exigem: backup, armazenamento, restauração, validação, recuperação. |
| **10. Status "realizado" não documentado nas regras** | **A** | `REGRAS-AGENDAMENTOS.md` §13-16 define apenas `agendado` e `cancelado`. Código usa `realizado` em `database.py:101-109` (atualização automática) e `app.py:225` (receita do período). Regra não documentada. |
| **11. Senha padrão do admin fixa no código** | **A** | `database.py:148` faz seed com `generate_password_hash("barbeariatop123")`. Credencial hardcoded no código versionado. Viola AGENTS.md §19 e V1 Comercial §143. |
| **12. Possível condição de corrida na criação de agendamentos** | **B** | `criar_agendamento` revalida disponibilidade antes do INSERT, mas **não usa lock** (SELECT FOR UPDATE ou advisory lock) na transação. Dois requests simultâneos podem passar na validação e criar conflito. Mitigação parcial: constraint unique em `agendamento_servico` não cobre horário. Requer decisão: aceitar risco baixo ou implementar lock. |
| **13. Ausência de CSRF e proteção contra tentativas repetidas de login** | **A** | Não há CSRF tokens nos forms (login, cancelamento). Não há rate limiting / brute-force protection no `/admin/login`. V1 Comercial §140 exige validação de entradas e proteção de rotas admin. |
| **14. SECRET_KEY com valor padrão inseguro** | **A** | `config.py:13`: `SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")`. Fallback inseguro versionado. `.env.example` tem placeholder correto, mas default no código viola AGENTS.md §19. |
| **15. DNS.md possivelmente desatualizado** | **D** | Documento datado 14/09/2026 (hoje). Subdomínio `agenda.alllogiconline.com.br` ainda sem registro A — condiz com estado atual. Não desatualizado. |
| **16. Arquivos legados `barbearia-top.service` e `nginx_barbearia_top.conf`** | **A** | Existem na raiz do projeto. Referenciam `/opt/barbearia_top`, usuário `www-data`, porta 8000, nome antigo "Barbearia Top". Projeto agora é **AllLogic Scheduler** com deploy via Docker/Traefik (INFRAESTRUTURA.md). Devem ser removidos ou movidos para docs/legacy. |
| **17. Textos singulares na interface após múltiplos serviços** | **C** | Frontend já atualizado: `index.html:19` "Escolha um ou mais serviços", `agendamento.js` suporta array `servicos`, resumo mostra múltiplos. `sucesso.html:16` usa `agendamento.servico_nome` (join). Sem textos singulares residuais no fluxo público. |

**Legenda:**
- **A** = Confirmado e deve ser corrigido
- **B** = Confirmado, mas depende de decisão/documentação
- **C** = Já corrigido
- **D** = Não confirmado

---

## Correções Confirmadas (A) — Ordem Recomendada pela Documentação

Seguindo a sequência oficial (AGENTS.md §9, Plano §24):

### Fase 1 — Banco e Configurações (Plano §2-3)
1. **Item 2** — Criar tabela `configuracao` no PostgreSQL e migrar `config.py` para BD (nome, telefone, endereço, nome_público, antecedência_máxima, horário_abertura, horário_fechamento, intervalo_slot, dias_funcionamento).
2. **Item 14** — Remover fallback inseguro de `SECRET_KEY` em `config.py`; exigir variável de ambiente obrigatória.
3. **Item 11** — Remover seed de senha hardcoded; exigir criação de admin via CLI/migração segura na primeira execução.

### Fase 2 — Backend e API (Plano §4-8)
4. **Item 3** — Implementar validação de antecedência máxima no backend (`models.data_permitida` ou nova função) lendo do BD.
5. **Item 1** — Implementar CRUD de Serviços no admin (listar, criar, editar, remover/desativar).
6. **Item 1** — Implementar CRUD de Profissionais no admin (listar, criar, editar, ativar/desativar).
7. **Item 4** — Implementar rota + template + lógica de **alteração de senha** (validar atual, confirmar nova, hash, invalidação).
8. **Item 13** — Adicionar CSRF protection (Flask-WTF ou similar) nos forms admin; implementar rate limiting no login (ex: Flask-Limiter).
9. **Item 12** — Adicionar lock em `criar_agendamento` (advisory lock por profissional+data ou `SELECT FOR UPDATE` em agendamentos do profissional/hora).

### Fase 3 — Administração (Plano §9-14)
10. **Item 7** — Adicionar botão/ação de **cancelar** na interface do admin dashboard (tabela de agendamentos).
11. **Item 5** — Implementar **reagendamento** completo (fluxo: reagendar → nova data → horários → confirmar; preservar histórico; validar disponibilidade e antecedência).
12. **Item 6** — Criar entidade `Cliente` (tabela + modelo) e migrar dados existentes; implementar consulta de histórico por cliente.
13. **Item 10** — Documentar status `realizado` em `REGRAS-AGENDAMENTOS.md` (regras de negócio, receita, disponibilidade, histórico).

### Fase 4 — Qualidade e Operação (Plano §15-19)
14. **Item 8** — Criar suite de testes automatizados (pytest): services, profissionais, disponibilidade, agendamento, cancelamento, reagendamento, antecedência, configurações, auth, alteração de senha.
15. **Item 9** — Documentar e implementar procedimento de **backup/restauração** PostgreSQL (scripts + validação de restore).
16. **Item 16** — Remover arquivos legados `barbearia-top.service` e `nginx_barbearia_top.conf` da raiz do projeto.

---

## Itens Classificados como B (Dependem de Decisão)

| Item | Decisão Necessária |
|------|-------------------|
| **12. Condição de corrida** | Aceitar risco (baixa concorrência esperada na V1) vs implementar advisory lock / SELECT FOR UPDATE. Recomendo: implementar lock simples por profissional+data na transação de criação. |

---

## Itens Já Corrigidos (C) ou Não Confirmados (D)

| Item | Status | Observação |
|------|--------|------------|
| **15. DNS.md** | D — Não confirmado | Documento atualizado (14/09/2026), reflete estado real. |
| **17. Textos singulares** | C — Já corrigido | Interface pública já adaptada para múltiplos serviços. |

---

## Próximos Passos

Iniciar pela **Fase 1** (banco de configurações, SECRET_KEY, seed de admin) conforme a sequência oficial da V1, mediante autorização.