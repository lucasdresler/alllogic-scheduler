# ADR-003 — Arquitetura de Cadastro, Provisionamento e Ciclo de Vida do Teste Gratuito

**Status:** APROVADO PARA O MVP  
**Data:** 12/10/2026  
**Contexto do Projeto:** AllLogic Scheduler (`app-agendamento`)  
**Autor:** Antigravity AI Pair Programming (com base em `~/AllLogic/AGENTS.md` e `SGA/FOUNDATION.md`)

---

## 1. Contexto do Problema

O **Agillex Agenda** evoluiu para um estágio em que é necessário permitir o cadastro automatizado de novos estabelecimentos interessados em utilizar o produto por 14 dias de avaliação gratuita.

O fluxo planejado possui como destino oficial a URL:
`https://agenda.alllogiconline.com.br/agillex`

Atualmente, a aplicação opera em ambiente VPS KingHost com:
- 1 contêiner Docker da aplicação Flask/Gunicorn (`alllogic-scheduler`);
- 1 serviço PostgreSQL dedicado (`alllogic-postgres`, porta 5432 interna, porta 5433 local de homologação);
- Traefik como proxy reverso com terminação SSL automática;
- Configuração de banco único por aplicação, conforme diretriz do SGA (ADR-001).

Antes de implementar o cadastro, é mandatório avaliar as opções arquiteturais de isolamento e provisionamento, considerando segurança, complexidade operacional, escalabilidade, custos, autenticação e tempo de ativação.

---

## 2. Opções Avaliadas

### Opção A: Instância / Banco de Dados Isolado por Estabelecimento (Database-per-Tenant)

- **Descrição:** Cada novo cadastro criaria dinamicamente um novo banco de dados no PostgreSQL (ex.: `scheduler_<slug>`), executaria scripts de DDL/seed e exigiria subdomínios ou roteamento dinâmico.
- **Vantagens:**
  - Isolamento físico e lógico absoluto dos dados de cada cliente;
  - Backups e restaurações pontuais por estabelecimento (`pg_dump` isolado);
  - Descarte trivial de dados ao término de contratos.
- **Desvantagens no Contexto Atual da AllLogic:**
  - **Incompatibilidade com o SGA ADR-001:** O padrão AllLogic prevê um banco de dados próprio por aplicação, não autorizando a criação dinâmica de dezenas de bancos desordenados no cluster sem orquestração central.
  - **Complexidade Operacional Desproporcional:** O aplicativo Flask precisaria de privilégios de superusuário (`CREATEDB`) no PostgreSQL;
  - **Roteamento de Rede e DNS:** Exigiria wildcard DNS no Cloudflare e regras dinâmicas de roteamento no Traefik que não existem na VPS KingHost;
  - **Overhead de Recursos:** Gerenciamento de múltiplos pools de conexão PostgreSQL em hardware de VPS com recursos finitos;
  - **Violação do Princípio de Simplicidade:** Introduziria complexidade prematura (overengineering) expressamente vetada pelo `AGENTS.md` do projeto.

### Opção B: Multi-Tenancy Lógico com Entidade `estabelecimento` no Mesmo Banco (Row-Level Multi-Tenancy)

- **Descrição:** Criação da entidade de primeira classe `estabelecimento` no banco de dados existente. Todas as contas administrativas (`admin`) passam a ser vinculadas a um `estabelecimento_id`. O estabelecimento armazena metadados de assinatura e controle de teste (`trial_inicio`, `trial_fim`, `status`).
- **Vantagens:**
  - **Zero Atrito de Infraestrutura:** 100% compatível com a VPS, Traefik, Docker Compose e o cluster PostgreSQL atual;
  - **Ativação Instantânea e Atômica:** O cadastro do estabelecimento e de sua primeira credencial administrativa ocorre em uma única transação SQL (`BEGIN ... COMMIT`), garantindo integridade sem recursos órfãos;
  - **Preservação do Estabelecimento Piloto:** O estabelecimento padrão já existente (ID 1, "Barbearia do Bairro") é preservado sem nenhuma alteração funcional;
  - **Controle Rigoroso do Teste (14 Dias):** Datas de início e término calculadas no servidor via timestamp UTC, impedindo adulteração pelo cliente;
  - **Simplicidade e Estabilidade:** Alinhado com o princípio fundamental de preservar o que funciona e evoluir incrementalmente para o MVP.
- **Mitigações de Segurança:**
  - Isolamento das credenciais e restrição de acesso por sessão autenticada;
  - Validação estrita de unicidade de e-mail e identificadores;
  - Senhas armazenadas com hash PBKDF2/SHA256 (Werkzeug security);
  - Proteção CSRF, rate-limiting contra brute force e abuso no cadastro.

---

## 3. Decisão Arquitetural Aprovada

Adota-se a **Opção B (Multi-Tenancy Lógico Centrado na Entidade `estabelecimento`)** para o MVP do Agillex Agenda.

### Diretrizes de Implementação:

1. **Modelo de Dados do Estabelecimento:**
   - Tabela `estabelecimento`:
     - `id`: identificador sequencial único;
     - `slug`: identificador alfanumérico único para URL e identificação;
     - `nome`: razão social ou nome fantasia do estabelecimento;
     - `nome_responsavel`: nome completo da pessoa responsável;
     - `email`: e-mail comercial (chave única para login e contato);
     - `telefone`: telefone ou WhatsApp normalizado;
     - `trial_inicio`: timestamp do momento exato do cadastro;
     - `trial_fim`: timestamp calculado estritamente como `trial_inicio + INTERVAL '14 days'`;
     - `status`: estado do estabelecimento (`ativo`, `expirado`, `suspenso`);
     - `criado_em`: timestamp de criação do registro.
2. **Vínculo com Contas Administrativas:**
   - Adição da coluna `estabelecimento_id` na tabela `admin` com chave estrangeira para `estabelecimento(id)`.
   - O admin inicial do sistema é vinculado retrocompativelmente ao `estabelecimento` padrão (ID 1).
3. **Regra de Transação Atômica:**
   - A criação do estabelecimento e do respectivo administrador ocorre dentro de uma transação protegida. Em caso de qualquer falha de validação ou integridade, a transação sofre `ROLLBACK`, impedindo registros órfãos.
4. **Ciclo de Vida e Expiração do Teste:**
   - Uma verificação de validade temporal é realizada no acesso administrativo:
     Se `CURRENT_TIMESTAMP > trial_fim`, o status transita para `expirado`.
   - Quando `expirado`: o acesso às rotas administrativas operacionais é bloqueado e uma tela informativa é exibida com orientações de contato para contratação definitiva.
   - **Nenhum dado é excluído automaticamente** ao expirar, garantindo preservação do histórico do cliente.
5. **Segurança do Período de Teste:**
   - O cliente não possui nenhum controle sobre `trial_inicio`, `trial_fim` ou `status` no painel administrativo. Essas propriedades só podem ser alteradas por procedimentos autorizados da AllLogic.

---

## 4. Consequências

- **Positivas:**
  - Cadastro 100% automatizado, funcional e imediato na rota `/agillex`;
  - Sem necessidade de intervenção técnica manual para liberar os 14 dias de teste;
  - Zero risco de quebra da VPS ou do container de produção;
  - Compatibilidade total com os 48 testes automatizados existentes.
- **Limitações e Evoluções Futuras:**
  - Em versões futuras (pós-MVP e SaaS em larga escala), a arquitetura poderá evoluir para esquemas PostgreSQL dedicados ou instâncias isoladas com provisionador Kubernetes/Docker, quando o volume de clientes justificar tal investimento.
