# AllLogic Scheduler — Plano de Finalização da V1 Comercial

## Objetivo

Registrar o planejamento aprovado para concluir, validar, documentar e publicar a V1 Comercial do AllLogic Scheduler.

A V1 deve ser pequena o suficiente para ser entregue e vendida, mas completa o suficiente para permitir que um pequeno estabelecimento configure e administre seus agendamentos com autonomia.

---

# 1. Limpeza e preparação

## 1.1 Resolver `prompts.odt`

- O arquivo histórico utilizado na criação do protótipo com a Verdent não faz parte do produto nem da documentação operacional atual.
- O arquivo será mantido fora do repositório do Scheduler.
- Registrar sua remoção no Git separadamente das alterações funcionais.

## 1.2 Revisar o estado atual

Revisar:

- `app.py`;
- `database.py`;
- `models.py`;
- templates;
- configuração;
- dependências.

Objetivo: estabelecer com precisão o que já funciona e o que ainda precisa ser implementado.

---

# 2. Banco e configurações

## 2.1 Estrutura de configurações

Criar no PostgreSQL a estrutura necessária para armazenar configurações da instalação.

Configurações iniciais:

- nome do estabelecimento;
- telefone;
- endereço;
- nome público;
- antecedência máxima para agendamento.

Valor inicial da antecedência: **14 dias**.

## 2.2 Funções de configuração

Implementar leitura e alteração das configurações pelo backend.

## 2.3 Antecedência máxima

Remover a dependência de uma regra fixa de 14 dias no código.

A regra deverá ser:

**PostgreSQL → configuração da instalação → aplicação.**

A validação deverá ocorrer no backend.

---

# 3. Configurações no Admin

Criar área de **Configurações** no painel administrativo.

## 3.1 Estabelecimento

Permitir configurar:

- nome;
- telefone;
- endereço.

## 3.2 Agendamentos

Permitir configurar:

- antecedência máxima permitida.

## 3.3 Salvamento

As alterações deverão ser persistidas no PostgreSQL e utilizadas pelo sistema sem intervenção técnica.

---

# 4. Segurança administrativa

## 4.1 Alteração de senha

Criar fluxo de:

**Alterar senha → senha atual → nova senha → confirmação.**

Regras:

- validar senha atual;
- exigir confirmação da nova senha;
- armazenar somente hash;
- invalidar imediatamente a senha anterior.

## 4.2 Validação

Testar:

- senha atual correta;
- senha atual incorreta;
- novas senhas diferentes;
- logout;
- login com senha antiga;
- login com senha nova;
- acesso direto a rotas administrativas sem autenticação.

---

# 5. Serviços

Finalizar o gerenciamento de serviços:

- cadastrar;
- editar;
- remover/desativar conforme comportamento definido;
- preço;
- duração.

Garantir que alterações não destruam informações históricas.

---

# 6. Profissionais

Finalizar:

- cadastro;
- edição;
- ativação;
- desativação.

Profissionais inativos não devem aparecer para novos agendamentos.

---

# 7. Horários de funcionamento

Garantir configuração de:

- dias de funcionamento;
- horário de abertura;
- horário de fechamento;
- intervalo dos slots.

A disponibilidade pública deverá respeitar essas configurações.

---

# 8. Disponibilidade

Validar:

- duração do serviço;
- horário de funcionamento;
- conflitos de horários;
- profissional;
- cancelamentos;
- liberação de horários após cancelamento;
- limite de antecedência.

A validação deverá existir no backend e não depender somente da interface.

---

# 9. Agendamento público

Finalizar o fluxo:

**Serviço → profissional → data → horário → dados → confirmação.**

Garantir:

- interface simples;
- abordagem mobile-first;
- validação dos dados;
- revalidação de disponibilidade no backend;
- respeito à antecedência configurada.

---

# 10. Agenda administrativa

Finalizar visualização:

- hoje;
- semana;
- mês.

Exibir adequadamente:

- horário;
- cliente;
- telefone;
- serviço;
- profissional;
- status.

---

# 11. Cancelamento

O cancelamento deverá:

- alterar o status;
- preservar o registro;
- liberar o horário;
- não contabilizar o cancelamento como receita prevista;
- manter o registro disponível no histórico.

---

# 12. Reagendamento

Implementar fluxo completo:

**Reagendar → nova data → horários disponíveis → confirmar.**

Requisitos:

- validar disponibilidade;
- impedir conflitos;
- respeitar a antecedência máxima;
- preservar o histórico;
- não apagar informações relevantes.

A forma técnica de preservar a rastreabilidade deverá ser definida durante a implementação sem introduzir complexidade desnecessária.

---

# 13. Clientes

Na V1:

- identificar por nome e telefone;
- permitir consulta do histórico de agendamentos.

Se a entidade `Cliente` ainda não estiver implementada, evoluir o modelo conforme a arquitetura documentada, preservando os dados existentes.

---

# 14. Dashboard

Finalizar indicadores básicos:

- total de agendamentos;
- receita prevista;
- resumo da agenda.

Regras:

