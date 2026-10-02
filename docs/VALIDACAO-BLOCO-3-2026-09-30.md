# Homologação Técnica do Bloco 3 — 2026-09-30

## Classificação geral

**NÃO APTO PARA VERSIONAMENTO.** Foram encontrados defeitos funcionais no fluxo público e na aplicação de configurações, além de lacunas de preservação histórica. Não houve alteração de código durante esta homologação.

## Escopo e procedimentos

Documentos consultados: este relatório antes da atualização, `ESPECIFICACAO-V1-CONSOLIDADA.md`, `MATRIZ-RECURSOS-VERSOES.md` e `docs/REGRAS-AGENDAMENTOS.md`.

Revisados o estado do working tree, `git diff --stat`, `git diff --check`, o diff rastreado completo e os arquivos novos de templates. Os quatro arquivos históricos untracked e os documentos de especificação existentes foram preservados sem alteração. Nenhum commit, push, reset ou restore foi executado.

## Testes executados

| Teste | Resultado |
|---|---|
| `python -m compileall .` (execução anterior registrada) | **PASSOU** — compilação sintática Python sem erros. |
| `python -m pytest -q` | **NÃO TESTADO** — pytest informou `no tests ran`; o projeto não contém suíte automatizada detectável. |
| Análise dos 11 templates com Jinja `Environment.get_template` | **PASSOU** — todos os templates foram analisados sem erro. |
| `git diff --check` | **PASSOU** — sem erros de whitespace no diff rastreado. |
| Exercícios de rotas, persistência e fluxos com PostgreSQL | **NÃO TESTADO** — `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SECRET_KEY` e `ADMIN_SENHA_INICIAL` estavam ausentes. Não foi feita conexão nem mutação de banco. |

Não foi possível executar testes direcionados de integração porque não existe fixture/suíte no projeto e não há ambiente de banco configurado. As falhas abaixo foram identificadas pela inspeção dos caminhos efetivamente chamados pelo código, não apresentadas como resultados de execução ponta a ponta.

## Matriz de homologação

