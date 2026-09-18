# AllLogic Scheduler — V1 Comercial

## Objetivo

Definir o escopo oficial da V1 Comercial do AllLogic Scheduler, estabelecendo o conjunto mínimo de recursos necessários para que um pequeno estabelecimento possa configurar, operar e administrar seu processo de agendamento sem intervenção técnica.

A V1 deve priorizar simplicidade, confiabilidade e uso comercial real. Funcionalidades futuras não devem ser antecipadas dentro desta versão.

## Escopo funcional da V1

### 1. Acesso administrativo
- Login administrativo.
- Alteração da senha de acesso ao painel.
- Validação da senha atual antes da alteração.
- Confirmação da nova senha.
- Armazenamento da senha somente em formato de hash.
- Sessão administrativa protegida.

### 2. Serviços
O administrador poderá:
- cadastrar serviços;
- editar serviços;
- remover serviços;
- informar preço;
- informar duração do serviço.

### 3. Profissionais
O administrador poderá:
- cadastrar profissionais;
- editar profissionais;
- ativar profissionais;
- desativar profissionais.

Profissionais desativados não devem aparecer como opção para novos agendamentos.

### 4. Horários de funcionamento
O administrador poderá definir:
- dias de funcionamento;
- horário de abertura;
- horário de fechamento;
- intervalo entre os horários disponíveis.

A disponibilidade pública deve respeitar essas configurações.

### 5. Agendamentos
A V1 deverá permitir:
- criação de agendamentos;
- visualização de agendamentos;
- cancelamento;
- reagendamento;
- preservação do histórico.

Um agendamento poderá conter um ou mais serviços.

A duração total do agendamento será a soma das durações dos serviços selecionados.

O valor total do agendamento será a soma dos preços dos serviços selecionados.

Um agendamento cancelado não deve ser apagado do banco de dados.

### 6. Histórico
O sistema deve preservar o histórico dos agendamentos.

O cancelamento deve alterar o estado do registro, e não removê-lo.

O reagendamento deve preservar a rastreabilidade do atendimento e não destruir informações históóricas.

### 7. Agenda administrativa
O administrador deverá visualizar a agenda por:
- hoje;
- semana;
- mês.

A agenda deve distinguir adequadamente os agendamentos ativos dos cancelados.

### 8. Clientes
Na V1, o sistema deverá identificar o cliente por:
- nome;
- telefone.

Também deverá ser possível consultar o histórico de agendamentos do cliente.

A evolução futura poderá utilizar uma entidade própria de cliente, mantendo a relação entre cliente e agendamentos.

### 9. Agendamento público
A área pública deverá permitir que o cliente:
1. selecione um ou mais serviços;
2. escolha o profissional, quando aplicável;
3. escolha a data;
4. visualize horários disponíveis;
5. informe seus dados;
6. confirme o agendamento.

A interface deverá ser simples e mobile-first.

### 10. Disponibilidade
O sistema deverá:
- considerar a duração total dos serviços selecionados;
- exigir um único bloco contínuo correspondente à duração total do agendamento;
- respeitar os horários de funcionamento;
- impedir conflitos de horários;
- considerar somente agendamentos ativos na ocupação dos horários;
- permitir novo agendamento em horário liberado após cancelamento.

O intervalo entre os horários disponíveis representa a granularidade dos slots e não define a duração do agendamento.

### 11. Antecedência máxima para agendamento
O período máximo permitido para novos agendamentos será configurável pelo administrador.

Na V1:
- valor inicial: 14 dias;
- o administrador poderá alterar o valor;
- o limite será aplicado ao agendamento público;
- datas posteriores ao limite configurado não poderão ser agendadas;
- a configuração será armazenada no PostgreSQL;
- o limite não será definido exclusivamente no código.

### 12. Dados básicos do estabelecimento
O administrador poderá configurar os dados básicos utilizados pelo sistema e pela área pública, incluindo:
- nome do estabelecimento;
- telefone;
- endereço, quando aplicável;
- nome apresentado na página pública.

A V1 não terá como objetivo criar um cadastro empresarial complexo.

