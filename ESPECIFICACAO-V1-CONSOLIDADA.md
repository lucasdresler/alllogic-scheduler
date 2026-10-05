# ESPECIFICAÇÃO V1 CONSOLIDADA — AllLogic Scheduler

---

## 1. VISÃO GERAL

**Projeto:** AllLogic Scheduler  
**Versão:** V1 Comercial  
**Objetivo:** Solução de agendamento online para pequenos negócios/empresas de bairro  
**Critério de saída:** Pequeno negócio opera sem intervenção técnica:
- cadastrar serviços;
- alterar serviços (nome, descrição, preço, duração);
- alterar preços de serviços;
- alterar duração de serviços;
- ativar/desativar serviços;
- cadastrar profissionais;
- configurar disponibilidade;
- receber agendamentos online;
- administrar agenda;
- consultar histórico de clientes;
- consultar histórico de atendimentos;
- cancelar agendamentos;
- reagendar atendimentos sem destruir o histórico.

---

## 2. MÓDULOS E STATUS ATUAL

### 2.1 Banco de Dados e Modelos

| Item | Situação Atual | O que Existe | O que Falta |
|------|----------------|--------------|-------------|
| Tabela `configuracao` | ✅ Implementada | 9 configurações persistidas no PostgreSQL (nome, telefone, endereço, nome_público, antecedência_máxima=14, horário_abertura, horário_fechamento, intervalo_slot, dias_funcionamento) | CRUD administrativo para editar |
| Tabela `servico` | ✅ Implementada | id, nome, preco, duracao_minutos | Coluna `ativo` (boolean), CRUD admin |
| Tabela `profissional` | ✅ Implementada | id, nome, ativo | Coluna `servicos_ids` (relação N:M), CRUD admin |
| Tabela `agendamento` | ✅ Implementada | id, cliente_nome, cliente_telefone, servico_id (legado), profissional_id, data, hora, status, criado_em | Coluna `cliente_id` (FK), remover `servico_id` legado |
| Tabela `agendamento_servico` | ✅ Implementada | N:M agendamento-serviço | — |
| Tabela `admin` | ✅ Implementada | id, usuario, senha_hash, senha_inicial_alterada | — |
| **Tabela `cliente`** | ❌ Não existe | — | **Criar tabela completa** (id, nome, telefone, email, observacoes, criado_em) |
| **Tabela `profissional_servico`** | ❌ Não existe | — | **Criar tabela N:M** profissional-serviço |
| **Tabela `estabelecimento`** | ❌ Não existe | Configurações espalhadas em `configuracao` | **Consolidar em tabela única** (identificação, contato, endereço, identidade_visual, funcionamento, agendamento, conta) |

**Alterações de banco necessárias:**
1. Criar tabela `cliente` com migração de dados existentes (agrupar agendamentos por nome+telefone)
2. Criar tabela `profissional_servico` (N:M)
3. Adicionar `cliente_id` em `agendamento` (FK, nullable na migração, NOT NULL depois)
4. Adicionar coluna `ativo` em `servico` (default TRUE)
5. Remover coluna legada `servico_id` de `agendamento` após migração
6. Criar tabela `estabelecimento` consolidando configurações dispersas
7. Índices: `agendamento(cliente_id)`, `agendamento(profissional_id, data)`, `agendamento(status)`

**Dependências:** Cliente → Agendamento; Profissional_Servico → Disponibilidade; Estabelecimento → Configurações globais  
**Riscos:** Migração de dados existentes sem perder histórico; duplicação de clientes (mesmo nome/telefone)  
**Testes:** Migração em banco com dados; validação de integridade referencial; rollback

---

### 2.2 Backend e API