| Área / critério | Classificação | Resultado da revisão |
|---|---|---|
| Serviços: listagem, criação, edição, ativação/desativação | **PASSOU COM RESSALVA** | Rotas, funções de modelo, validação de nome/preço/duração positiva e formulários existem; comportamento de banco não foi executado. O campo `descrição` previsto na especificação não existe no modelo/tela. |
| Serviço inativo fora do fluxo público | **FALHOU** | A listagem pública esconde inativos, mas endpoints de disponibilidade/criação aceitam IDs existentes sem validar `ativo`. |
| Serviço utilizado preservado no histórico | **FALHOU** | Não há exclusão física na interface, mas nome/preço/duração históricos são lidos da linha atual de `servico`; `agendamento_servico` guarda somente IDs, sem snapshot. |
| Profissionais: listagem, criação, edição, ativação/desativação e nome | **PASSOU COM RESSALVA** | Operações e validação de nome estão presentes; não foram exercitadas contra banco. |
| Profissional inativo fora de novos agendamentos | **FALHOU** | A listagem pública filtra ativos, mas disponibilidade e criação validam existência, não o estado ativo. |
| Histórico após edição de profissional | **FALHOU** | Consultas históricas obtêm `profissional_nome` da tabela atual; não há snapshot de nome no agendamento. |
| Relação profissional × serviço: criar/remover e cardinalidade N:M | **PASSOU COM RESSALVA** | A tabela de junção, chave composta, operações de associação e remoção estão presentes e suportam múltiplos serviços/profissionais; não houve teste de persistência. As operações de criação/edição do profissional e vínculo são transações separadas, podendo deixar alteração parcial em caso de vínculo inválido. |
| Profissional incompatível não aparece; compatível aparece | **FALHOU** | `index.html` apresenta todos os profissionais ativos sem filtrar os serviços escolhidos. O endpoint pode retornar zero horários para incompatível, mas a opção continua selecionável e não atende ao critério de filtragem. |
| Disponibilidade: dia, slots, duração, profissional, serviço e conflitos | **PASSOU COM RESSALVA** | A lógica existente verifica dia da semana, duração em slots contínuos, vínculo e conflitos `agendado`; não houve execução com banco. Também não verifica serviço/profissional ativo e pode oferecer slot cujo término ultrapassa o fechamento quando duração não é múltipla do intervalo. |
| Antecedência máxima | **FALHOU** | O backend tem regra de limite, mas alterações administrativas não limpam o cache `lru_cache` do modelo; o processo mantém valores anteriores após salvar. O calendário público também não usa os dias de funcionamento configurados e ignora domingo por regra fixa. |
| Configurações administrativas aplicadas no fluxo público | **FALHOU** | A tela persiste valores, porém o cache do modelo não é invalidado. Validação limita-se a conversão para inteiro; intervalo zero/negativo, dias fora de 0–6 e horários incoerentes podem ser salvos e causar indisponibilidade, erro ou loop na geração de slots. |
| Fluxo administrativo completo até publicação | **NÃO TESTADO** | Sem banco de homologação; não foi possível simular persistência de serviço, profissional, vínculo e configuração até a página pública. A filtragem por compatibilidade já falha na revisão estática. |
| Fluxo público completo e criação de agendamento | **NÃO TESTADO** | Sem banco; não foi possível simular POST e confirmação. Revisão estática encontrou aceitação de IDs inativos e ausência de snapshots. |
| Login, logout e alteração de senha | **PASSOU COM RESSALVA** | Caminhos existentes não foram alterados no diff; execução/regressão não testada por falta de banco e configuração de segredo. |
| Dashboard | **PASSOU COM RESSALVA** | Rota e template preservam a estrutura existente e recebem atalhos novos; renderização com dados reais não testada. |
| Cancelamento existente | **PASSOU COM RESSALVA** | A rota autenticada e atualização para `cancelado` permanecem; teste de persistência/liberação do horário não executado. |
| CSRF e rate limiting | **PASSOU COM RESSALVA** | CSRF está aplicado às rotas/formulários admin e limite de login permanece configurado; não foi possível executar teste HTTP de regressão. |
| Regras de status da Fase 2 | **PASSOU COM RESSALVA** | O diff não altera as regras existentes de status; teste funcional não executado. |
| Schema, relações, índices e migração | **PASSOU COM RESSALVA** | O diff do Bloco 3 não altera `database.py` nem introduz migração destrutiva. O schema existente define PK composta e FKs em `profissional_servico`; não há índice secundário declarado para consultas por profissional/data. O estado real do banco não foi inspecionado. |

## Falhas encontradas

1. **IDs inativos aceitos no agendamento público**
	- Arquivos: `app.py`, `models.py`.
	- Comportamento: `/api/appointments` e `/api/availability` aceitam serviço/profissional existente mesmo inativo.
	- Causa provável: verificação de existência sem validar `ativo` em `api_appointments` e `horarios_disponiveis`.
	- Impacto: contorno da interface pública permite criar reservas para ofertas/profissionais desativados.
	- Correção necessária: validar status ativo no backend para disponibilidade e criação, revalidando no caminho de gravação.

2. **Profissional não filtrado pelos serviços selecionados**
	- Arquivos: `templates/index.html`, `app.py`.
	- Comportamento: todos os profissionais ativos são exibidos após a seleção de serviços.
	- Causa provável: renderização da lista antes da seleção não consulta a relação profissional-serviço.
	- Impacto: usuário pode selecionar profissional incompatível e chegar a uma lista vazia de horários.
	- Correção necessária: filtrar dinamicamente profissionais pela interseção dos serviços selecionados, preservando validação no servidor.

3. **Configurações persistidas não atualizam o cache em execução**
	- Arquivos: `app.py`, `models.py`.
	- Comportamento: mudanças salvas podem não afetar disponibilidade até reiniciar o processo.
	- Causa provável: a rota salva configurações sem chamar `_limpar_cache_config()`.
	- Impacto: dias, horários, intervalo e antecedência exibidos/aceitos divergem do que o administrador acabou de configurar.
	- Correção necessária: invalidar o cache após gravação e validar limites, formato/ordem de horários, dias 0–6 e intervalo estritamente positivo.

