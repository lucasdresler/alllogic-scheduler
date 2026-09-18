# AGENTS.md

## Regras de Desenvolvimento — AllLogic Scheduler

## 1. Identidade do projeto

Nome técnico oficial:

**AllLogic Scheduler**

O AllLogic Scheduler é o sistema de agendamento online da AllLogic.

O projeto é independente dos demais projetos da AllLogic.

Não confundir este projeto com o **OfertaIA** ou com qualquer outro projeto da AllLogic.

A pasta local atual do projeto é:

`~/AllLogic/Projetos/app-agendamento/`

O repositório oficial no GitHub é:

`alllogic-scheduler`

A expressão **App de Agendamento** pode ser utilizada como descrição funcional do produto, mas o nome técnico e oficial do projeto é **AllLogic Scheduler**.


### Decisão sobre nomenclatura da pasta local

A pasta local permanece, por enquanto:

`~/AllLogic/Projetos/app-agendamento/`

A padronização futura para uma pasta local `scheduler` foi considerada, mas fica deliberadamente adiada para uma etapa posterior de organização e padronização.

A renomeação não faz parte da construção da V1 atual e não deve ser realizada durante esta etapa de evolução do produto.

---

## 2. Contexto e origem do projeto

O AllLogic Scheduler parte de uma aplicação web de agendamento que já existia e que foi originalmente desenvolvida com auxílio de outra IA.

A aplicação já possui uma versão funcional utilizada como base para evolução.

A estratégia oficial do projeto é:

**preservar o que funciona e evoluir incrementalmente.**

Não reconstruir a aplicação do zero sem uma decisão explícita que justifique essa mudança.

Não reescrever componentes funcionais sem necessidade.

As evoluções devem ser pequenas, rastreáveis, reversíveis e orientadas ao valor comercial.

---

## 3. Objetivo

O objetivo é evoluir a aplicação existente para uma solução comercial simples, profissional e adequada a pequenos negócios e empresas de bairro que trabalham com serviços mediante agendamento.

A solução deve reduzir a complexidade da organização da agenda e facilitar a administração dos atendimentos.

A simplicidade de utilização, a facilidade de implantação, a manutenção e a experiência em dispositivos móveis devem ser prioridades.

---

## 4. Público-alvo inicial

O público-alvo inicial são pequenos negócios e empresas de bairro que trabalham com serviços mediante agendamento.

O produto deve ser suficientemente simples para que um pequeno negócio consiga utilizá-lo sem depender de intervenção técnica para suas operações rotineiras.

---

## 5. Objetivo comercial da V1

A V1 deve alcançar um nível de maturidade suficiente para que a AllLogic possa começar a oferecer e vender o produto para clientes reais.

Não é necessário concluir toda a visão futura do produto antes de iniciar a comercialização.

Quando a V1 atender ao critério de saída definido neste documento, a prioridade passa a ser utilizar o produto comercialmente e evoluí-lo a partir das necessidades reais dos clientes.

O objetivo não é esperar por um produto completo ou definitivo para começar a vender.

A V1 deve ser:

* útil;
* simples;
* estável;
* profissional;
* comercializável;
* suficientemente completa para resolver o problema principal de agendamento.

---

## 6. Escopo da V1 Comercial

A V1 Comercial deve contemplar, de forma incremental:

* clientes;
* agendamentos;
* serviços;
* profissionais;
* disponibilidade;
* agenda administrativa;
* dashboard;
* experiência pública de agendamento;
* cancelamento;
* reagendamento;
* histórico de clientes;
* histórico de atendimentos.

A implementação desses recursos deve ocorrer conforme os sprints definidos para o projeto.

Nenhum recurso adicional deve ser incorporado ao escopo apenas por iniciativa do agente.

---

## 7. Funcionalidades deliberadamente adiadas

As funcionalidades abaixo não fazem parte da prioridade inicial da V1 e não devem ser antecipadas sem decisão explícita:

* pagamentos online;
* programa de fidelidade;
* campanhas de marketing;
* recursos de inteligência artificial;
* automações de WhatsApp;
* marketplace;
* controle de estoque;
* faturamento;
* múltiplas unidades;
* aplicativo mobile nativo.

Essas funcionalidades podem ser consideradas futuramente, mas não devem aumentar o escopo da V1 por iniciativa do agente.

---

## 8. Visão futura

O produto poderá evoluir futuramente para recursos relacionados a CRM e relacionamento com clientes.

Essa visão futura deve orientar decisões que precisem preservar capacidade de evolução, mas não deve justificar a implementação antecipada de funcionalidades ainda não priorizadas.

Evitar complexidade prematura.

A arquitetura deve permitir evolução futura sem obrigar o projeto a implementar antecipadamente toda a visão de longo prazo.