| Funcionalidade | Situação | O que Existe | O que Falta |
|----------------|----------|--------------|-------------|
| Listar serviços | ✅ | `GET /api/services` | Filtro por ativo |
| Listar profissionais | ✅ | `GET /api/professionals` | Filtro por ativo + serviços |
| Disponibilidade | ✅ | `GET /api/availability` | Considerar profissional-serviço |
| Criar agendamento | ✅ | `POST /api/appointments` | Validar cliente existente/criar; lock concorrência |
| Cancelar agendamento | ✅ | `models.cancelar_agendamento` | Rota admin + registro de origem |
| **Reagendar** | ❌ | — | **Implementar fluxo completo** |
| **CRUD Serviços** | ❌ | — | **Criar, editar, ativar/desativar, listar admin** |
| **CRUD Profissionais** | ❌ | — | **Criar, editar, ativar/desativar, definir serviços** |
| **CRUD Cliente** | ❌ | — | **Criar, listar, histórico, buscar** |
| **CRUD Configurações** | ❌ | Funções em `database.py` | **Rotas admin + validação** |
| **Alterar senha admin** | ✅ | `POST /admin/alterar-senha` | — |
| **Login admin** | ✅ | `POST /admin/login` | Rate limiting, CSRF |

**Alterações de banco:** Ver 2.1  
**Dependências:** Modelos (2.1) → API  
**Riscos:** Concorrência na criação (race condition); validação de antecedência apenas no frontend hoje  
**Testes:** Disponibilidade com múltiplos serviços; criação simultânea; validação de regras de negócio

---

### 2.3 Administração (Painel Admin)

| Funcionalidade | Situação | O que Existe | O que Falta |
|----------------|----------|--------------|-------------|
| Login / Logout | ✅ | `admin_login`, `admin_logout`, sessão Flask | Rate limiting, CSRF |
| Alterar senha (1º acesso) | ✅ | Fluxo obrigatório, validação, hash | — |
| Dashboard (hoje/semana/mês) | ✅ | `admin_dashboard` com indicadores | Indicadores por status (realizado, não compareceu) |
| **Serviços (CRUD)** | ❌ | Apenas listagem pública | **Tela completa: listar, criar, editar, ativar/desativar** |
| **Profissionais (CRUD)** | ❌ | Apenas listagem pública | **Tela completa: listar, criar, editar, ativar/desativar, vincular serviços** |
| **Clientes (CRUD + Histórico)** | ❌ | — | **Tela: listar, buscar, ver histórico de agendamentos** |
| **Configurações Estabelecimento** | ❌ | — | **Tela única: identificação, contato, endereço, logo, funcionamento, agendamento (antecedência), conta (senha)** |
| **Cancelar agendamento** | Parcial | Backend existe | **Botão na tabela do dashboard + confirmação + registro de origem** |
| **Reagendar** | ❌ | — | **Fluxo: selecionar → nova data/horário → confirmar → preservar histórico** |
| **Logo do estabelecimento** | ❌ | — | **Upload/remoção + exibição na área pública** |

**Dependências:** Backend/API (2.2) → Admin  
**Riscos:** Interface mobile-first; validações duplicadas frontend/backend  
**Testes:** Fluxos completos CRUD; permissões; validações; mobile

---

### 2.4 Área Pública (Agendamento)

| Etapa | Situação | O que Existe | O que Falta |
|-------|----------|--------------|-------------|
| 1. Serviços (múltiplos) | ✅ | Seleção múltipla, preço/duração somados | Filtro apenas ativos |
| 2. Profissional | ✅ | Seleção única | Filtrar por serviços selecionados (via profissional_servico) |
| 3. Data | ✅ | Grid respeita dias_funcionamento, antecedência | Validação backend já existe |
| 4. Horário | ✅ | Slots contínuos pela duração total | Considerar profissional-serviço |
| 5. Dados cliente | ✅ | Nome + telefone | **Buscar cliente existente por telefone; se novo, criar** |
| 6. Confirmação | ✅ | Resumo completo | **Gerar token/link de acesso à reserva** |
| Sucesso | ✅ | `sucesso.html` | Exibir token/link de gerenciamento |

**Mecanismo de acesso do cliente à própria reserva (NOVO):**
- Ao confirmar agendamento, gerar **token único (UUID)** armazenado em `agendamento.token_acesso`
- Enviar/link: `/reserva/<token>` (rota pública, sem login)
- Página permite: visualizar detalhes + **cancelar própria reserva**
- Token invalida após cancelamento ou reagendamento (novo token)
- Não expõe dados de outros clientes (token é imprevisível e pontual)

