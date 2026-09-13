# Ambiente de Desenvolvimento — AllLogic Scheduler

## Objetivo

Registrar a estrutura de PostgreSQL utilizada pelo AllLogic Scheduler durante o desenvolvimento e a homologação local.

## Finalidade

O PostgreSQL deste ambiente existe para permitir o desenvolvimento e a validação da aplicação antes de sua integração com a infraestrutura VPS da AllLogic.

Este ambiente não representa, por si só, a configuração definitiva de produção.

## Isolamento

O PostgreSQL do AllLogic Scheduler deve permanecer independente dos demais projetos.

O ambiente não deve utilizar o container, volume, banco ou usuário PostgreSQL pertencentes ao OfertaIA.

## Estrutura

O ambiente deverá utilizar:

- PostgreSQL em container Docker;
- volume persistente próprio;
- banco PostgreSQL próprio para o Scheduler;
- usuário PostgreSQL próprio;
- rede Docker própria ou definida pelo ambiente de desenvolvimento;
- credenciais fornecidas por configuração de ambiente e não registradas no Git.

## Produção

A infraestrutura de produção deverá seguir o padrão PostgreSQL definido pelo SGA:

- um único serviço/cluster PostgreSQL por VPS;
- banco próprio para cada aplicação ou instalação;
- usuário próprio para cada banco;
- credenciais próprias;
- acesso pela rede interna;
- PostgreSQL sem exposição direta à Internet.

## Relação com o protótipo

O protótipo atual utiliza SQLite por meio do arquivo `barbearia.db`.

A evolução para PostgreSQL será realizada no ambiente de desenvolvimento/homologação antes de qualquer implantação.

Como definido em `docs/ARQUITETURA-BANCO.md`, a V1 Comercial poderá iniciar com um banco PostgreSQL novo e limpo.

## Segurança

Credenciais reais não devem ser registradas neste documento, no código-fonte ou em arquivos versionados.

## Referências

- `FOUNDATION.md`
- `AGENTS.md`
- `README.md`
- `docs/ARQUITETURA-BANCO.md`
- `SGA/02-Governanca/adr/ADR-001-padrao-postgresql-vps.md`
- `SGA/03-Infraestrutura/arquitetura/padrao-postgresql-vps.md`
