# Relatório Técnico — Limpeza dos Dados de Homologação do Agillex Agenda

**Data:** 12/10/2026  
**Projeto Técnico:** AllLogic Scheduler (`app-agendamento`)  
**Módulo:** Gestão de Ambientes / Homologação Local  
**Banco de Dados Autorizado:** `scheduler_test_homologacao` (`127.0.0.1:5433`)  
**Status da Operação:** **CONCLUÍDO COM SUCESSO**

---

## 1. Identificação Confirmada do Banco

Em estrita conformidade com as diretrizes do `~/AllLogic/AGENTS.md` e os requisitos operacionais da tarefa:

1. **Host e Porta:** `127.0.0.1:5433` (instância PostgreSQL local em contêiner Docker `alllogic-scheduler-postgres`).
2. **Identificação da Conexão:** A identificação do banco foi verificada por consulta SQL direta no motor do PostgreSQL:
   ```sql
   SELECT current_database();
   ```
   **Resultado:** `scheduler_test_homologacao`.
3. **Isolamento Confirmado:**
   - O banco de aplicação regular `alllogic_scheduler` foi mantido isolado e intocado.
   - A VPS de produção (`177.153.203.158`) não foi acessada nem modificada.
   - O arquivo de configuração `.env` não foi alterado.

---

## 2. Backup e Validação de Recuperabilidade

Antes de qualquer operação de exclusão, foi gerado um backup completo do banco de homologação e sua capacidade de restauração foi testada e validada em ambiente isolado.

### 2.1. Artefatos de Backup Gerados

- **Dump Binário Customizado (formato pg_dump custom):**
  - **Caminho:** `/home/dresler/.gemini/antigravity-ide/brain/7a43f0a5-ce59-41d7-84d3-cfe91f27d45a/scratch/backup_pre_limpeza_scheduler_test_homologacao.dump`
  - **Tamanho:** 62 KB
  - **SHA-256:** `1c894d819f157d5d165dacab505f2e3ab1d8676148eadb30590b018422b431c3`

- **Dump SQL Texto (script SQL com DDL e dados):**
  - **Caminho:** `/home/dresler/.gemini/antigravity-ide/brain/7a43f0a5-ce59-41d7-84d3-cfe91f27d45a/scratch/backup_pre_limpeza_scheduler_test_homologacao.sql`
  - **Tamanho:** 203 KB
  - **SHA-256:** `fef953e6d064f79118fb2ddf3b7e5bedee9c67275d6974d9532cb693cbe8d8bc`

### 2.2. Validação da Recuperação do Backup

Para assegurar a viabilidade operacional de rollback:
1. Foi criado um banco PostgreSQL temporário isolado (`test_validation_backup_temp`).
2. O dump binário foi restaurado com sucesso utilizando `pg_restore`.
3. Foram auditadas as quantidades de registros na base restaurada, confirmando 100% de paridade com o estado pré-limpeza:
   - `agendamento`: 495 registros
   - `servico`: 426 registros
   - `profissional`: 423 registros
   - `configuracao`: 24 registros
   - `admin`: 994 registros
4. O banco temporário de teste foi encerrado e descartado após a validação.

---

## 3. Quantidade de Registros Antes e Depois, por Categoria

Todas as tabelas relacionadas a **Agendamentos**, **Serviços** e **Profissionais** foram limpas com sucesso. As tabelas de **Administração** e **Configuração do Estabelecimento** foram integralmente preservadas.

| Categoria | Tabela | Antes | Depois | Status |
| :--- | :--- | :---: | :---: | :--- |
| **Agendamentos** | `agendamento` | 495 | **0** | Registros removidos |
| Itens do Agendamento | `agendamento_servico` | 495 | **0** | Registros removidos |
| Histórico de Reagendamentos | `agendamento_reagendamento` | 55 | **0** | Registros removidos |
| Histórico de Status | `agendamento_status_historico` | 63 | **0** | Registros removidos |
| **Profissionais** | `profissional` | 423 | **0** | Registros removidos |
| Vínculos Profissional-Serviço | `profissional_servico` | 473 | **0** | Registros removidos |
| Grade de Disponibilidade | `profissional_disponibilidade` | 347 | **0** | Registros removidos |
| **Serviços** | `servico` | 426 | **0** | Registros removidos |
| **Administração** | `admin` | 994 | **994** | **100% Preservado** |
| Tokens de Recuperação | `admin_token_recuperacao` | 0 | **0** | Preservado |
| **Configurações Gerais** | `configuracao` | 24 | **24** | **100% Preservado** |

---

## 4. Tabelas Afetadas e Execução Transacional