**Dependências:** Cliente (2.1), Disponibilidade (2.2), Token (novo campo)  
**Riscos:** Token vazado = acesso à reserva; rate limiting na consulta  
**Testes:** Fluxo completo; cancelamento pelo token; tentativa de acesso a token inválido

---

### 2.5 Dashboard e Indicadores

| Indicador | Regras de Cálculo (Status) |
|-----------|----------------------------|
| **Receita Prevista** | Soma de `servico_preco` onde `status = 'agendado'` |
| **Receita do Período** | Soma onde `status IN ('agendado', 'realizado')` — **NÃO inclui cancelado, não compareceu** |
| **Quantidade Realizados** | Count onde `status = 'realizado'` |
| **Quantidade Cancelados** | Count onde `status = 'cancelado'` |
| **Quantidade Não Compareceram** | Count onde `status = 'nao_compareceu'` |
| **Total Agendamentos** | Count todos (exceto talvez cancelados? Definir) |

**O que falta:** Atualizar `admin_dashboard` para calcular corretamente com 4 status; exibir breakdown por status

---

### 2.6 Status dos Agendamentos (DECISÃO DEFINITIVA)

**Estados operacionais (4):**
1. `agendado` — Ativo, bloqueia horário, entra em receita prevista
2. `realizado` — Atendimento ocorreu, definido por admin, histórico, NÃO bloqueia horário, entra em receita do período
3. `nao_compareceu` — Cliente não veio, definido por admin, histórico, NÃO bloqueia horário, NÃO entra em receita
4. `cancelado` — Cancelado por cliente ou admin, libera horário, histórico, NÃO entra em receita prevista

**Transições permitidas:**

| De → Para | Permitida? | Quem | Regra |
|-----------|------------|------|-------|
| agendado → realizado | ✅ | Admin | **Somente após a data/hora do agendamento ter passado** |
| agendado → nao_compareceu | ✅ | Admin | Após data/hora passada |
| agendado → cancelado | ✅ | Cliente (token) / Admin | A qualquer momento |
| realizado → agendado | ✅ | Admin | Correção (reabrir) |
| realizado → cancelado | ❌ | — | Não permitido (já ocorreu) |
| nao_compareceu → agendado | ✅ | Admin | Correção (reabrir) |
| nao_compareceu → cancelado | ❌ | — | Não faz sentido |
| cancelado → agendado | ✅ | Admin | Reativar (reativar reserva) |
| cancelado → realizado | ❌ | — | Não permitido |

**Registro de origem:** Coluna `status_origem` em `agendamento` (`cliente`, `admin`, `sistema`)  
**Histórico de status:** Tabela `agendamento_status_historico` (agendamento_id, status_anterior, status_novo, origem, usuario_id, criado_em) — **implementar na V1**

**Regra crítica:** Sistema **NÃO** transforma automaticamente agendamento passado em `realizado` (remover `atualizar_agendamentos_realizados` do `init_db`)

---

### 2.7 Cancelamento

| Aspecto | Especificação |
|---------|---------------|
| Quem pode cancelar | Cliente (via token/link) + Admin (painel) |
| O que preserva | Agendamento completo: cliente, serviços, profissional, data/hora, histórico, **origem do cancelamento** |
| Efeito imediato | Status → `cancelado`; libera horário para nova reserva; remove da receita prevista |
| Registro | `status_origem = 'cliente'` ou `'admin'`; entrada em `agendamento_status_historico` |
| Interface admin | Botão "Cancelar" em cada linha da tabela + confirmação modal |
| Interface cliente | Página `/reserva/<token>` → botão "Cancelar minha reserva" + confirmação |

---

### 2.8 Reagendamento

| Aspecto | Especificação |
|---------|---------------|
| Fluxo | Admin: editar agendamento → nova data/horário → validar disponibilidade → confirmar |
| Preservação | **Não criar status "reagendado"** — manter status atual (`agendado`) |
| Histórico | Registrar em `agendamento_status_historico` (ou tabela dedicada `agendamento_reagendamento`: agendamento_id, data_anterior, hora_anterior, data_nova, hora_nova, usuario_id, criado_em) |
| Validações | Disponibilidade (profissional, duração total, antecedência, conflitos); mesmo profissional (ou permitir trocar?) |
| Cliente | Futuro: cliente via token pode reagendar (fora da V1?) — **V1: apenas admin** |