4. **Calendário público ignora os dias configurados**
	- Arquivos: `templates/index.html`, `static/js/agendamento.js`.
	- Comportamento: o frontend remove domingo fixamente e não recebe `dias_funcionamento`; a quantidade de datas geradas também não equivale necessariamente ao horizonte máximo em dias corridos.
	- Causa provável: calendário baseado em regra fixa no JavaScript, enquanto o backend usa configuração do banco.
	- Impacto: datas válidas podem não aparecer; datas inválidas podem ser exibidas e depois rejeitadas pelo servidor.
	- Correção necessária: gerar/apresentar datas usando configuração real e respeitar o limite corrido; manter validação backend.

5. **Histórico não preserva snapshots dos serviços/profissional**
	- Arquivos: `database.py` (schema existente), `models.py`.
	- Comportamento: alteração de serviço muda preço, duração e nome apresentados para reservas antigas; alteração de profissional muda o nome histórico apresentado.
	- Causa provável: junções históricas leem valores atuais; `agendamento_servico` não contém `preco_unitario`/`duracao_minutos` e `agendamento` não contém snapshot do nome do profissional.
	- Impacto: histórico e valores de reservas passadas deixam de representar o momento da contratação; alteração de duração também muda o cálculo de ocupação histórica.
	- Correção necessária: criar migração não destrutiva e gravar/consultar snapshots no momento da reserva, preservando registros existentes.

6. **Validação insuficiente das configurações operacionais**
	- Arquivo: `app.py`.
	- Comportamento: entradas inteiras sintaticamente válidas, mas fora do domínio (por exemplo intervalo zero ou dia 7), são aceitas.
	- Causa provável: validação somente com `int()`.
	- Impacto: intervalo zero pode impedir a progressão do loop que gera slots; configurações inválidas podem interromper consultas ou produzir agenda incoerente.
	- Correção necessária: validar limites e invariantes no backend antes de persistir.

7. **CRUD de serviço não inclui descrição prevista**
	- Arquivos: `models.py`, `templates/admin_servico_form.html`; schema em `database.py`.
	- Comportamento: não é possível cadastrar/editar descrição do serviço.
	- Causa provável: campo não existe no modelo/schema/formulário.
	- Impacto: requisito de serviço indicado na especificação V1 não é atendido.
	- Correção necessária: definir e implementar campo e migração de forma compatível, se mantido como requisito do escopo homologado.

## Banco de dados

Nenhuma alteração de schema foi introduzida no diff do Bloco 3; nenhum comando foi executado contra PostgreSQL. O schema versionado existente define `profissional_servico` com PK composta e FKs com `ON DELETE CASCADE`, e tabelas de associação de agendamento com chaves/FKs. Não foi identificada migração destrutiva no código revisado. Integridade dos dados reais não foi testada. Os snapshots de preço/duração exigidos pela especificação estão ausentes; índices secundários relevantes para agenda não estão declarados no schema revisado.

## Regressões

**Não foi possível confirmar regressão de execução** por falta de ambiente PostgreSQL e credenciais de teste. Login/logout, alteração de senha, dashboard, cancelamento, CSRF, rate limiting e regras de status permanecem sem teste funcional. As falhas listadas são defeitos/gaps do comportamento atual encontrados por inspeção; não foram atribuídas sem evidência a este diff como regressões novas.

## Conclusão

**NÃO APTO PARA VERSIONAMENTO.** Resolver as falhas funcionais e executar nova homologação com banco isolado, cobrindo os fluxos administrativos e públicos, antes de considerar o Bloco 3 aprovado. Não foi iniciado o Bloco 4.

## Reteste após correções — 2026-10-01

Esta seção complementa e substitui a classificação inicial acima para o código retestado. O Bloco 4 não foi iniciado.

### Correções verificadas

