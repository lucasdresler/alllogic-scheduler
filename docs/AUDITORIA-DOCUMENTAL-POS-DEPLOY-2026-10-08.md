# Auditoria Documental Pós-Deploy — Agillex Agenda
**Data da Auditoria:** 2026-10-08  
**Projeto:** AllLogic Scheduler (Agillex Agenda)  
**Ambiente:** Produção (`https://agenda.alllogiconline.com.br`) & Repositório Local (`~/AllLogic/Projetos/app-agendamento`)  
**Commit Auditado:** `843e291` (*feat: melhorar confirmacao e formulario de reagendamento*)  
**Commit Anterior em Produção:** `d41485b` (*feat: implementar acoes administrativas da agenda*)  
**Classificação:** Auditoria e Diagnóstico Documental Pós-Deploy (Sem alteração de código ou de documentos originais nesta etapa)

---

## 1. Identificação e Contexto da Auditoria

Esta auditoria tem como finalidade confrontar o estado real da aplicação e da infraestrutura de produção — após a publicação bem-sucedida do commit `843e291` — com o conjunto de documentos técnicos, arquiteturais, operacionais e estratégicos existentes no repositório `alllogic-scheduler` e no SGA.

### Dados de Referência Verificados
- **Commit implantado em produção:** `843e29159b277daca6b5f64cca49a26ccbccf6b2` (`843e291`).
- **Commit imediatamente anterior em produção:** `d41485b0b6e8261fdc0d53ddcd2a40dad0662c15` (`d41485b`).
- **Commit intermediário incluído no deploy:** `c8ee4b0122ae5ac33fa2b25014888bb8dacb6c07` (`c8ee4b0` — pesquisa de agendamentos e semana Domingo a Sábado).
- **Diretório de backup pré-deploy ativo e íntegro na VPS:**  
  `/opt/alllogic/backups/scheduler/pre-d41485b-20261009T020819Z/`
- **Artefatos validados no backup via SHA-256:**
  - `postgres-alllogic_scheduler.dump` (26 KB)
  - `scheduler-image.tar` (56 MB)
  - `source-before.bundle` (1.6 MB)
  - `compose.yaml` (634 B)
  - `.env` (311 B, modo 600)
  - `SHA256SUMS` (todos validados com `OK`)
- **Tag Docker de rollback:** `scheduler-scheduler:rollback-d41485b-20261009T020819Z`.
- **Serviços em produção:** Container `alllogic-scheduler` ativo (porta 8000), roteado via Traefik v3.6.1 com TLS Let's Encrypt para `agenda.alllogiconline.com.br`, conectado ao cluster PostgreSQL 17 (`alllogic-postgres`).

---

## 2. Documentos Consultados

Durante esta auditoria foram analisados integralmente os seguintes documentos:

### Governança e SGA
1. `~/AllLogic/AGENTS.md` (Diretrizes gerais corporativas da AllLogic).
2. `~/AllLogic/SGA/FOUNDATION.md` (Fundamentos, valores e código de ética da AllLogic).
3. `~/AllLogic/SGA/02-Governanca/padroes/padrao-documentacao-tecnica.md` (Estrutura e princípios documentais).
4. `~/AllLogic/SGA/02-Governanca/adr/ADR-001-padrao-postgresql-vps.md` (Padrão de banco de dados PostgreSQL por VPS).

### Documentação do Projeto
5. `~/AllLogic/Projetos/app-agendamento/AGENTS.md` (Regras de desenvolvimento do AllLogic Scheduler).
6. `~/AllLogic/Projetos/app-agendamento/FOUNDATION.md` (Princípios fundamentais do Scheduler).
7. `~/AllLogic/Projetos/app-agendamento/README.md` (Apresentação e visão técnica do repositório).
8. `~/AllLogic/Projetos/app-agendamento/docs/roadmap.md` (Roadmap oficial de marcos do projeto).
9. `~/AllLogic/Projetos/app-agendamento/docs/AllLogic-Scheduler-Plano-Finalizacao-V1.md` (Plano de finalização da V1 Comercial).
10. `~/AllLogic/Projetos/app-agendamento/docs/AllLogic-Scheduler-V1-Comercial.md` (Escopo comercial da V1).
11. `~/AllLogic/Projetos/app-agendamento/ESPECIFICACAO-V1-CONSOLIDADA.md` (Especificação consolidada de requisitos e módulos).
12. `~/AllLogic/Projetos/app-agendamento/MATRIZ-RECURSOS-VERSOES.md` (Matriz de recursos por versão).
13. `~/AllLogic/Projetos/app-agendamento/docs/REGRAS-AGENDAMENTOS.md` (Regras de status, ciclo de vida e agendamentos).
14. `~/AllLogic/Projetos/app-agendamento/docs/INFRAESTRUTURA.md` (Inventário de infraestrutura e hospedagem KingHost).
15. `~/AllLogic/Projetos/app-agendamento/docs/ARQUITETURA-BANCO.md` (Arquitetura de banco de dados).
16. `~/AllLogic/Projetos/app-agendamento/docs/AMBIENTE-DESENVOLVIMENTO.md` (Configuração do ambiente local).
17. `~/AllLogic/Projetos/app-agendamento/docs/VALIDACAO-BLOCO-3-2026-09-30.md` (Relatório histórico de homologação do Bloco 3).
18. `~/AllLogic/Projetos/app-agendamento/docs/VALIDACAO-FASE-2-2026-09-30.md` (Relatório histórico de validação da Fase 2).
19. `~/AllLogic/Projetos/app-agendamento/AUDITORIA-TECNICA-V1.md` (Auditoria técnica prévia do código e arquivos legados).

