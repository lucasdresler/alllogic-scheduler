# Relatório de Preparação e Validação do Backup Pré-Deploy

**Data da Execução:** 11/10/2026  
**Projeto:** AllLogic Scheduler (Agillex Agenda)  
**Ambiente Alvo:** Produção VPS KingHost (`177.153.203.158`)  
**Commit Publicado em `origin/main`:** `3f225a748ab91fed5edde1e2f9db77bea17bad8e` (`3f225a7`)  
**Commit Efetivo em Produção (VPS):** `843e29159b277daca6b5f64cca49a26ccbccf6b2` (`843e291`)  
**Diretório de Backup Criado na VPS:** `/opt/alllogic/backups/scheduler/pre-843e291-20261011T130745Z`  
**Responsável Técnico:** Antigravity AI Pair Programming  
**Conclusão da Etapa:** **BACKUP VALIDADO**

---

## 1. Instruções e Procedimentos Consultados

A preparação e execução deste backup seguiram rigorosamente as diretrizes operacionais de governança:
1. `~/AllLogic/AGENTS.md` (Governança corporativa da AllLogic).
2. `~/AllLogic/SGA/FOUNDATION.md` (Princípios fundamentais, integridade e resiliência de infraestrutura).
3. `~/AllLogic/Projetos/app-agendamento/AGENTS.md` (Regras operacionais do projeto AllLogic Scheduler).
4. `~/AllLogic/Projetos/app-agendamento/FOUNDATION.md` (Fundamentos e visão técnica do produto).
5. `docs/INFRAESTRUTURA.md` (Inventário de servidores, redes Docker `proxy`/`allLogic-internal` e Traefik).
6. `docs/AUDITORIA-PRE-DEPLOY-PRODUCAO-2026-10-10.md` (Procedimento oficial documentado de backup e rollback desacoplado).
7. `docs/AUDITORIA-PRE-DEPLOY-REDESIGN-ADMIN-2026-10-11.md` (Auditoria pré-deploy do redesign administrativo).

---

## 2. Verificações Pré-Backup (Somente Leitura)

### 2.1. Ambiente Local
- **Repositório Local:** `~/AllLogic/Projetos/app-agendamento`
- **HEAD Local:** `3f225a748ab91fed5edde1e2f9db77bea17bad8e`
- **Referência Remota `origin/main`:** `3f225a748ab91fed5edde1e2f9db77bea17bad8e` (sincronizada).
- **Working Tree:** Limpo, preservando relatórios não rastreados e `Logo Dourado de Salão Premium.png`.

### 2.2. Ambiente de Produção na VPS (`177.153.203.158`)
- **Diretório da Aplicação:** `/opt/alllogic/apps/alllogic-scheduler`
- **Commit em Execução:** `843e29159b277daca6b5f64cca49a26ccbccf6b2`
- **Estado do Git na VPS:** Limpo (`git status --short` vazio).
- **Armazenamento:** 54 GB livres na partição raiz (`/dev/xvda4` com 17% de uso).
- **Containers Ativos e Saudáveis:**
  - `alllogic-scheduler`: Status `Up 2 days` (Gunicorn na porta 8000).
  - `alllogic-postgres`: Status `Up 7 days (healthy)` (PostgreSQL 17).
  - `traefik`: Status `Up 2 weeks` (Traefik v3.6.1).
- **PostgreSQL:** `pg_isready` retornou `/var/run/postgresql:5432 - accepting connections`.

---

## 3. Artefatos de Backup Criados

O backup foi executado sem interromper os serviços de produção, com geração no diretório:  
`/opt/alllogic/backups/scheduler/pre-843e291-20261011T130745Z`