- APIs de disponibilidade e criação rejeitam serviços e profissionais inativos; a camada de domínio também revalida estado, vínculo com todos os serviços e disponibilidade antes de gravar.
- A seleção pública consulta profissionais compatíveis com todos os serviços escolhidos. O calendário recebe os dias configurados e limita as datas pelo horizonte corrido de antecedência; o backend aplica a mesma convenção `0=domingo`.
- Configurações têm validação de intervalo, antecedência, dias únicos entre 0 e 6, formato e ordem dos horários. A gravação incrementa uma geração compartilhada no PostgreSQL; cada worker observa a nova geração e descarta seu cache local.
- Novos agendamentos gravam nome/preço/duração dos serviços e nome do profissional. Consultas históricas usam os snapshots, com fallback para registros sem snapshot.
- CRUD administrativo de serviços inclui descrição.
- A inicialização aplica migração aditiva e idempotente para descrição, snapshots e índice `(profissional_id, data, status)`. Valores de snapshots existentes não são sobrescritos; associações legadas recebem preenchimento somente quando os snapshots estão ausentes. Nenhuma coluna ou registro é removido.
- Foi adicionada suíte de integração condicionada a `SCHEDULER_TEST_DATABASE=1`, host loopback e nome de banco `scheduler_test_*`. O ambiente usado foi PostgreSQL 17 descartável em Docker, sem volume persistente, publicado somente em loopback. O `.env` do projeto não foi carregado.

### Testes executados

| Teste | Resultado |
|---|---|
| `python -m compileall -q app.py models.py database.py tests` | **PASSOU** — sem erros de compilação. |
| `python -m pytest -q` com PostgreSQL isolado | **PASSOU** — 3 testes de integração. |
| Fluxos HTTP no `Flask.test_client` | **PASSOU** — login válido/inválido, proteção admin, CSRF, CRUD com descrição, persistência e rejeição de configurações inválidas. |
| APIs e persistência PostgreSQL | **PASSOU** — serviço/profissional inativos, compatibilidade N:M, disponibilidade, criação e snapshots após alteração de serviço e profissional. |
| Migração em banco legado isolado | **PASSOU** — adicionou colunas/índice, preservou registro e snapshots já existentes e foi executada novamente sem sobrescrever os snapshots. |
| Cache de configuração entre workers simulados | **PASSOU** — a geração mudou após salvar e um cache independente carregou a configuração atualizada. |
| Navegador local em `127.0.0.1:5017` | **PASSOU** — com dois serviços selecionados, somente o profissional compatível foi exibido; o calendário apresentou exclusivamente as sextas configuradas dentro do horizonte. |
| `node --check static/js/agendamento.js` | **PASSOU** — sem erros de sintaxe. |
| `git diff --check` | **PASSOU** — sem erros de whitespace no diff rastreado. |
| Diagnósticos dos módulos Python alterados | **PASSOU** — nenhum erro reportado. |

### Limitações e pendências

- Snapshots verdadeiros de agendamentos anteriores à migração não podem ser reconstruídos se serviço ou profissional já tiver sido alterado. A migração preenche campos ausentes com os valores disponíveis no banco no momento da execução; esses valores legados podem não representar o valor histórico original.
- A validação foi feita em banco descartável, não em cópia de produção. Não foram acessados nem alterados banco, arquivos ou serviços de produção; deploy, commit e push não foram executados.
- Configurações persistidas existentes foram preservadas sem reinterpretação destrutiva. Como a implementação anterior usava numeração diferente da legenda `0=domingo`, instalações existentes devem revisar os dias configurados em homologação antes de qualquer publicação.
- Não houve teste de concorrência com múltiplos processos Gunicorn reais; a invalidação entre processos foi verificada por geração compartilhada e cache independente em teste.

## Classificação final

**APTO PARA VERSIONAMENTO DO BLOCO 3, COM AS LIMITAÇÕES ACIMA REGISTRADAS.** A migração é aditiva e não destrutiva; a homologação funcional local passou. Esta classificação não autoriza deploy. Não foi criado commit nem executado push.