---

## 3. Estado do Repositório Git Antes da Auditoria

```text
No ramo main
Your branch is up to date with 'origin/main'.

Arquivos não monitorados:
  (utilize "git add <arquivo>..." para incluir o que será submetido)
	Logo Dourado de Salão Premium.png

nada adicionado ao envio mas arquivos não registrados estão presentes (use "git add" to registrar)
```

- **Branch:** `main` perfeitamente sincronizada com `origin/main`.
- **Commit local e remoto:** `843e291`.
- **Arquivos modificados ou staged:** Nenhum.
- **Arquivo não rastreado:** `Logo Dourado de Salão Premium.png` (mantido estritamente fora do controle de versão e do deploy).

---

## 4. Resumo Executivo

A aplicação web Agillex Agenda (AllLogic Scheduler) evoluiu significativamente através de sucessivos blocos de implementação, homologações locais com testes automatizados e deploy em produção na VPS KingHost sob o domínio oficial `https://agenda.alllogiconline.com.br`.

No entanto, a auditoria constatou um **descompasso relevante entre o código/infraestrutura real e a documentação versionada do repositório**:

1. **Atraso nos marcos do roadmap:** O arquivo `docs/roadmap.md` ainda descreve o projeto como estando no *"Marco 4 (Em andamento)"*, embora os recursos do Marco 5 (gestão de serviços, profissionais, ações da agenda, pesquisa, cancelamento e reagendamento) e do Marco 8 (deploy em produção com Docker e Traefik) já estejam efetivamente implementados, testados e no ar.
2. **Defasagem da especificação consolidada:** A tabela de módulos em `ESPECIFICACAO-V1-CONSOLIDADA.md` ainda marca recursos como *"CRUD de Serviços"*, *"CRUD de Profissionais"*, *"Reagendar"*, *"Cancelar"* e *"Logo"* como inexistentes ou parciais, quando todos já estão em produção.
3. **Ausência de registro dos testes automatizados:** O documento `docs/VALIDACAO-BLOCO-3-2026-09-30.md` registra formalmente que *o projeto não possuía suíte automatizada*. Na realidade atual, o projeto conta com uma suíte madura de **48 testes automatizados no pytest** cobrindo todos os fluxos críticos contra PostgreSQL.
4. **Inventário de infraestrutura estático:** `docs/INFRAESTRUTURA.md` reflete um inventário preliminar de 14/09/2026 que planejava o Scheduler como algo futuro. Não descreve a stack real `/opt/alllogic/stacks/scheduler`, a rede interna `allLogic-internal` nem o container de banco `alllogic-postgres`.
5. **Diferença conceitual entre backup e teste de restauração:** A infraestrutura possui rotinas determinísticas de cópia de segurança pré-deploy (`pg_dump`, `docker save`, bundles e checksums), mas **não há evidência documental de um teste real de restauração (restore drill)** executado em ambiente isolado para comprovar a recuperação de desastres.
6. **Necessidade de homologação funcional humana em produção:** Embora os testes automatizados (48/48) e as sondagens HTTP/HTTPS (200 OK) estejam aprovados, a **homologação funcional no navegador pelo usuário final em produção** ainda está pendente de validação visual/operacional interativa.

---

## 5. Matriz de Divergências Documentais