---

### 2.9 Serviços

**Operações administrativas obrigatórias na V1:**
- criar serviço;
- editar serviço;
- alterar preço;
- alterar duração;
- alterar nome;
- alterar descrição;
- ativar serviço;
- desativar serviço;
- visualizar preço atual;
- visualizar duração atual;
- visualizar status (ativo/inativo).

**Regra de Preço (snapshot imutável):**
- o preço cadastrado no serviço é o **preço atual** utilizado para novos agendamentos;
- o Admin pode alterar esse preço a qualquer momento;
- alterar o preço **não altera** o valor de agendamentos já existentes;
- cada agendamento deve preservar o preço efetivamente utilizado no momento da reserva através do **snapshot em `agendamento_servico`** (colunas `preco_unitario`, `duracao_minutos` copiadas do serviço na criação).

**Regra de Duração (snapshot imutável):**
- a duração cadastrada no serviço é a **duração atual** utilizada para novos agendamentos;
- o Admin pode alterar essa duração a qualquer momento;
- alterar a duração **não altera** a duração de agendamentos já existentes;
- a duração utilizada em agendamentos existentes deve permanecer preservada no **snapshot em `agendamento_servico`** (coluna `duracao_minutos` copiada do serviço na criação).

| Operação | Regras |
|----------|--------|
| Cadastrar | Nome, descrição, preço, duração_minutos, ativo=TRUE |
| Editar | Todos os campos (nome, descrição, preço, duração); **alteração de preço/duração NÃO afeta agendamentos passados** (valor/duração fixados no agendamento via snapshot em `agendamento_servico`) |
| Ativar/Desativar | `ativo` boolean; inativos não aparecem no agendamento público |
| Excluir | **Não exclusão física** se houver histórico — apenas desativar |
| Histórico | Agendamento guarda snapshot do preço/duração no momento (via `agendamento_servico` + campos `preco_unitario`, `duracao_minutos` na tabela de junção) — **colunas já previstas** |

---

### 2.10 Profissionais

| Operação | Regras |
|----------|--------|
| Cadastrar | Nome, ativo=TRUE |
| Editar | Nome |
| Ativar/Desativar | `ativo` boolean; inativos não aparecem no agendamento público |
| Definir serviços | Relação N:M via `profissional_servico` (nova tabela) |
| Excluir | **Não exclusão física** se houver histórico — apenas desativar |

---

### 2.11 Configuração do Estabelecimento (Consolidado)

**Tabela `estabelecimento` (registro único):**

