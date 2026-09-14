# DNS — AllLogic Scheduler

## Objetivo

Registrar as informações de DNS identificadas para a publicação do AllLogic Scheduler.

## Domínio

- Domínio: `alllogiconline.com.br`
- Provedor DNS autoritativo: Cloudflare

## Nameservers

O domínio utiliza os seguintes nameservers autoritativos:

- `ada.ns.cloudflare.com`
- `kip.ns.cloudflare.com`

## Estado atual do domínio

O registro A do domínio raiz `alllogiconline.com.br` está publicado e atualmente resolve para:

- `172.67.177.234`
- `104.21.59.134`

Esses endereços correspondem à publicação do domínio através da infraestrutura da Cloudflare.

## Subdomínio do Scheduler

O domínio oficial definido para o AllLogic Scheduler é:

`agenda.alllogiconline.com.br`

No levantamento realizado em 14/09/2026, o subdomínio ainda não possuía registro A público.

Consulta realizada:

```text
dig A agenda.alllogiconline.com.br +short
```

Resultado:

```text
(nenhum resultado)
```

## Próxima configuração prevista

Para a homologação do Scheduler, deverá ser criado no DNS da Cloudflare um registro:

- Tipo: `A`
- Nome: `agenda`
- IPv4: `177.153.203.158`

A configuração inicial prevista é utilizar `DNS only` para validar primeiro a resolução direta do subdomínio para o servidor KingHost.

Após a validação da resolução DNS e da conectividade com o servidor, a configuração de proxy da Cloudflare poderá ser avaliada conforme a arquitetura de publicação definida.

## Validação

Após a criação do registro, a resolução deverá ser validada com:

```text
dig A agenda.alllogiconline.com.br +short
```

O resultado esperado é:

```text
177.153.203.158
```

## Data do levantamento

14/09/2026

## Referências

- Projeto AllLogic Scheduler — `AGENTS.md`
- Projeto AllLogic Scheduler — `docs/INFRAESTRUTURA.md`
- Cloudflare — DNS do domínio `alllogiconline.com.br`
