# Relatório de Deploy — Padronização Visual e Institucional da Página de Cadastro Agillex Agenda

**Data:** 18/10/2026 10:29 (BRT) / 13:29 (UTC)  
**Projeto:** AllLogic Scheduler (Agillex Agenda) — `~/AllLogic/Projetos/app-agendamento`  
**Host de Produção:** Oracle Cloud Infrastructure (`136.248.113.145`)  
**Commit Publicado:** `8571388` (`origin/main`)  
**Status da Operação:** **DEPLOY CONCLUÍDO COM SUCESSO — TESTES DE FUMAÇA APROVADOS**

---

## 1. Objetivo da Alteração

Atender à solicitação do fundador para padronizar integralmente a página `https://agenda.alllogiconline.com.br/agillex` (página de adesão e ativação dos 14 dias de teste gratuito do Agillex Agenda), alinhando seu design visual, layout, paleta de cores, componentes e navegação aos padrões homologados do site institucional da **AllLogic Online**:

1. **Barra Superior de Utilidades (`header__services`):**
   - Links: `Encontre seu domínio | Hospede seu site` apontando para `https://alllogiconline.com.br/dominios-e-hospedagem`.
2. **Cabeçalho Principal Institucional (`header`):**
   - Logotipo oficial da AllLogic Online com fallback dinâmico.
   - Menu desktop completo: Início, Soluções, Família Agillex (com dropdown para Agillex Hub, Agillex Agenda e Agillex Atendimento), Portfólio, Diagnóstico, Sobre e Contato.
   - Menu hambúrguer mobile responsivo com animação e controle de acessibilidade (`aria-expanded`).
3. **Design System & Tipografia Inter:**
   - Adotada a fonte Google Fonts `Inter` (pesos 400, 500, 600, 700, 800) em substituição à Poppins.
   - Aplicação dos tokens oficiais da AllLogic: `--color-primary: #0a1f44`, `--color-primary-dark: #061530`, `--color-secondary: #1f6fff`, `--color-accent: #c9a227`, `--color-surface: #f4f6fa`, `--color-border: #dde3ee`.
4. **Links Jurídicos no Termo de Aceite:**
   - Transformação dos textos "termos de uso" e "política de privacidade" em hiperlinks clicáveis direcionando para `https://alllogiconline.com.br/termos-de-uso/` e `https://alllogiconline.com.br/politica-de-privacidade/` com `target="_blank"`, `rel="noopener noreferrer"` e tratamento de propagação de eventos para evitar desseleção involuntária do checkbox.
5. **Rodapé Institucional Completo (`footer`):**
   - Layout em 3 colunas: Marca e Slogan oficial ("Tecnologia que trabalha para as pessoas"), links de navegação e bloco de contato com canais diretos (E-mail, Telefone e WhatsApp Oficial).
   - Copyright oficial: `© 2026 AllLogic Online. Todos os direitos reservados.`
6. **Botão Flutuante Voltar ao Topo (`scroll-to-top`):**
   - Botão circular dourado (`#c9a227`) com seta branca centralizada (`#ffffff`), sombra suave e comportamento suave de rolagem.

---

## 2. Arquivos Modificados e Commitados

- `templates/agillex.html`: Reestruturação completa do layout incorporando a topbar, header institucional, grid de benefícios modernizado, seletor de planos interativo, formulário protegido com CSRF, rodapé institucional de 3 colunas, botão voltar ao topo e scripts vanilla.
- `static/images/logo-alllogic.png`: Adição do asset do logotipo institucional AllLogic Online nos estáticos da aplicação.

**Commit local e remoto:** `8571388` no repositório `lucasdresler/alllogic-scheduler`.

---

## 3. Salvaguarda Pré-Deploy (VPS Oracle Cloud)

Antes de aplicar a atualização em produção, foi realizado o procedimento de salvaguarda:

- **Diretório de Backup:** `/opt/alllogic/backups/scheduler/pre-deploy-20261018T132838Z`
- **Arquivos Preservados:** `.env` e `compose.yaml`

---

## 4. Execução da Publicação

1. Sincronização do repositório remoto na VPS:
   `git pull origin main` (avanço `9e729ac` → `8571388`).
2. Recompilação da imagem Docker:
   `docker compose build scheduler`
3. Recriação do container em produção:
   `docker compose up -d --force-recreate scheduler`

---

## 5. Validação dos Testes de Fumaça (Smoke Tests)

| Endpoint / Recurso | Código HTTP | Resultado |
| :--- | :---: | :--- |
| `https://agenda.alllogiconline.com.br/agillex` | **200 OK** | Página de cadastro carregada com layout institucional completo, topbar, cabeçalho, formulário e rodapé. |
| `https://agenda.alllogiconline.com.br/static/images/logo-alllogic.png` | **200 OK** | Imagem do logotipo oficial carregada com sucesso (1.48 MB PNG). |
| Aceite dos Termos de Uso e Privacidade | **Aprovado** | Links clicáveis funcionando e apontando para as URLs homologadas do site AllLogic Online. |
| Navegação e Dropdown Família Agillex | **Aprovado** | Submenu funcional tanto em desktop quanto no menu hambúrguer mobile. |