| Artefato | Formato / Tipo | Tamanho | Checksum SHA-256 |
|:---|:---|:---:|:---|
| `compose.yaml` | Arquivo texto de configuração Compose | 634 bytes | `12c689630439f1b159be57b8c67be998a31f20105fd706de2a05647265389fae` |
| `.env` | Variáveis de ambiente (modo `600`) | 311 bytes (9 linhas) | `088b9569c301116b315a85df7cebf048cc00f9672d6cc6983d29c5fd568a7a6c` |
| `postgres-alllogic_scheduler.dump` | Dump PostgreSQL Custom (`-Fc`) | 25.963 bytes (~26 KB) | `1bdd486e4628783211ae66f7139acb32a00c7567b6550bc180de434aa980d2e9` |
| `scheduler-image.tar` | Imagem Docker completa em execução | 58.490.368 bytes (~56 MB) | `deee3b3c737ab90a0743fb51c1713aaa5542d6ccc393c4151895824f0eb25df4` |
| `source-before.bundle` | Git Bundle binário do código fonte | 1.659.974 bytes (~1.6 MB) | `6df9478006f8237ce80b5dee143c76b88abc2bd84d31e9df703e3b8b6103c916` |
| `SHA256SUMS` | Manifesto consolidado de integridade | 351 bytes | N/A (Arquivo de manifesto) |

Adicionalmente, a imagem Docker em execução foi tagueada no daemon da VPS com a tag imutável de recuperação:  
`scheduler-scheduler:rollback-843e291-20261011T130745Z` (Image ID: `25b25264a6a7`, 238 MB).

---

## 4. Resultados das Verificações de Integridade

Todas as checagens foram realizadas de forma não destrutiva, sem restauração cega sobre o banco de produção:

1. **Validação do Manifesto SHA-256:**
   - Comando: `sha256sum -c SHA256SUMS`
   - Resultado: Todos os 5 artefatos retornaram `OK`.
2. **Validação Estrutural do Dump do PostgreSQL:**
   - Comando: `docker exec -i alllogic-postgres pg_restore --list < postgres-alllogic_scheduler.dump`
   - Resultado: Arquivo íntegro, versão PostgreSQL 17.11, formato CUSTOM com compressão gzip, contendo 66 entradas na TOC (Table of Contents), abrangendo todas as tabelas operacionais da aplicação: `admin`, `admin_token_recuperacao`, `agendamento`, `agendamento_reagendamento`, `agendamento_servico`, `agendamento_status_historico`, `configuracao`, `profissional`, `profissional_disponibilidade`, `profissional_servico`, `servico`.
3. **Validação da Imagem Docker:**
   - Comando: `tar -tvf scheduler-image.tar`
   - Resultado: Arquivo tarball consistente, contendo camadas e manifestos legíveis associados ao container atual.
4. **Validação do Bundle Git:**
   - Comando: `git bundle verify source-before.bundle`
   - Resultado: `source-before.bundle is okay`. Histórico completo confirmado a partir do commit `843e29159b277daca6b5f64cca49a26ccbccf6b2`.
5. **Validação da Configuração e Segurança do `.env`:**
   - Permissão confirmada em `-rw-------` (`chmod 600`), pertencente ao usuário `dresler:dresler`, sem exibição de conteúdo sensível em logs ou terminal.
6. **Saúde da Produção Pós-Backup:**
   - As sondagens HTTP/2 públicas em `https://agenda.alllogiconline.com.br/` e `/admin/login` retornaram `HTTP/2 200 OK`.
   - A criação do backup não causou degradação ou indisponibilidade no serviço.

---

## 5. Limitações, Riscos e Pendências

- **Limitações:** Nenhuma. Todos os artefatos foram gerados com integridade comprovada e permissões adequadas.
- **Riscos Identificados:** Nenhum risco identificado para o processo de deploy. O backup fornece capacidade de restauração instantânea da aplicação (via tag Docker e Git bundle) sem necessidade de tocar no banco de dados.
- **Pendências:** **NENHUMA ação de deploy foi realizada.** A publicação da nova versão em produção aguarda autorização humana explícita.

---

## 6. Conclusão Objetiva

Todos os critérios de segurança, completude e validação de artefatos foram integralmente atendidos.

### **BACKUP VALIDADO**
