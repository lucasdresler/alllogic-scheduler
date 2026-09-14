# Infraestrutura — AllLogic Scheduler

## Objetivo

Registrar o estado da infraestrutura remota destinada ao AllLogic Scheduler e os componentes existentes que deverão ser considerados durante a implantação.

## Servidor

- Provedor: KingHost
- IP público: `177.153.203.158`
- Hostname: `topcia.vps-kinghost.net`
- Sistema operacional: Ubuntu 24.04.4 LTS
- Kernel: Linux 6.8.0-136-generic
- Arquitetura: x86-64
- Virtualização: Xen
- Hardware virtualizado: HVM domU
- CPU: 2 vCPUs
- Processador: Intel Xeon Silver 4514Y
- Memória: 3,8 GiB
- Swap: 1 GiB
- Disco raiz: 67 GB
- Espaço utilizado no inventário: aproximadamente 7%
- Espaço livre no inventário: aproximadamente 60 GB

## Firewall

- UFW está ativo.
- Política padrão de entrada: deny.
- Política padrão de saída: allow.
- Política padrão de roteamento: deny.
- Logging: low.
- Regra explicitamente identificada: SSH TCP 22 permitido para IPv4 e IPv6.
- Não foram identificadas regras públicas específicas para a aplicação Scheduler.

## Docker

- Docker instalado e operacional.
- Docker: 29.6.2
- Docker Compose: v5.3.1
- A infraestrutura Docker existente utiliza a rede compartilhada `proxy`.
- Não é necessário instalar Docker para o Scheduler.
- Não deve ser criada outra rede pública para substituir `proxy`.

## Containers existentes

- `traefik` — imagem `traefik:v3.6.1` — ativo.
- `whoami` — imagem `traefik/whoami:v1.11.0` — ativo.

## Rede Docker `proxy`

- Tipo: bridge.
- Subnet: `172.18.0.0/16`.
- Gateway: `172.18.0.1`.
- Traefik: `172.18.0.2`.
- whoami: `172.18.0.3`.
- IPv6 desabilitado.

## Traefik

- Projeto localizado em `/opt/alllogic/stacks/traefik`.
- Arquivo Compose: `/opt/alllogic/stacks/traefik/compose.yaml`.
- Portas públicas: TCP 80 e TCP 443.
- Dashboard habilitado.
- Provider Docker habilitado.
- `exposedbydefault=false`.
- HTTP redirecionado para HTTPS.
- Let's Encrypt configurado com desafio HTTP.
- Armazenamento ACME: `/letsencrypt/acme.json`.
- Nível de log: INFO.

### Volumes do Traefik

- `/opt/alllogic/stacks/traefik/letsencrypt` → `/letsencrypt` (rw).
- `/var/run/docker.sock` → `/var/run/docker.sock` (ro).

## Portas identificadas

- TCP 22 — SSH.
- TCP 80 — Traefik / Docker proxy.
- TCP 443 — Traefik / Docker proxy.
- DNS local em `127.0.0.53` e `127.0.0.54`.

## Serviços do sistema

O inventário identificou 49 unidades systemd habilitadas, incluindo componentes relacionados a Docker, containerd, UFW e atualizações automáticas.

## Diretriz de implantação do Scheduler

A implantação do AllLogic Scheduler deverá utilizar a infraestrutura Docker existente e a rede compartilhada `proxy`.

- O container da aplicação não deverá publicar sua porta diretamente na Internet.
- O Traefik deverá realizar o roteamento HTTPS para o Scheduler.
- O domínio oficial definido para o Scheduler é `agenda.alllogiconline.com.br`.
- O acesso externo deverá utilizar HTTPS.
- O Scheduler deverá possuir seu próprio banco PostgreSQL lógico e seu próprio usuário PostgreSQL.
- O PostgreSQL deverá permanecer em rede interna, sem exposição direta à Internet.
- A implantação deverá respeitar o padrão PostgreSQL definido pela AllLogic.

## PostgreSQL

A arquitetura oficial para aplicações AllLogic em VPS utiliza um serviço/cluster PostgreSQL por VPS, com isolamento lógico entre aplicações.

Para o AllLogic Scheduler:

- Banco de dados próprio.
- Usuário PostgreSQL próprio.
- Credenciais próprias.
- Acesso por rede interna.
- Sem exposição da porta PostgreSQL à Internet.

## Estado de manutenção

No momento do inventário, o servidor informou aproximadamente 48 atualizações disponíveis e necessidade de reinicialização.

Essas atualizações e a reinicialização devem ser tratadas como atividade separada de manutenção de infraestrutura e não devem ser executadas como parte automática da implantação do Scheduler.

## Data do inventário

14/09/2026

## Observações

- O servidor KingHost `177.153.203.158` é o servidor destinado ao AllLogic Scheduler.
- O servidor `177.104.163.165` pertence à infraestrutura do site institucional da AllLogic e não deve ser utilizado para o Scheduler.
- O ambiente existente de Traefik e a rede `proxy` deverão ser preservados.
- O Scheduler deverá ser homologado antes da publicação definitiva em produção.

## Referências

- SGA/02-Governanca/adr/ADR-001-padrao-postgresql-vps.md
- SGA/03-Infraestrutura/arquitetura/padrao-postgresql-vps.md
- Projeto AllLogic Scheduler — `FOUNDATION.md`
- Projeto AllLogic Scheduler — `AGENTS.md`
- Projeto AllLogic Scheduler — `docs/ARQUITETURA-BANCO.md`
- Projeto AllLogic Scheduler — `docs/AMBIENTE-DESENVOLVIMENTO.md`