| Seção | Campos |
|-------|--------|
| **Identificação** | `nome` (interno), `nome_publico` (página pública), `descricao` |
| **Contato** | `telefone`, `whatsapp`, `email` |
| **Endereço** | `cep`, `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `estado` |
| **Identidade Visual** | `logo_url` (caminho/URL do arquivo) |
| **Funcionamento** | `dias_funcionamento` (array int 0-6), `horario_abertura` (time), `horario_fechamento` (time) |
| **Agendamento** | `antecedencia_maxima_dias` (int, default 14) |
| **Conta** | `senha_admin_hash` (já em `admin`), fluxo alteração já existe |

**Fora da V1:** Múltiplas unidades, redes sociais, SEO, banner, galeria, cores personalizadas, favicon, recuperação de senha

---

### 2.12 Disponibilidade — Regras Completas

Um horário está disponível **SE E SOMENTE SE**:

1. **Funcionamento:** Data está em dia de funcionamento; horário dentro de abertura/fechamento
2. **Profissional:** Profissional está `ativo = TRUE`
3. **Profissional-Serviço:** Profissional realiza **todos** os serviços selecionados (via `profissional_servico`)
4. **Duração total:** Bloco contínuo de slots = `ceil(soma(duracao_servicos) / intervalo_slot)`
5. **Conflitos:** Nenhum agendamento `status = 'agendado'` para mesmo profissional no mesmo horário (considerando duração)
6. **Agendamentos ativos:** Apenas `status = 'agendado'` bloqueia; `realizado`, `nao_compareceu`, `cancelado` **não bloqueiam**
7. **Antecedência:** Data ≤ `hoje + antecedencia_maxima_dias`
8. **Passado:** Não permitir horários já passados no dia de hoje

**Validação:** Backend (models.horarios_disponiveis) + revalidação na criação (já existe)

---

### 2.13 Histórico e Valores (Imutabilidade)

- Agendamento **deve preservar** snapshot dos dados no momento da reserva:
  - `agendamento_servico` precisa de colunas: `preco_unitario`, `duracao_minutos` (copiados do serviço na criação)
  - Alteração futura de preço/duração do serviço **não altera** agendamentos antigos
  - Cliente: `cliente_id` + snapshot nome/telefone/email no agendamento (para caso cliente seja alterado depois)
  - Profissional: snapshot nome no agendamento

---

### 2.14 Segurança (V1 — O que Deve Ser Tratado)

| Item | Etapa | Observação |
|------|-------|------------|
| Autenticação admin (sessão + hash) | ✅ Fase 1 | Já implementado |
| Alteração de senha (valida atual, confirma, hash) | ✅ Fase 1 | Já implementado |
| Proteção rotas admin (`@login_requerido`) | ✅ | Já implementado |
| **SECRET_KEY obrigatória (sem fallback)** | ✅ Fase 1 | Já implementado |
| **ADMIN_SENHA_INICIAL obrigatória** | ✅ Fase 1 | Já implementado |
| **CSRF protection** | 🔄 Fase 2 | Flask-WTF nos forms admin |
| **Rate limiting login** | 🔄 Fase 2 | Flask-Limiter em `/admin/login` |
| **Lock concorrência agendamento** | 🔄 Fase 2 | Advisory lock (profissional+data) em `criar_agendamento` |
| **Validação de entrada (backend)** | 🔄 Fase 2 | Já parcial; completar |
| **Token de acesso cliente (reserva)** | 🔄 Fase 3 | UUID imprevisível, rota `/reserva/<token>` |
| **Credenciais fora do código/Git** | ✅ | `.env` + `.env.example` |
| **Concorrência criação agendamento** | 🔄 Fase 2 | Ver lock acima |

---

### 2.15 Ordem de Implementação (Fases Pequenas, Independentes, Validáveis)

#### FASE 1 — Banco e Modelos (Base) ✅ **CONCLUÍDA**
- [x] Tabela `configuracao` + seed + funções CRUD
- [x] `SECRET_KEY` obrigatória, `ADMIN_SENHA_INICIAL` obrigatória
- [x] Coluna `senha_inicial_alterada` em `admin`
- [x] Validação antecedência máxima no backend (`models.data_permitida`)
- [x] Cache configurações dinâmico (`models.py`)

#### FASE 2 — Backend/API + Segurança Core
1. **Lock concorrência** em `criar_agendamento` (advisory lock por profissional+data)
2. **CSRF + Rate limiting** (Flask-WTF + Flask-Limiter)
3. **CRUD Serviços API** (listar, criar, editar, ativar/desativar) + coluna `ativo` + snapshot preço/duração em `agendamento_servico`
4. **CRUD Profissionais API** + tabela `profissional_servico` (N:M)
5. **Validação disponibilidade** considerar `profissional_servico`
6. **Remover** `atualizar_agendamentos_realizados` do `init_db`

#### FASE 3 — Entidade Cliente + Migração
1. **Criar tabela `cliente`** (id, nome, telefone, email, observacoes, criado_em)
2. **Migração dados:** Agrupar agendamentos existentes por (nome, telefone) → criar cliente → popular `agendamento.cliente_id`
3. **Adicionar `cliente_id` em `agendamento`** (FK, nullable → NOT NULL)
4. **API Cliente:** buscar/criar por telefone, listar, histórico
5. **Agendamento público:** buscar cliente por telefone; se não existe, criar; associar `cliente_id`

#### FASE 4 — Administração (Painel)
1. **CRUD Serviços** (tela admin): criar, editar (nome, descrição, **preço**, **duração**), ativar, desativar, listar
2. **CRUD Profissionais** (tela admin + vincular serviços)
3. **CRUD Clientes** (listar, buscar, ver histórico)
4. **Configurações Estabelecimento** (tela única consolidada)
5. **Cancelar agendamento** (botão na tabela + modal + origem)
6. **Dashboard** atualizar indicadores para 4 status

#### FASE 5 — Reagendamento + Token Cliente
1. **Reagendamento admin** (fluxo completo + histórico em `agendamento_reagendamento`)
2. **Token de acesso** (`agendamento.token_acesso` UUID + rota `/reserva/<token>`)
3. **Página cliente** (`/reserva/<token>`): visualizar + cancelar própria reserva
4. **Exibir token/link** na confirmação (`sucesso.html`)

#### FASE 6 — Tabela Estabelecimento + Logo
1. **Criar tabela `estabelecimento`** (registro único) + migrar de `configuracao`
2. **Upload/remoção logo** + exibição na área pública
3. **Remover** configs obsoletas de `configuracao` (manter apenas as não migradas?)

#### FASE 7 — UX/UI + Mobile
1. Revisão completa mobile-first
2. Acessibilidade básica
3. Feedback visual (loading, erros, sucesso)

#### FASE 8 — Testes Automatizados
1. Suite pytest: services, profissionais, disponibilidade, agendamento, cancelamento, reagendamento, antecedência, configurações, auth, alteração senha, cliente, token
2. Testes de regressão

#### FASE 9 — Backup/Recuperação + Documentação
1. Scripts backup/restore PostgreSQL documentados + validados
2. Atualizar `REGRAS-AGENDAMENTOS.md` com 4 status + transições
3. Documentar procedimentos operacionais

#### FASE 10 — Homologação + Deploy
1. Cenário completo simulando estabelecimento real (checklist do Plano §18)
2. Homologação local → homologação → produção
3. Validação `agenda.alllogiconline.com.br`

---

## 3. DEPENDÊNCIAS ENTRE MÓDULOS (GRÁFICO)

```
Banco/Modelos (Fase 1,3)
    │
    ├─→ Backend/API (Fase 2) ←── Segurança Core (Fase 2)
    │       │
    │       ├─→ Admin: Serviços/Profissionais (Fase 4)
    │       ├─→ Admin: Clientes (Fase 3→4)
    │       ├─→ Admin: Configurações (Fase 4,6)
    │       ├─→ Admin: Cancelar/Reagendar (Fase 4,5)
    │       ├─→ Público: Agendamento (Fase 3→5)
    │       └─→ Dashboard (Fase 4)
    │
    ├─→ Cliente (Fase 3) ←── Migração dados existentes
    │       │
    │       └─→ Token acesso reserva (Fase 5)
    │
    └─→ Estabelecimento (Fase 6) ←── Consolida configuração
