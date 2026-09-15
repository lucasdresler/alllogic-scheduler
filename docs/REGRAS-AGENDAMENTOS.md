# Regras de Agendamento

## Objetivo

Registrar as regras funcionais do ciclo de vida dos agendamentos na V1 Comercial do AllLogic Scheduler.

## Escopo

Este documento define as regras de status, ocupação de horários, receita prevista, preservação do histórico, cancelamento e reagendamento.

## Status do agendamento

Na V1:

- `agendado`: agendamento ativo e válido;
- `cancelado`: agendamento cancelado, mantido no histórico.

## Regras de negócio

### Agendamento ativo

Um agendamento `agendado` ocupa o horário do profissional, impede sua reutilização, compõe a agenda, compõe a receita prevista pelo valor do serviço e permanece no histórico.

### Agendamento cancelado

Um agendamento `cancelado` não ocupa mais o horário, permite que o horário volte a ser disponibilizado, não compõe a receita prevista e permanece registrado no banco e disponível no histórico.

O cancelamento não deve excluir o agendamento.

## Receita prevista

A receita prevista deve considerar somente os agendamentos com status `agendado`.

Quando um agendamento for cancelado, seu valor deve ser retirado da previsão de receita.

Exemplo: 3 agendamentos ativos de R$ 40,00 geram R$ 120,00 de previsão. Se 1 for cancelado, a previsão passa a R$ 80,00.

## Disponibilidade

A disponibilidade deve considerar somente agendamentos com status `agendado`.

Agendamentos cancelados não devem bloquear horários.

Essa regra deve valer tanto para a consulta de disponibilidade quanto para a revalidação realizada na criação de um novo agendamento.

## Histórico

O cancelamento deve preservar o registro, incluindo cliente, serviço, profissional, data, horário, status e demais dados do agendamento.

## Reagendamento

O reagendamento deve preservar o histórico do atendimento e não destruir o registro original.

Os detalhes do fluxo de reagendamento serão definidos durante sua implementação, sem ampliar o escopo aprovado da V1.

## Validação

A implementação deverá verificar:

1. novo agendamento inicia como `agendado`;
2. `agendado` bloqueia horário;
3. `cancelado` libera horário;
4. `agendado` entra na receita prevista;
5. `cancelado` sai da receita prevista;
6. cancelamento preserva o registro;
7. histórico identifica o status;
8. horário liberado por cancelamento pode receber novo agendamento.

## Rollback

Alterações estruturais no banco devem ter estratégia de rollback definida antes da produção.

A produção não deve ser alterada diretamente durante o desenvolvimento.

## Boas práticas

- Preservar dados existentes.
- Não excluir agendamentos para representar cancelamento.
- Alterar somente o necessário.
- Validar localmente antes da homologação.
- Atualizar a documentação quando o comportamento for implementado.
- Versionar após validação.

## Referências

- `FOUNDATION.md`
- `AGENTS.md`
- `docs/ARQUITETURA-BANCO.md`

## Antecedência máxima para agendamento

A antecedência máxima permitida para novos agendamentos deve ser uma configuração administrável pelo estabelecimento.

Na V1:

- o valor inicial será de 14 dias;
- o administrador poderá alterar esse valor no painel administrativo;
- o limite será aplicado à data escolhida pelo cliente no agendamento público;
- datas posteriores ao limite configurado não poderão ser agendadas;
- o valor deve ser armazenado no PostgreSQL, e não definido exclusivamente no código.

Essa configuração permite que cada estabelecimento defina o horizonte de agendamento adequado à sua operação, sem necessidade de intervenção técnica.
