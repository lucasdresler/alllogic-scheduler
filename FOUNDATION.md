# FOUNDATION — AllLogic Scheduler

## 1. Identidade

**Projeto:** AllLogic Scheduler
**Organização:** AllLogic
**Categoria:** Sistema de agendamento online

O AllLogic Scheduler é um projeto independente da AllLogic.

Este projeto não deve ser confundido com o projeto OfertaIA.

---

## 2. Propósito

Evoluir o aplicativo de agendamento existente para uma solução simples, profissional e comercialmente viável para pequenos negócios e empresas de bairro.

O sistema deve reduzir a complexidade do processo de agendamento e facilitar a administração da agenda pelo negócio.

---

## 3. Público Inicial

O público inicial são pequenos negócios que trabalham com atendimento mediante horário, incluindo negócios de bairro e pequenas empresas.

A solução deve priorizar:

- simplicidade;
- facilidade de uso;
- baixo atrito para implantação;
- experiência adequada para dispositivos móveis;
- recursos realmente úteis para o pequeno negócio.

---

## 4. Estado Inicial

O projeto parte de um aplicativo existente e funcional, desenvolvido originalmente com:

- Python;
- Flask;
- PostgreSQL;
- HTML;
- CSS;
- JavaScript;
- Gunicorn.

A evolução será incremental sobre essa base.

---

## 5. Direção de Evolução

A primeira meta é alcançar uma versão comercialmente utilizável do sistema de agendamento.

A evolução futura poderá incluir recursos de relacionamento com clientes e funcionalidades de CRM.

Essa evolução não deve antecipar funcionalidades que ainda não tenham sido definidas ou priorizadas.

---

## 6. Princípios

### 6.1 Simplicidade

O sistema deve ser simples para o pequeno negócio operar e para o cliente utilizar.

### 6.2 Evolução incremental

Novos recursos devem ser incorporados em etapas, mantendo o sistema funcional.

### 6.3 Preservação da produção

Alterações de desenvolvimento não devem ser realizadas diretamente no ambiente de produção.

### 6.4 Segurança dos dados

O histórico e os dados existentes devem ser preservados durante a evolução do sistema.

### 6.5 Preparação para evolução

As decisões arquiteturais devem evitar bloqueios desnecessários para futuras expansões, sem transformar a primeira versão em um sistema excessivamente complexo.

---

## 7. Escopo da Primeira Evolução

A primeira evolução deverá priorizar:

- clientes;
- agendamentos;
- serviços;
- profissionais;
- disponibilidade;
- agenda administrativa;
- dashboard;
- cancelamento e reagendamento;
- experiência de agendamento público.

A priorização e o detalhamento de cada funcionalidade serão definidos durante o planejamento das sprints.

---

## 8. Relação com Outros Projetos

O AllLogic Scheduler é um projeto independente dentro da AllLogic.

Projetos como OfertaIA e o Site Institucional da AllLogic possuem seus próprios repositórios, documentação e ciclo de desenvolvimento.

Integrações futuras entre projetos somente serão realizadas quando forem explicitamente definidas.

---

## 9. Regra de Alteração

Este documento representa os princípios fundamentais do projeto.

Mudanças estruturais ou de propósito devem ser documentadas e versionadas no Git.