A exclusão ocorreu estritamente de forma atômica e transacional, respeitando as regras de integridade referencial e as dependências de chaves estrangeiras (`Foreign Keys`):

1. **Dependências de Agendamentos:**
   - Remoção de `agendamento_reagendamento` (depende de `agendamento`);
   - Remoção de `agendamento_status_historico` (depende de `agendamento`);
   - Remoção de `agendamento_servico` (depende de `agendamento` e `servico`);
   - Remoção de `agendamento`.
2. **Dependências de Profissionais e Serviços:**
   - Remoção de `profissional_disponibilidade` (depende de `profissional`);
   - Remoção de `profissional_servico` (depende de `profissional` e `servico`);
   - Remoção de `profissional`;
   - Remoção de `servico`.
3. **Reinicialização de Sequências:**
   As sequências de chaves primárias foram reiniciadas em 1 para garantir previsibilidade na nova rodada de testes:
   - `agendamento_id_seq` -> 1
   - `agendamento_reagendamento_id_seq` -> 1
   - `agendamento_status_historico_id_seq` -> 1
   - `profissional_id_seq` -> 1
   - `servico_id_seq` -> 1
4. **Preservação Estrutural:**
   - Nenhum comando `DROP TABLE` foi executado.
   - O esquema, índices, constraints e tipos de dados do banco permaneceram inalterados.

---

## 5. Verificações de Integridade e Acesso Administrativo

Após a limpeza, o ambiente local foi testado contra o servidor Flask ativo (`http://127.0.0.1:5000`):

1. **Acesso Administrativo:**
   - A conta do administrador de homologação (`homolog_admin`) permaneceu ativa e capaz de autenticar no painel sem restrições.
   - As credenciais administrativas e tokens de sessão operaram normalmente.
2. **Navegação e Telas do Painel Administrativo:**
   As telas principais foram verificadas via Chrome DevTools Protocol em viewport desktop (1280x800):
   - **Dashboard (`/admin?aba=hoje`):** Respondeu com HTTP 200. Painel carregado sem erros, exibindo estado limpo de atendimentos.
   - **Serviços (`/admin/servicos`):** Respondeu com HTTP 200. Lista vazia exibida corretamente com opção de cadastro habilitada.
   - **Profissionais (`/admin/profissionais`):** Respondeu com HTTP 200. Lista vazia exibida corretamente com opção de cadastro habilitada.
   - **Estabelecimento (`/admin/estabelecimento`):** Respondeu com HTTP 200. Dados institucionais, endereço e horários do estabelecimento preservados.
   - **Configurações (`/admin/configuracoes`):** Respondeu com HTTP 200. Todas as 24 chaves de configuração do sistema mantidas intactas.
   - **Rodapé Institucional Agillex Premium:** Presente, estilizado e sem transbordamento em todas as rotas verificadas.
3. **Evidências Visuais Geradas:**
   - `pos_limpeza_dashboard.png` (84.778 bytes)
   - `pos_limpeza_servicos.png` (75.148 bytes)
   - `pos_limpeza_profissionais.png` (73.410 bytes)
   - `pos_limpeza_estabelecimento.png` (90.126 bytes)
   - `pos_limpeza_configuracoes.png` (83.456 bytes)

---

## 6. Confirmação de Preservação e Restrições

| Diretriz / Restrição | Status | Detalhes |
| :--- | :---: | :--- |
| **VPS de Produção** | **Preservada** | Nenhuma conexão aberta com a VPS (`177.153.203.158`). |
| **Banco `alllogic_scheduler`** | **Preservado** | Verificado diretamente via conexão PostgreSQL. Contagens intactas. |
| **Arquivo `.env`** | **Preservado** | Nenhuma modificação realizada no `.env`. |
| **Código da Aplicação** | **Preservado** | Nenhum arquivo Python ou de lógica foi alterado para a limpeza. |
| **Modificações Locais Rastreadas** | **Preservadas** | `static/css/style.css` e `templates/base_admin.html` mantidos. |
| **Arquivos Não Rastreados e Documentação** | **Preservados** | Todos os relatórios em `docs/` e imagens locais preservados intactos. |
| **Git (Commit/Push/Deploy)** | **Respeitado** | Nenhum commit, push ou deploy foi realizado. |

---

## 7. Conclusão

O banco local de homologação `scheduler_test_homologacao` encontra-se devidamente limpo, sem registros residuais de testes anteriores em agendamentos, serviços ou profissionais, mantendo o painel administrativo, as credenciais e as configurações do estabelecimento 100% funcionais para a nova rodada de testes.