| Documento | Situação | Evidência / Realidade Atual | Correção Necessária | Prioridade |
| :--- | :--- | :--- | :--- | :--- |
| **`README.md`** | **Desatualizada** | Informa status *"🚧 Em desenvolvimento – Projeto Fênix"*; cita execução legada via serviço systemd (`barbearia-top.service`) e proxy Nginx. Não cita os 48 testes automatizados nem a arquitetura Docker Compose + Traefik. | Atualizar nome do produto (Agillex Agenda / AllLogic Scheduler), remover referências legadas ao serviço systemd/Nginx e descrever o fluxo Docker/Compose e a suíte de testes. | **Alta** |
| **`docs/roadmap.md`** | **Desatualizada** | Registra estado atual no Marco 4 (revisar múltiplos serviços). Marcos 5 a 8 constam como pendentes. | Atualizar status dos Marcos 4, 5 e 8 para concluídos. Registrar o deploy em produção do commit `843e291`. Atualizar o estado atual para homologação em produção e consolidação da V1. | **Alta** |
| **`ESPECIFICACAO-V1-CONSOLIDADA.md`** | **Desatualizada** | Tabela 2.1 a 2.3 lista Reagendamento (`❌ Não existe`), CRUD Serviços (`❌ Não existe`), CRUD Profissionais (`❌ Não existe`), Cancelamento (`Parcial`), Logo (`❌ Não existe`). | Atualizar as tabelas refletindo a implementação completa dos CRUDs de serviços, profissionais, disponibilidades, logotipo, cancelamento e reagendamento homologados. | **Alta** |
| **`docs/INFRAESTRUTURA.md`** | **Desatualizada** | Data de 14/09/2026. Descreve a implantação do Scheduler como futura (*"deverá utilizar..."*). Não detalha o container `alllogic-scheduler`, o container `alllogic-postgres` nem o diretório `/opt/alllogic/stacks/scheduler`. | Atualizar o inventário para registrar os containers ativos em produção, a rede `allLogic-internal`, a pasta da stack e o procedimento de deploy efetivo. | **Média** |
| **`docs/VALIDACAO-BLOCO-3-2026-09-30.md`** | **Desatualizada / Histórica** | Documenta o Bloco 3 como *"NÃO APTO PARA VERSIONAMENTO"* e diz que *não há suíte de testes automatizados*. | Manter este documento como histórico de 30/09 e criar ou referenciar um relatório oficial de validação pós-Bloco 3 registrando os 48 testes aprovados. | **Média** |
| **`docs/REGRAS-AGENDAMENTOS.md`** | **Atual com Ressalva** | As regras de negócio e de ciclo de vida de status estão aderentes ao código. Porém, não descreve a tela de confirmação de 5 segundos de reagendamento nem a busca/pesquisa administrativa introduzida em `c8ee4b0`. | Adicionar seção documentando o fluxo de confirmação após reagendamento e os critérios de pesquisa/filtragem de agendamentos. | **Média** |
| **`docs/AllLogic-Scheduler-Plano-Finalizacao-V1.md`** | **Desatualizada** | Itens da ordem prática (configurações, estabelecimento, serviços, profissionais, horários, cancelamento, reagendamento, testes) aparecem como lista de afazeres futuros. | Adicionar seção de status final marcando os itens concluídos e isolando apenas as pendências reais de fechamento da V1. | **Média** |
| **`docs/ARQUITETURA-BANCO.md`** | **Atual com Ressalva** | Descreve adequadamente a migração SQLite -> PostgreSQL e a tabela `agendamento_servico`. Não menciona a tabela `configuracao` expandida nem os snapshots de profissional/serviço no agendamento. | Atualizar o esquema relacional com as colunas de snapshot adicionadas e documentar o estado do modelo de dados. | **Baixa** |
| **Procedimentos de Backup e Rollback** | **Não comprovada** | Os backups pré-deploy existem e estão verificados (`SHA256SUMS: OK`). Todavia, nenhum documento registra um teste real de restauração do dump (`pg_restore`) executado com sucesso. | Registrar explicitamente que as cópias de segurança estão operacionais, mas o teste prático de restauração (restore drill) permanece pendente de execução. | **Alta** |
| **Escopo Futuro (CRM, WhatsApp, Pagamentos)** | **Atual** | Documentos mantêm tais recursos explicitamente adiados fora da V1. O código não implementou tais itens prematuramente. | Nenhuma correção necessária. Princípio de escopo respeitado. | — |

---

## 6. Pendências de Homologação Funcional

A auditoria enfatiza que **um deploy técnico bem-sucedido não substitui a homologação funcional**:

