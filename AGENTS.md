AGENTS.md

Regras de Desenvolvimento — App de Agendamento

Identidade do projeto

Este projeto é o App de Agendamento da AllLogic.

O App de Agendamento é um projeto independente.

Não confundir este projeto com o OfertaIA ou com qualquer outro projeto da AllLogic.

Objetivo

O objetivo inicial é evoluir uma aplicação web de agendamento para uma solução comercial simples, profissional e adequada a pequenos negócios e empresas de bairro.

A evolução deve ocorrer de forma incremental.

Regra de escopo

Não implementar funcionalidades que não façam parte do escopo aprovado.

Não alterar o objetivo ou a direção arquitetural do projeto sem autorização.

Não incorporar funcionalidades de outros projetos da AllLogic.

Produção

A produção existente não deve ser modificada diretamente durante o desenvolvimento.

Alterações devem ser desenvolvidas e validadas em ambiente local ou de homologação antes de qualquer publicação.

Arquitetura

A arquitetura deve permitir evolução futura sem introduzir complexidade desnecessária.

Evitar overengineering.

Priorizar simplicidade, manutenção, segurança e capacidade de evolução.

Banco de dados

Alterações no modelo de dados devem ser planejadas antes da implementação.

Dados existentes devem ser preservados.

Qualquer migração de dados deve possuir estratégia de validação e rollback.

Desenvolvimento

Antes de alterar código existente, compreender seu funcionamento atual.

Não reescrever componentes funcionais sem necessidade.

Preferir alterações pequenas, rastreáveis e reversíveis.

Segurança

Não expor credenciais, senhas, tokens ou outras informações sensíveis no código ou no Git.

Não desativar mecanismos de segurança existentes sem justificativa e autorização.

Git

Alterações significativas devem ser versionadas.

Antes de iniciar trabalho em uma sessão de desenvolvimento, verificar o estado do repositório com:

git status

Quando houver um repositório remoto configurado, sincronizar a branch antes do desenvolvimento conforme o fluxo definido pela AllLogic.

Documentação

Mudanças relevantes de arquitetura, banco de dados, infraestrutura ou comportamento devem ser documentadas.

A documentação deve permanecer coerente com o estado real do projeto.

Agentes e IA

Agentes de IA devem analisar o projeto antes de propor alterações.

Nenhum agente deve assumir autorização para modificar arquitetura, escopo ou produção.

Quando houver dúvida sobre uma decisão estrutural, a decisão deve ser apresentada antes da implementação.

Princípio geral

Preservar o que já funciona.

Evoluir de forma incremental.

Priorizar o que gera valor comercial.

Evitar complexidade prematura.

Manter o projeto independente dos demais projetos da AllLogic.