---

## 9. Sequência oficial de evolução

A evolução inicial do produto seguirá esta sequência:

1. Banco de dados e modelos
2. Backend e API
3. Administração
4. Agendamento público
5. Dashboard
6. UX/UI
7. Segurança
8. Homologação
9. Deploy

A sequência pode ser ajustada mediante decisão explícita quando uma dependência técnica ou comercial justificar a alteração.

---

## 10. Arquitetura funcional de referência

A visão funcional de evolução do produto é:

```text
Empresa
├── Profissionais
├── Serviços
├── Clientes
├── Agendamentos
└── Configurações
```

Essa estrutura representa uma direção funcional de evolução.

Ela não implica implementação imediata de uma arquitetura multiempresa ou SaaS.

Não implementar multi-tenancy, múltiplas unidades ou estruturas equivalentes sem definição explícita de escopo.

---

## 11. Evolução do modelo de clientes

A implementação atual armazena nome e telefone do cliente diretamente no agendamento.

A direção planejada para a evolução é criar uma entidade própria de cliente, permitindo relacionamento entre clientes e seus agendamentos.

Modelo conceitual de referência:

```text
Cliente
├── id
├── nome
├── telefone
├── email
├── observacoes
└── criado_em
        │
        │ 1:N
        ▼
Agendamento
├── cliente_id
├── servico_id
├── profissional_id
├── data
├── hora
├── status
└── demais dados do agendamento
```

Essa evolução deve preservar os agendamentos existentes.

A existência desta diretriz não autoriza, por si só, a alteração do banco.

Antes de qualquer migração devem ser definidos:

* modelo final da alteração;
* estratégia de migração;
* preservação dos dados existentes;
* validação;
* rollback;
* impacto no código existente.

Nenhum dado existente deve ser descartado como consequência de uma evolução estrutural sem autorização explícita.

---

## 12. Critério de saída da V1 Comercial

A V1 será considerada suficientemente madura para comercialização quando um pequeno negócio puder, sem intervenção técnica:

* cadastrar seus serviços;
* cadastrar seus profissionais;
* configurar sua disponibilidade;
* receber agendamentos online;
* administrar sua agenda;
* consultar seus clientes;
* consultar o histórico de atendimentos;
* cancelar agendamentos;
* reagendar atendimentos sem destruir o histórico.

O objetivo não é atingir a versão final do produto.

O objetivo é alcançar uma solução útil, estável, simples e comercializável.

---

## 13. Regra de evolução do produto

Cada evolução deve seguir o princípio:

**preservar o que funciona → evoluir incrementalmente → validar → documentar → versionar → homologar → publicar.**

Mudanças estruturais devem ser planejadas antes da implementação.

Nenhuma funcionalidade futura deve ser incorporada apenas porque faz sentido tecnicamente.

O valor comercial e a prioridade definida para o projeto devem orientar a evolução.

---

## 14. Regra de escopo

Não implementar funcionalidades que não façam parte do escopo aprovado.

Não alterar o objetivo ou a direção arquitetural do projeto sem autorização.

Não incorporar funcionalidades de outros projetos da AllLogic.

Não utilizar decisões, estruturas ou recursos do OfertaIA para ampliar o escopo do AllLogic Scheduler sem definição explícita.

---

## 15. Produção

A produção existente não deve ser modificada diretamente durante o desenvolvimento.

Alterações devem ser desenvolvidas e validadas em ambiente local ou de homologação antes de qualquer publicação.

A existência de uma aplicação atualmente em produção não autoriza alterações diretas no ambiente produtivo.

Qualquer publicação deve ocorrer somente após validação adequada.

---

## 16. Arquitetura

A arquitetura deve permitir evolução futura sem introduzir complexidade desnecessária.

Evitar overengineering.

Priorizar:

* simplicidade;
* manutenção;
* segurança;
* capacidade de evolução;
* baixo atrito operacional.

Não criar estruturas, camadas, serviços ou tecnologias apenas por antecipação de necessidades futuras.

---

## 17. Banco de dados

O padrão de banco de dados para aplicações executadas na infraestrutura VPS da AllLogic é PostgreSQL, conforme decisão registrada no ADR-001 do SGA.

A arquitetura de infraestrutura utiliza um único serviço/cluster PostgreSQL por VPS.

Cada aplicação ou instalação deve utilizar:

* banco de dados PostgreSQL próprio;
* usuário PostgreSQL próprio;
* credenciais próprias;
* acesso ao banco pela rede interna, sem exposição direta à Internet.

Alterações no modelo de dados devem ser planejadas antes da implementação.

Dados existentes devem ser preservados quando houver obrigação ou necessidade de preservação.