1. **Validação visual e operacional no navegador (Produção):**
   - Acesso autenticado ao painel administrativo em `https://agenda.alllogiconline.com.br/admin/login`.
   - Execução de um reagendamento de teste para constatar:
     - Apresentação da nova tela de confirmação (`/admin/agendamento/<id>/reagendar`).
     - Título único *"Reagendamento realizado com sucesso!"* (ausência de duplicidade de mensagens).
     - Contagem regressiva visual de 5 segundos.
     - Redirecionamento automático correto de volta para a Agenda.
     - Preservação do contexto (aba selecionada, filtros de pesquisa, profissional e data).
     - Tipografia corrigida nos campos de data e horário (tamanho de fonte `0.95rem` e família Poppins padronizada).
2. **Validação da Pesquisa de Agendamentos (Produção):**
   - Filtragem combinada por nome do cliente, telefone, status, profissional e período.
   - Limpeza de filtros e preservação do estado após ações de cancelamento ou conclusão.
3. **Validação da Navegação Semanal (Produção):**
   - Conferência da exibição dos dias da semana iniciando no Domingo e encerrando no Sábado.
   - Verificação do rótulo *"Valor dos agendamentos"* nos cards de resumo financeiro do dashboard.

> [!NOTE]
> **Nota de Atualização (2026-10-09):**  
> Em 09/10/2026, o usuário realizou a validação funcional completa no navegador em ambiente de produção (`https://agenda.alllogiconline.com.br/`) e confirmou formalmente que a aplicação está operando corretamente, considerando a homologação funcional como **concluída com sucesso**. O registro original acima é mantido como histórico fidedigno da auditoria realizada em 08/10/2026.

---

## 7. Pendências Documentais e Operacionais

1. **Reconciliação dos documentos da V1:** Atualizar os arquivos técnicos e de visão geral para refletir que o AllLogic Scheduler já atingiu funcionalmente os requisitos essenciais da V1 Comercial.
2. **Registro de teste de restauração (Restore Drill):** Planejar e executar em ambiente de teste ou homologação a restauração de um dump gerado (`pg_restore` no PostgreSQL de homologação) para certificar a recuperabilidade total em caso de desastre.
3. **Limpeza de arquivos legados (Auditoria Técnica V1):** Decidir o arquivamento formal dos arquivos legados `barbearia-top.service` e `nginx_barbearia_top.conf` presentes na raiz do repositório (conforme apontado no `AUDITORIA-TECNICA-V1.md`).
4. **Isolamento de arquivos locais não versionados:** Manter `Logo Dourado de Salão Premium.png` fora do repositório ou adicioná-lo ao `.gitignore` local se for um artefato definitivo de desenvolvimento do cliente.

---

## 8. Lista de Documentos que Precisam de Atualização

Os seguintes documentos deverão ser editados em uma etapa posterior de reconciliação documental:

1. [README.md](file:///home/dresler/AllLogic/Projetos/app-agendamento/README.md)
2. [docs/roadmap.md](file:///home/dresler/AllLogic/Projetos/app-agendamento/docs/roadmap.md)
3. [ESPECIFICACAO-V1-CONSOLIDADA.md](file:///home/dresler/AllLogic/Projetos/app-agendamento/ESPECIFICACAO-V1-CONSOLIDADA.md)
4. [docs/INFRAESTRUTURA.md](file:///home/dresler/AllLogic/Projetos/app-agendamento/docs/INFRAESTRUTURA.md)
5. [docs/AllLogic-Scheduler-Plano-Finalizacao-V1.md](file:///home/dresler/AllLogic/Projetos/app-agendamento/docs/AllLogic-Scheduler-Plano-Finalizacao-V1.md)
6. [docs/REGRAS-AGENDAMENTOS.md](file:///home/dresler/AllLogic/Projetos/app-agendamento/docs/REGRAS-AGENDAMENTOS.md)
7. [docs/ARQUITETURA-BANCO.md](file:///home/dresler/AllLogic/Projetos/app-agendamento/docs/ARQUITETURA-BANCO.md)

---

## 9. Próximo Passo Recomendado

Para manter a governança rigorosa e a rastreabilidade do AllLogic Scheduler, recomenda-se a seguinte ordem de continuidade:

1. **Submeter este relatório de auditoria à revisão do usuário/responsável.**
2. **Executar a homologação funcional humana em produção** via navegador em `https://agenda.alllogiconline.com.br/`, validando o fluxo de reagendamento (5 segundos, dados exibidos, tipografia e retorno à agenda).
3. **Após o aceite da homologação funcional**, abrir uma sessão dedicada de **reconciliação documental**, atualizando de forma incremental e versionada os documentos listados na Seção 8, consolidando formalmente o fechamento da V1 Comercial do produto.