- agendamentos ativos entram nos indicadores apropriados;
- cancelamentos não entram como receita prevista ativa.

---

# 15. Segurança e qualidade

Revisar:

- rotas administrativas;
- autenticação;
- sessões;
- validação de entradas;
- IDs inexistentes;
- datas inválidas;
- credenciais;
- dependências;
- arquivos versionados.

Nenhuma credencial deverá ser versionada.

---

# 16. Testes

Criar ou ampliar testes para:

- serviços;
- profissionais;
- disponibilidade;
- criação de agendamento;
- cancelamento;
- reagendamento;
- antecedência máxima;
- configurações;
- autenticação;
- alteração de senha.

Executar testes de regressão para garantir que funcionalidades existentes continuem funcionando.

---

# 17. Backup e recuperação

## 17.1 Backup

Documentar o procedimento oficial de backup do PostgreSQL.

## 17.2 Restauração

Documentar e executar restauração em ambiente de teste.

## 17.3 Validação

Confirmar que os dados restaurados estão íntegros e que a aplicação consegue utilizá-los.

Princípio:

**backup que nunca foi restaurado não está efetivamente homologado.**

---

# 18. Homologação comercial

Executar cenário completo simulando um estabelecimento real.

## Cenário

1. Primeiro acesso.
2. Alteração da senha.
3. Configuração do estabelecimento.
4. Cadastro de serviços.
5. Cadastro de profissionais.
6. Configuração dos horários.
7. Definição da antecedência.
8. Cliente acessa a área pública.
9. Cliente realiza agendamento.
10. Administrador visualiza o agendamento.
11. Cancelamento.
12. Liberação do horário.
13. Reagendamento.
14. Preservação do histórico.
15. Atualização do dashboard.
16. Teste em dispositivo móvel.
17. Backup.
18. Restauração.
19. Revisão de segurança.

O objetivo é validar o produto como solução comercial completa, não apenas verificar funções isoladas.

---

# 19. Documentação

Depois que o comportamento estiver implementado e validado:

- atualizar `docs/REGRAS-AGENDAMENTOS.md`;
- atualizar documentação técnica;
- atualizar documentação operacional;
- registrar configurações;
- registrar backup e recuperação;
- registrar comportamento de cancelamento e reagendamento.

A documentação deve refletir o comportamento realmente implementado e homologado.

---

# 20. Git

Para cada bloco significativo:

**validar → `git diff` → `git diff --check` → commit → push.**

Manter alterações rastreáveis e separadas por finalidade.

---

# 21. Homologação do ambiente

Após a V1 estar pronta localmente:

**Local → homologação → validação → produção.**

Não publicar diretamente em produção sem validação prévia.

---

# 22. Publicação

Somente após homologação:

1. atualizar servidor;
2. atualizar aplicação;
3. aplicar estrutura/configuração PostgreSQL;
4. rebuild/restart;
5. validar HTTPS;
6. validar domínio;
7. testar login;
8. testar área pública;
9. testar Admin;
10. testar cancelamento;
11. testar reagendamento.

URL oficial:

`agenda.alllogiconline.com.br`

O antigo `agenda.alllogic.com.br` permanece descartado.

---

# 23. Teste como produto comercial

Pergunta final:

> **Eu consigo entregar isso para uma barbearia ou outro pequeno negócio amanhã e o responsável consegue operar sozinho?**

Se a resposta for sim, a V1 está pronta.

A partir daí, o Scheduler deverá ser colocado em uso comercial e as necessidades dos primeiros clientes poderão orientar a V2.

---

# Ordem prática de execução

1. Resolver `prompts.odt`.
2. Revisar estado atual do código.
3. Implementar configurações PostgreSQL.
4. Implementar Configurações no Admin.
5. Aplicar antecedência máxima no agendamento público.
6. Implementar alteração de senha.
7. Finalizar estabelecimento.
8. Finalizar serviços.
9. Finalizar profissionais.
10. Finalizar horários.
11. Finalizar disponibilidade.
12. Finalizar agenda.
13. Finalizar cancelamento.
14. Implementar reagendamento.
15. Finalizar clientes e histórico.
16. Finalizar dashboard.
17. Executar revisão de segurança.
18. Criar/ampliar testes.
19. Implementar e validar backup/restauração.
20. Executar homologação comercial.
21. Atualizar documentação.
22. Versionar com Git.
23. Homologar ambiente.
24. Publicar.
25. Homologar em produção.
26. Liberar para venda.

---

## Critério final

A V1 Comercial será considerada concluída quando o pequeno estabelecimento conseguir, sem intervenção técnica:

- configurar seus dados;
- administrar serviços e profissionais;
- configurar horários;
- definir a antecedência máxima;
- receber agendamentos online;
- administrar sua agenda;
- cancelar e reagendar;
- consultar histórico;
- alterar sua senha;
- acompanhar indicadores básicos;
- operar adequadamente em dispositivos móveis;
- contar com backup e recuperação documentados e validados.

**Objetivo final: colocar o AllLogic Scheduler no mercado sem esperar pela visão futura de CRM.**
