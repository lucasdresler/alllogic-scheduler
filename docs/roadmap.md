# Roadmap do AllLogic Scheduler

O roadmap organiza a evolução do AllLogic Scheduler por marcos. Ele registra o estado atual do projeto, as entregas concluídas, o trabalho em andamento, as pendências e a próxima etapa de execução, permitindo recuperar a continuidade do projeto sem depender do histórico da conversa.

## Marco 1 — Fundação do Projeto

**Status: ✔ Concluído**

- Definição do AllLogic Scheduler como projeto independente.
- Definição do objetivo comercial da V1.
- Criação e organização da documentação fundamental.
- Definição do escopo da V1 Comercial.
- Definição da arquitetura inicial e da estratégia de evolução incremental.
- Repositório Git configurado e publicado.

## Marco 2 — Infraestrutura e Banco de Dados

**Status: ✔ Concluído**

- PostgreSQL definido como banco de dados alvo.
- Banco e usuário próprios por instalação.
- Rede interna `allLogic-internal`.
- Aplicação preparada para PostgreSQL.
- Criação da tabela `agendamento_servico`.
- Migração da relação legada de serviço único.
- Inicialização e validação do PostgreSQL concluídas.
- Consultas de agendamentos existentes validadas.

## Marco 3 — Múltiplos Serviços por Agendamento

**Status: ✔ Implementado e validado**

- Um agendamento pode conter um ou mais serviços.
- Duração total é a soma das durações dos serviços.
- Valor total é a soma dos valores dos serviços.
- A disponibilidade reserva um bloco contínuo pela duração total.
- O intervalo dos horários é apenas a granularidade da agenda.
- Backend, APIs e persistência adaptados.
- Seleção múltipla implementada no frontend.
- Resumo do agendamento adaptado.
- Disponibilidade com múltiplos serviços validada.
- Criação de agendamento com múltiplos serviços validada.
- Bloqueio contínuo da agenda validado.

## Marco 4 — Interface e Fluxo Comercial da V1

**Status: 🚧 Em andamento**

### Já realizado

- Seleção múltipla de serviços.
- Texto da etapa atualizado para indicar a seleção de um ou mais serviços.
- Envio de múltiplos serviços pelo frontend.
- Cálculo e apresentação do valor total no resumo.

### Próximas etapas

- Revisar `templates/sucesso.html` para múltiplos serviços.
- Revisar `templates/admin_dashboard.html` para múltiplos serviços.
- Validar o fluxo completo pela interface.
- Verificar referências restantes ao modelo de serviço único nas telas e fluxos.

## Marco 5 — Recursos Comerciais da V1

**Status: 🚧 Em andamento**

Escopo:

- Clientes.
- Serviços.
- Profissionais.
- Disponibilidade.
- Agenda administrativa.
- Agendamento público.
- Cancelamento.
- Reagendamento.
- Histórico de clientes.
- Histórico de atendimentos.
- Dashboard administrativo.
- Configuração do estabelecimento.
- Logo do estabelecimento.

### Próximas etapas

- Implementar/validar gerenciamento da logo do estabelecimento.
- Validar o fluxo comercial completo.
- Verificar preservação do histórico em cancelamentos e reagendamentos.
- Confirmar operação sem intervenção técnica.

## Marco 6 — Segurança e Homologação da V1

**Status: ⏳ Pendente**

- Revisão de segurança.
- Validação de autenticação e autorização.
- Validação de entradas e tratamento de erros.
- Validação de cancelamento e reagendamento.
- Homologação funcional completa.
- Registro dos resultados.
- Correção de eventuais problemas.
- Auditoria técnica final.

## Marco 7 — Documentação e Versionamento da V1

**Status: ⏳ Pendente**

- Atualizar documentação com o comportamento implementado.
- Atualizar este roadmap.
- Registrar decisões relevantes.
- Revisar o repositório.
- Executar validações finais.
- Revisar `git diff`.
- Executar `git diff --check`.
- Criar commit da V1.
- Enviar ao repositório remoto.

## Marco 8 — Homologação e Publicação

**Status: ⏳ Pendente**

- Atualizar ambiente de homologação.
- Validar a versão candidata.
- Realizar backup conforme procedimento.
- Publicar a versão homologada.
- Validar produção.
- Confirmar `agenda.alllogiconline.com.br`.
- Registrar a publicação e o estado final da V1.

## Direção futura

Funcionalidades reservadas para evolução posterior à V1:

- Pagamentos.
- Fidelidade.
- Marketing.
- IA.
- Automações de WhatsApp.
- Marketplace.
- Estoque.
- Faturamento.
- Múltiplas unidades.
- Aplicativos móveis nativos.
- Evolução futura para recursos de CRM.

## Estado atual

**Marco:** Marco 4 — Interface e Fluxo Comercial da V1.

**Próxima ação:** revisar `templates/sucesso.html` e `templates/admin_dashboard.html` para validar a apresentação de múltiplos serviços.

## Regra de atualização

Este roadmap deve ser atualizado quando um marco relevante for concluído, uma pendência for resolvida, uma nova etapa começar ou uma decisão aprovada alterar o caminho da V1.

O documento deve refletir o estado real do projeto. Uma entrega só deve ser marcada como concluída após implementação e validação.
