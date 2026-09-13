# Arquitetura de Banco de Dados — AllLogic Scheduler

## Objetivo

Registrar a arquitetura de banco de dados definida para o AllLogic Scheduler e distinguir o estado atual do protótipo do estado-alvo da V1 Comercial.

## Estado atual

O protótipo existente utiliza SQLite por meio do arquivo local `barbearia.db`.

A implementação atual possui acesso ao banco diretamente pelo módulo `database.py`.

O SQLite pertence ao estado legado do protótipo e não representa o padrão definitivo de banco de dados para execução do Scheduler na infraestrutura VPS da AllLogic.

## Estado-alvo

O AllLogic Scheduler utilizará PostgreSQL como banco de dados oficial quando integrado à infraestrutura VPS da AllLogic.

A arquitetura seguirá o padrão definido no SGA:

- um único serviço/cluster PostgreSQL por VPS;
- um banco PostgreSQL próprio para cada aplicação ou instalação;
- um usuário PostgreSQL próprio para cada banco;
- credenciais próprias para cada aplicação;
- acesso ao banco pela rede interna;
- PostgreSQL sem exposição direta à Internet.

## Banco do AllLogic Scheduler

Cada instalação do AllLogic Scheduler deverá possuir seu próprio banco PostgreSQL.

O nome definitivo do banco e do usuário PostgreSQL será definido durante a implementação da infraestrutura da aplicação.

Credenciais reais não devem ser registradas neste documento nem em arquivos versionados.

## Dados do protótipo

O protótipo atual não possui uma base de clientes que precise ser preservada para a V1 Comercial.

Os dados atualmente existentes no SQLite também não constituem obrigação de preservação para a evolução da V1.

A implementação PostgreSQL poderá, portanto, iniciar com um banco novo e limpo.

Essa decisão é específica para o estado atual do projeto e não representa autorização geral para descarte de dados em outros contextos.

## Estratégia de evolução

A substituição do SQLite por PostgreSQL deverá ocorrer durante a evolução técnica do Scheduler.

A implementação deverá:

1. substituir a camada de acesso SQLite por acesso PostgreSQL;
2. adaptar o modelo de dados ao PostgreSQL;
3. validar criação e consulta dos dados;
4. validar as regras de negócio existentes;
5. validar o comportamento da aplicação;
6. documentar a configuração necessária;
7. somente depois avançar para homologação e implantação.

## Referências

- `FOUNDATION.md`
- `AGENTS.md`
- `README.md`
- `SGA/02-Governanca/adr/ADR-001-padrao-postgresql-vps.md`
- `SGA/03-Infraestrutura/arquitetura/padrao-postgresql-vps.md`