### 13. Dashboard
O painel administrativo deverá apresentar indicadores básicos úteis à operação, incluindo informações como:
- total de agendamentos;
- receita prevista;
- visão resumida da agenda.

Os indicadores devem considerar o estado dos agendamentos. Cancelamentos não devem ser contabilizados como receita prevista ativa.

### 14. Segurança
A V1 deverá contemplar:
- autenticação administrativa;
- senha armazenada com hash;
- sessão protegida;
- validação dos dados recebidos;
- proteção das rotas administrativas;
- separação adequada entre área pública e administrativa;
- nenhuma exposição de credenciais no código versionado.

### 15. Banco de dados
O banco oficial da V1 será PostgreSQL.

A arquitetura seguirá o padrão definido para a infraestrutura AllLogic:
- PostgreSQL como serviço;
- banco lógico separado por aplicação/instalação;
- usuário PostgreSQL separado por aplicação/instalação;
- credenciais separadas;
- comunicação pela rede interna apropriada.

SQLite não será utilizado como banco oficial da V1 comercial.

### 16. Operação, backup e recuperação
A V1 deverá possuir procedimento documentado para:
- backup do banco;
- armazenamento dos backups;
- restauração;
- validação de restauração;
- recuperação em caso de falha.

A existência de backup não será considerada suficiente sem que o procedimento de restauração esteja definido e validado.

## Critérios de saída da V1

O AllLogic Scheduler poderá ser considerado V1 Comercial quando um pequeno estabelecimento conseguir, sem intervenção técnica:
1. acessar o painel administrativo;
2. alterar sua senha;
3. configurar seus dados básicos;
4. cadastrar serviços;
5. cadastrar e administrar profissionais;
6. configurar dias e horários de funcionamento;
7. definir a antecedência máxima para agendamentos;
8. receber agendamentos pela área pública;
9. visualizar sua agenda por hoje, semana e mês;
10. consultar os clientes e seu histórico;
11. cancelar agendamentos sem apagar seus registros;
12. reagendar agendamentos respeitando a disponibilidade;
13. acompanhar os indicadores básicos do dashboard;
14. operar o sistema de forma adequada em dispositivos móveis;
15. contar com procedimento de backup e recuperação documentado.

## Funcionalidades deliberadamente fora da V1

Permanecem fora do escopo da V1:
- pagamentos online;
- automações de WhatsApp;
- campanhas de marketing;
- programa de fidelidade;
- recursos de IA;
- estoque;
- emissão fiscal;
- múltiplas unidades;
- aplicativo nativo Android/iOS;
- marketplace;
- CRM completo;
- múltiplos níveis de usuários e permissões;
- relatórios financeiros avançados.

Esses recursos poderão ser avaliados em versões futuras, sem alterar o escopo aprovado da V1.

## Estratégia de entrega

A implementação deve seguir a sequência definida para o projeto:
1. banco de dados e modelos;
2. backend/API;
3. administração;
4. agendamento público;
5. dashboard;
6. UX/UI;
7. segurança;
8. homologação;
9. implantação.

Toda alteração deverá ser desenvolvida e validada fora da produção antes da publicação.

## Homologação final

Antes de considerar a V1 pronta para venda, deverá ser executado um cenário completo simulando um estabelecimento real, incluindo:
- configuração inicial;
- cadastro de serviços;
- cadastro de profissionais;
- configuração dos horários;
- configuração da antecedência máxima;
- criação de agendamentos públicos;
- operação da agenda;
- cancelamento;
- reagendamento;
- consulta de histórico;
- alteração de senha;
- validação do dashboard;
- teste em dispositivo móvel;
- backup;
- restauração do banco;
- verificação de segurança e funcionamento.

O objetivo da homologação final é validar o produto como solução comercial completa, e não apenas verificar funções isoladas.

## Princípio da V1

A V1 deve ser pequena o suficiente para ser entregue e vendida, mas completa o suficiente para resolver o problema central do pequeno estabelecimento:

**configurar seus serviços e horários, receber agendamentos online e administrar sua agenda com segurança, histórico e autonomia.**