Qualquer migração de dados deve possuir estratégia de:

* validação;
* rollback;
* preservação dos dados;
* verificação pós-migração.

Alterações no banco devem considerar o comportamento da aplicação existente antes da mudança.

No contexto atual do protótipo do AllLogic Scheduler, não há obrigação de preservar a base de clientes ou os dados existentes do SQLite. A V1 Comercial poderá iniciar com um banco PostgreSQL novo e limpo.

Não realizar migrações destrutivas sem autorização explícita.

---

## 18. Desenvolvimento

Antes de alterar código existente, compreender seu funcionamento atual.

Não reescrever componentes funcionais sem necessidade.

Preferir alterações pequenas, rastreáveis e reversíveis.

Antes de introduzir uma alteração estrutural:

1. compreender o comportamento atual;
2. identificar impactos;
3. definir a solução;
4. validar a estratégia;
5. implementar;
6. testar;
7. documentar;
8. versionar.

---

## 19. Segurança

Não expor credenciais, senhas, tokens ou outras informações sensíveis no código ou no Git.

Não desativar mecanismos de segurança existentes sem justificativa e autorização.

Credenciais de produção devem permanecer fora do código-fonte versionado.

Configurações sensíveis devem utilizar mecanismos apropriados de configuração e ambiente.

Questões de segurança identificadas durante o levantamento devem ser registradas e tratadas dentro do escopo apropriado, sem alterações improvisadas durante outras etapas do projeto.

---

## 20. Git

Alterações significativas devem ser versionadas.

Antes de iniciar trabalho em uma sessão de desenvolvimento, verificar o estado do repositório com:

```bash
git status
```

Quando houver um repositório remoto configurado, sincronizar a branch antes do desenvolvimento conforme o fluxo definido pela AllLogic.

Não descartar alterações locais sem autorização.

Antes de alterações significativas, o estado do repositório deve estar conhecido.

Após alterações relevantes:

1. validar;
2. verificar o estado do Git;
3. revisar as alterações;
4. criar commit apropriado;
5. enviar ao repositório remoto quando aplicável.

---

## 21. Documentação

Mudanças relevantes de arquitetura, banco de dados, infraestrutura ou comportamento devem ser documentadas.

A documentação deve permanecer coerente com o estado real do projeto.

A documentação do projeto deve ser versionada junto ao código quando fizer parte do repositório.

O `AGENTS.md` registra contexto operacional, decisões e regras necessárias para orientar o desenvolvimento.

O `FOUNDATION.md` permanece como documento fundamental do projeto.

O `README.md` deve apresentar o projeto de forma adequada para consulta e entendimento geral.

Documentações específicas devem ser criadas quando a complexidade ou importância do assunto justificar.

---

## 22. Hierarquia documental

As regras gerais da AllLogic são definidas pelo:

`~/AllLogic/AGENTS.md`

As regras específicas do projeto são definidas por este documento:

`~/AllLogic/Projetos/app-agendamento/AGENTS.md`

O `FOUNDATION.md` do projeto contém seus fundamentos e princípios.

Em caso de conflito, deve ser respeitada a hierarquia de autoridade definida pela estrutura geral da AllLogic e pelos documentos fundamentais aplicáveis.

Este documento não substitui o `FOUNDATION.md` nem as regras gerais da AllLogic.

---

## 23. Agentes e IA

Agentes de IA devem analisar o projeto antes de propor alterações.

Nenhum agente deve assumir autorização para modificar arquitetura, escopo ou produção.

Quando houver dúvida sobre uma decisão estrutural, a decisão deve ser apresentada antes da implementação.

Agentes devem utilizar este documento como fonte de contexto permanente do projeto, evitando depender de informações existentes apenas em conversas anteriores.

Agentes não devem inventar decisões históricas, requisitos ou funcionalidades que não estejam documentados ou explicitamente definidos.

Quando uma decisão ainda não estiver definida, ela deve ser tratada como decisão pendente.

---

## 24. Continuidade do projeto

O contexto necessário para compreender a direção do AllLogic Scheduler deve permanecer documentado nos arquivos do próprio projeto.

Decisões relevantes não devem depender exclusivamente do histórico de conversas.

Quando uma decisão permanente de produto, arquitetura, escopo ou operação for tomada, ela deve ser registrada no documento apropriado.

O objetivo é permitir que uma nova sessão de trabalho consiga compreender o estado e a direção do projeto consultando a documentação versionada.

---

## 25. Princípio geral

Preservar o que já funciona.

Evoluir de forma incremental.

Priorizar o que gera valor comercial.

Evitar complexidade prematura.

Manter o projeto independente dos demais projetos da AllLogic.
