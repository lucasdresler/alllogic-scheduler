# Preservação de Código — Provisionamento Automatizado, Multi-Tenant e Trial de 14 Dias

**Data de Preservação:** 12 de Outubro de 2026  
**Status:** Preservado para Decisão Futura (Decisões 1, 4 e 5 da AllLogic)

---

## 1. Motivação e Contexto

Durante o ciclo de desenvolvimento do AllLogic Scheduler (Agillex Agenda), foram implementadas as funcionalidades de:
- Cadastro automatizado de estabelecimentos e criação atômica de contas administrativas;
- Controle do ciclo de vida de 14 dias de avaliação gratuita (trial com datas de início e término inalteráveis pelo cliente);
- Interceptação de expiração de trial e tela informativa de renovação comercial;
- Modelagem de tabela `estabelecimento` e coluna `admin.estabelecimento_id`.

### Diretrizes de Separação para Produção:
1. **Decisão 1:** A rota `/agillex` e sua interface de auto-cadastro não serão disponibilizadas nesta publicação, pois o aplicativo em produção atende a uma instalação operacional dedicada.
2. **Decisão 4:** O código de cadastro, provisionamento e trial **não foi descartado**, ficando integralmente preservado neste diretório.
3. **Decisão 5:** A tabela `estabelecimento`, a coluna `admin.estabelecimento_id` e alterações de esquema relacionadas não devem ser introduzidas em produção sem necessidade comprovada, evitando um **multi-tenancy parcial** que daria a entender que os dados estão isolados quando as tabelas operacionais (`agendamento`, `servico`, `profissional`) ainda não possuem chave de tenant.

---

## 2. Conteúdo Deste Pacote de Preservação

| Arquivo | Descrição |
| :--- | :--- |
| `database_extension.py` | Schema DDL completo da tabela `estabelecimento`, FK em `admin`, migração de retrocompatibilidade e funções auxiliares (`gerar_slug`, `criar_estabelecimento_com_admin`, `verificar_status_trial`, `obter_admin_com_estabelecimento`). |
| `routes_agillex.py` | Implementação completa da rota `GET/POST /agillex` com rate limiting (5 POST/min), validação rigorosa, proteção anti-duplicidade, hashing e rota `/admin/trial-expirado`. |
| `templates/agillex.html` | Template Jinja2 comercial com apresentação dos benefícios e formulário de cadastro responsivo. |
| `templates/admin_trial_expirado.html` | Template Jinja2 informativo exibido após o término do período de 14 dias, com garantias de preservação integral dos dados e links comerciais para reativação. |
| `tests/test_cadastro_agillex.py` | Suíte completa com 9 testes automatizados no Pytest cobrindo validações, cálculo exato de 14 dias, criação atômica, anti-duplicidade e comportamento pós-expiração. |

---

## 3. Como Reativar no Futuro

Quando a AllLogic decidir avançar para uma plataforma multi-tenant real ou SaaS centralizado:

1. **Evolução do Schema:** Além de reintroduzir `estabelecimento` e `admin.estabelecimento_id`, adicionar `estabelecimento_id INTEGER REFERENCES estabelecimento(id)` também nas tabelas `agendamento`, `servico`, `profissional` e `profissional_disponibilidade`, garantindo isolamento relacional completo de ponta a ponta.
2. **Integração das Rotas:** Importar `routes_agillex.py` e acoplar no `app.py`.
3. **Templates e Testes:** Mover os templates de volta para `templates/` e os testes para `tests/`.
4. **Execução dos Testes:** Executar `pytest tests/test_cadastro_agillex.py` para revalidar a suíte.
