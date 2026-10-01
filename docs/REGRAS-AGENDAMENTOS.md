# Regras de Agendamento

## Objetivo

Registrar as regras funcionais do ciclo de vida dos agendamentos na V1 Comercial do AllLogic Scheduler.

## Escopo

Este documento define as regras de status, ocupação de horários, receita prevista, preservação do histórico, cancelamento e reagendamento.

## Status do agendamento

Na V1:

- `agendado`: agendamento ativo e válido;
- `realizado`: atendimento ocorreu, definido por admin, histórico, NÃO bloqueia horário, entra em receita do período;
- `nao_compareceu`: cliente não veio, definido por admin, histórico, NÃO bloqueia horário, NÃO entra em receita;
- `cancelado`: agendamento cancelado, mantido no histórico.

## Regras de negócio

## Composição do agendamento

Na V1 Comercial, um agendamento pode conter um ou mais serviços.

As regras são:

- cada serviço selecionado pertence ao mesmo agendamento;
- a duração total do agendamento é a soma das durações dos serviços selecionados;
- o valor total do agendamento é a soma dos preços dos serviços selecionados;
- a disponibilidade deve reservar um único bloco contínuo correspondente à duração total;
- o intervalo utilizado para apresentar os horários disponíveis representa apenas a granularidade dos slots e não define a duração do agendamento;
- os serviços que compõem o agendamento devem permanecer identificáveis no histórico.

Exemplo:

Um cliente seleciona um serviço de 30 minutos e outro de 30 minutos. O agendamento ocupa um bloco contínuo de 60 minutos.

Um cliente seleciona serviços cuja duração total seja de 75 minutos. O sistema deve exigir um bloco contínuo de 75 minutos disponível.


### Agendamento ativo

Um agendamento `agendado` ocupa o horário do profissional, impede sua reutilização, compõe a agenda, compõe a receita prevista pelo valor do serviço e permanece no histórico.

### Agendamento realizado

Um agendamento `realizado` não ocupa mais o horário, permite que o horário volte a ser disponibilizado, compõe a receita do período e permanece no histórico.

O status `realizado` é atribuído exclusivamente pelo administrador, somente após a data/hora do agendamento ter passado.

### Agendamento não compareceu

Um agendamento `nao_compareceu` não ocupa mais o horário, permite que o horário volte a ser disponibilizado, NÃO compõe a receita do período e permanece no histórico.

O status `nao_compareceu` é atribuído exclusivamente pelo administrador, após a data/hora do agendamento ter passado.

### Agendamento cancelado

Um agendamento `cancelado` não ocupa mais o horário, permite que o horário volte a ser disponibilizado, não compõe a receita prevista e permanece registrado no banco e disponível no histórico.

O cancelamento não deve excluir o agendamento.

## Receita prevista

A receita prevista deve considerar somente os agendamentos com status `agendado`.

Quando um agendamento for cancelado, seu valor deve ser retirado da previsão de receita.

Exemplo: 3 agendamentos ativos de R$ 40,00 geram R$ 120,00 de previsão. Se 1 for cancelado, a previsão passa a R$ 80,00.

## Receita do período

A receita do período deve considerar os agendamentos com status `agendado` e `realizado`.

Não inclui agendamentos `cancelado` nem `nao_compareceu`.

## Disponibilidade

A disponibilidade deve considerar somente agendamentos com status `agendado`.

Agendamentos cancelados, realizados e não compareceram não devem bloquear horários.

Essa regra deve valer tanto para a consulta de disponibilidade quanto para a revalidação realizada na criação de um novo agendamento.

## Histórico

O cancelamento deve preservar o registro, incluindo cliente, serviço, profissional, data, horário, status e demais dados do agendamento.

O reagendamento deve preservar o histórico do atendimento e não destruir o registro original.

## Transições de status permitidas

| De → Para           | Permitida? | Quem  | Regra                                                                 |
|---------------------|------------|-------|-----------------------------------------------------------------------|
| agendado → realizado       | ✅         | Admin | Somente após a data/hora do agendamento ter passado                   |
| agendado → nao_compareceu  | ✅         | Admin | Após data/hora passada                                                |
| agendado → cancelado       | ✅         | Cliente (token) / Admin | A qualquer momento                                    |
| realizado → agendado       | ✅         | Admin | Correção (reabrir)                                                    |
| realizado → cancelado      | ❌         | —     | Não permitido (já ocorreu)                                            |
| nao_compareceu → agendado  | ✅         | Admin | Correção (reabrir)                                                    |
| nao_compareceu → cancelado | ❌         | —     | Não faz sentido                                                       |
| cancelado → agendado       | ✅         | Admin | Reativar (reativar reserva)                                           |
| cancelado → realizado      | ❌         | —     | Não permitido                                                         |

## Registro de origem

Coluna `status_origem` em `agendamento` (`cliente`, `admin`, `sistema`).

## Histórico de status

Tabela `agendamento_status_historico` (agendamento_id, status_anterior, status_novo, origem, usuario_id, criado_em) — a ser implementada na V1.

## Regra crítica

Sistema **NÃO** transforma automaticamente agendamento passado em `realizado` (remover `atualizar_agendamentos_realizados` do `init_db`).

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