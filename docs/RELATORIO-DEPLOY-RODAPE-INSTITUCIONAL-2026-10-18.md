# Relatório de Deploy — Rodapé Institucional e Comercial do Agillex Agenda

**Data:** 18/10/2026 00:08 (BRT) / 03:08 (UTC)  
**Projeto:** AllLogic Scheduler (Agillex Agenda) — `~/AllLogic/Projetos/app-agendamento`  
**Host de Produção:** Oracle Cloud Infrastructure (`136.248.113.145`)  
**Commit Publicado:** `f0d7677` (`origin/main`)  
**Status da Operação:** **DEPLOY CONCLUÍDO COM SUCESSO — TESTES DE FUMAÇA APROVADOS**

---

## 1. Objetivo da Alteração

Atender à solicitação do fundador para enriquecer o rodapé público do aplicativo de agendamento online (`agenda.alllogiconline.com.br`) com os dados oficiais de contato da **AllLogic Online** e aviso de direitos autorais:
- Linha de contato com e-mail (`contato@alllogiconline.com.br`) e telefone (`(11) 96638-1915`) como links clicáveis (`mailto:` e `tel:`).
- Linha jurídica de copyright: `© 2026 AllLogic Online. Todos os direitos reservados.`
- Preservação da chamada comercial do produto: `Agillex Agenda · Experimente grátis por 14 dias`.

---

## 2. Arquivos Modificados e Commitados

- `templates/index.html`: Atualização do rodapé na página principal de agendamento.
- `templates/sucesso.html`: Padronização do mesmo rodapé na página de confirmação de agendamento.
- `static/css/style.css`: Estilos flexbox responsivos (`.rodape-comercial-chamada`, `.rodape-institucional-contato`, `.link-institucional`, `.rodape-copy`).

**Commit local e remoto:** `f0d7677` no repositório `lucasdresler/alllogic-scheduler`.

---

## 3. Procedimento de Salvaguarda Pré-Deploy (VPS Oracle Cloud)

Antes de qualquer substituição de código ou rebuild em produção, foram gerados os seguintes artefatos de segurança:

- **Diretório de Backup:** `/opt/alllogic/backups/scheduler/pre-deploy-20261018T030708Z`
- **Dump do Banco PostgreSQL:** `alllogic_scheduler.sql` (via `matriz-postgres`)
  - Checksum: `cb89a4e35319b62bfdcb40cca4b5a694f953f1feef871f64e0b94124352b77e6`
- **Arquivos de Ambiente:** `.env` e `compose.yaml`
- **Tag Docker de Rollback Imediato:**
  - `scheduler-scheduler:rollback-783945e-20261018T030708Z`

---

## 4. Execução da Publicação

1. Sincronização do código via Git na VPS:
   `git pull origin main` (avanço rápido `783945e` → `f0d7677`).
2. Recompilação da imagem Docker:
   `docker compose build scheduler`
3. Reinicialização e recriação do container:
   `docker compose up -d --force-recreate scheduler`

---

## 5. Validação dos Testes de Fumaça (Smoke Tests)

| Endpoint | Código HTTP | Resultado |
| :--- | :---: | :--- |
| `https://agenda.alllogiconline.com.br/` | **200 OK** | Página inicial pública renderizada com novo rodapé |
| `https://agenda.alllogiconline.com.br/admin/login` | **200 OK** | Formulário de login ativo com CSRF e cookies |
| `/api/services?estabelecimento_id=1` | **200 OK** | JSON retornado com os 7 serviços ativos |