```

---

## 4. CONFLITOS IDENTIFICADOS (Documentação vs Código vs Novas Decisões)

| Item | Documentação Atual | Código Atual | Nova Decisão | Ação |
|------|-------------------|--------------|--------------|------|
| Status agendamento | `REGRAS-AGENDAMENTOS.md`: apenas `agendado`, `cancelado` | `database.py` atualiza auto para `realizado`; `app.py` usa `realizado` em receita | **4 status**: agendado, realizado, nao_compareceu, cancelado | Atualizar `REGRAS-AGENDAMENTOS.md`; remover auto-update; implementar transições |
| Cliente | `AGENTS.md §11`: entidade própria planejada | Nome/telefone direto no agendamento | **Obrigatório na V1** | Criar tabela + migração (Fase 3) |
| Acesso cliente reserva | Não especificado | Não existe | **Token/link individual** | Implementar Fase 5 |
| Reagendamento | `REGRAS`: preservar histórico, sem status "reagendado" | Não existe | **Sem status "reagendado"; tabela histórico dedicada** | Implementar Fase 5 |
| Serviços inativos | `V1 Comercial §3`: desativados não aparecem | Coluna `ativo` não existe | Adicionar `ativo` + filtro | Fase 2 |
| Profissional-serviço | `V1 Comercial §3`: definir quais serviços realiza | Não existe | Tabela N:M `profissional_servico` | Fase 2 |
| Configurações | Dispersas em `configuracao` | 9 chaves em `configuracao` | **Tabela `estabelecimento` consolidada** | Fase 6 |
| Antecedência | `V1 Comercial §11`: configurável, persistida no BD | Backend valida (Fase 1 ✅) | Manter; admin edita via Configurações | Fase 4 |
| Receita prevista | `REGRAS §52`: apenas `agendado` | `app.py`: `agendado` + `realizado` | **Corrigir: apenas `agendado`** | Fase 4 |
| Auto-realizado | Não documentado | `database.py:206-214` faz UPDATE automático | **REMOVER** — admin define manual | Fase 2 |

---

## 5. DECISÕES PENDENTES (Precisam de Definição Antes da Implementação)

1. **Migração cliente:** Como lidar com duplicatas (mesmo nome/telefone em agendamentos diferentes)? Regra: agrupar por telefone normalizado; se nomes diferentes, criar cliente com nome mais frequente + observação.
2. **Snapshot preço/duração:** Adicionar `preco_unitario`, `duracao_minutos` em `agendamento_servico` OU criar tabela `agendamento_servico_historico`? **Decisão:** colunas na própria `agendamento_servico` (simples, atende V1).
3. **Reagendamento por cliente:** V1 permite apenas admin. Cliente reagenda via cancelar + novo agendamento? **Decisão:** V1 = apenas admin; cliente cancela e faz novo.
4. **Troca de profissional no reagendamento:** Permitir? **Decisão:** Sim, validando disponibilidade do novo profissional.
5. **Tabela `estabelecimento` vs `configuracao`:** Migrar tudo ou manter `configuracao` para configs técnicas? **Decisão:** `estabelecimento` = dados do negócio; `configuracao` = parâmetros técnicos (intervalo_slot, etc.).
6. **Logo:** Armazenar como arquivo (volume) ou base64 no BD? **Decisão:** Arquivo em volume Docker + caminho no BD.
7. **Índices de performance:** Quais criar na V1? **Mínimo:** `agendamento(profissional_id, data)`, `agendamento(cliente_id)`, `agendamento(status)`.
8. **Cancelamento pelo cliente:** Exigir motivo? **Decisão:** Opcional, campo `cancelamento_motivo` em `agendamento` (nullable).

---

## 6. CHECKLIST DE CONFORMIDADE (AGENTS.md / FOUNDATION.md)

- [x] Preserva o que funciona (código Fase 1 válido)
- [x] Evolução incremental (fases pequenas)
- [x] Prioriza valor comercial (critério de saída claro)
- [x] Evita complexidade prematura (sem multi-tenancy, SaaS, CRM, pagamentos)
- [x] PostgreSQL como padrão (já implementado)
- [x] Dados existentes preservados (migrações com IF NOT EXISTS)
- [x] Segurança: sem secrets no código, hash scrypt, SECRET_KEY obrigatória
- [x] Git: alterações versionadas por fase
- [x] Documentação: esta especificação + docs atualizados conforme implementação
- [x] Independência de outros projetos AllLogic (OfertaIA, etc.)

---

## 7. PRÓXIMOS PASSOS IMEDIATOS (Início Fase 2)

1. **Implementar lock de concorrência** em `criar_agendamento` (advisory lock)
2. **Adicionar CSRF + Rate limiting** (Flask-WTF, Flask-Limiter)
3. **Adicionar coluna `ativo` em `servico`** + migração + filtro nas listagens
4. **Criar tabela `profissional_servico`** + API CRUD
5. **Atualizar `horarios_disponiveis`** para filtrar por `profissional_servico`
6. **Remover `atualizar_agendamentos_realizados`** do `init_db`
7. **Atualizar `REGRAS-AGENDAMENTOS.md`** com 4 status + transições

---

*Documento versão 1.0 — Consolidado a partir de AGENTS.md, FOUNDATION.md, V1 Comercial, Plano de Finalização, REGRAS-AGENDAMENTOS.md, ARQUITETURA-BANCO.md, Auditoria Técnica, Roadmap e estado atual do código (set/2026).*