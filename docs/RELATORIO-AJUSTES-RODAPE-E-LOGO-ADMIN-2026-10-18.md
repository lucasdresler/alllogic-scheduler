# Relatório de Deploy — Alinhamento de Cabeçalho, Logo no Rodapé Admin e Dropup Família Agillex

**Data:** 18/10/2026 10:45 (BRT) / 13:45 (UTC)  
**Projeto:** AllLogic Scheduler (Agillex Agenda) — `~/AllLogic/Projetos/app-agendamento` e Site Institucional (`~/AllLogic/Site`)  
**Hosts de Produção:**
- Oracle Cloud VPS (`136.248.113.145`) — Agillex Agenda
- cPanel HostGator (`177.104.163.165:21008`) — Site Institucional AllLogic Online  
**Commits Publicados:**
- `lucasdresler/alllogic-scheduler`: `0505fca`
- `lucasdresler/alllogic-site`: `11bf863`  
**Status da Operação:** **DEPLOY CONCLUÍDO COM SUCESSO — TESTES DE FUMAÇA APROVADOS EM AMBOS OS AMBIENTES**

---

## 1. Escopo das Alterações Executadas

1. **Rodapé Institucional — Família Agillex como Dropdown / Dropup:**
   - No site institucional (`Site/`):
     - `src/content/navigation.ts`: Agrupados os três produtos sob `{ label: "Família Agillex", children: [...] }` na lista do rodapé.
     - `src/components/navigation/Footer.astro`: Implementada renderização com detecção de `children`, gerando botão interativo com ícone chevron e menu flutuante *dropup* com links para Agillex Hub, Agillex Agenda e Agillex Atendimento. Adicionado script de alternância acessível (`aria-expanded`).
     - `src/components/navigation/footer.css`: Estilizados o botão e o submenu suspenso para cima (evitando transbordo da página) com tokens do Design System AllLogic.
   - Na página de cadastro do Agillex Agenda (`Projetos/app-agendamento/templates/agillex.html`):
     - Substituídos os três links avulsos pelo mesmo componente *dropup* `Família Agillex` com estilos equivalentes e evento de clique/toque.

2. **Alinhamento do Menu Principal na URL `/agillex`:**
   - Em `templates/agillex.html`:
     - O container `.header__container` foi corrigido de `max-width: 1200px` para `max-width: 1024px; padding: 0 1rem;`, alinhando sua largura e margens com exatidão ao container padrão `<Container size="lg">` utilizado no site institucional.
     - A altura da logo no cabeçalho `.header__logo img` foi ajustada para `72px`, idêntica ao site institucional.
     - O container do rodapé `.footer__container` foi igualmente padronizado para `max-width: 1024px; padding: 0 1rem;`.

3. **Logotipo da AllLogic Online no Rodapé do Painel Administrativo:**
   - Em `templates/base_admin.html`:
     - Inserido bloco `.admin-footer-left` no rodapé do painel administrativo, contendo o logotipo oficial da AllLogic Online com link para `https://alllogiconline.com.br` e fallback automático.
   - Em `static/css/style.css`:
     - Criados os estilos responsivos para `.admin-footer-left`, `.admin-footer-logo-link` e `.admin-footer-logo` (altura 38px, alinhamento flexível e hover suave).

---

## 2. Validações e Testes de Fumaça

| Ambiente / Endpoint | Código HTTP | Resultado |
| :--- | :---: | :--- |
| `https://alllogiconline.com.br/` | **200 OK** | Rodapé atualizado com *dropup* "Família Agillex ▾" funcional e interativo. |
| `https://agenda.alllogiconline.com.br/agillex` | **200 OK** | Cabeçalho e rodapé alinhados em 1024px, idênticos ao site institucional; dropup funcional. |
| `https://agenda.alllogiconline.com.br/admin` | **200 OK** | Rodapé do painel com logotipo oficial AllLogic Online no lado esquerdo. |
| Integridade do Endpoint PHP de Diagnóstico | **Preservado** | `public/api/diagnosis.php` comparado e mantido intacto. |
