# MATRIZ DE RECURSOS — 3 VERSÕES COMERCIAIS DO ALLLOGIC SCHEDULER

---

## 1. PRINCÍPIOS NORTEADORES

| Princípio | Descrição |
|-----------|-----------|
| **Experiência do cliente idêntica** | As 3 versões oferecem EXATAMENTE a mesma experiência para o cliente final (agendamento público, cancelamento próprio, visualização de reserva). |
| **Diferenciação apenas administrativa** | A separação entre versões ocorre exclusivamente nos recursos disponíveis no painel administrativo. |
| **Nenhum recurso inventado** | Não criar funcionalidades "premium" artificiais apenas para preencher a matriz. |
| **Sem billing/assinatura na V1** | Não implementar cobrança, trials, planos ou feature gating técnico agora. Apenas documentar a distribuição planejada. |
| **Base = V1 Comercial** | A versão **Básica** corresponde ao escopo mínimo da V1 Comercial definido em `ESPECIFICACAO-V1-CONSOLIDADA.md` e `docs/AllLogic-Scheduler-V1-Comercial.md`. |
| **Evolução incremental** | Recursos das versões Intermediária e Avançada podem ser desenvolvidos após a V1, conforme prioridade comercial. |

---

## 2. NÚCLEO COMUM (EXPERIÊNCIA DO CLIENTE — TODAS AS VERSÕES)

| Área | Recurso | Status V1 | Observação |
|------|---------|-----------|------------|
| **Agendamento Público** | Seleção de múltiplos serviços | ✅ Implementado | Soma de duração e preço |
| | Escolha de profissional | ✅ Implementado | Filtro por serviços do profissional (Fase 2) |
| | Escolha de data (respeita dias/horário/antecedência) | ✅ Implementado | Validação backend + frontend |
| | Visualização de horários disponíveis (slots contínuos) | ✅ Implementado | Considera duração total |
| | Informar nome + telefone | ✅ Implementado | Buscar cliente existente por telefone (Fase 3) |
| | Confirmação com resumo completo | ✅ Implementado | |
| **Gestão Própria da Reserva** | Acesso via token único (`/reserva/<token>`) | 🔄 Fase 5 | UUID imprevisível, rota pública sem login |
| | Visualizar detalhes da reserva | 🔄 Fase 5 | |
| | Cancelar própria reserva | 🔄 Fase 5 | Registra origem `cliente` |
| | Receber link/token na confirmação | 🔄 Fase 5 | Exibido em `sucesso.html` |
| **Regras de Negócio** | Disponibilidade (funcionamento, profissional, conflitos, antecedência) | ✅ Implementado | Backend valida tudo |
| | Snapshot imutável de preço/duração no agendamento | 🔄 Fase 2 | Colunas em `agendamento_servico` |
| | 4 status: agendado, realizado, não compareceu, cancelado | 🔄 Fase 2/4 | Transições definidas em `ESPECIFICACAO-V1-CONSOLIDADA.md §2.6` |
| | Histórico preservado em cancelamento/reagendamento | ✅ Regra definida | Implementação Fase 4/5 |
| **UX/Mobile** | Interface mobile-first, responsiva | 🔄 Fase 7 | |
| | Acessibilidade básica | 🔄 Fase 7 | |

> **Regra imutável:** Nenhum recurso acima varia entre versões. O cliente final **não percebe** qual versão o estabelecimento contratou.

---

## 3. RECURSOS ADMINISTRATIVOS — NÚCLEO V1 (VERSÃO BÁSICA)

> Estes recursos compõem o **mínimo comercializável** (critério de saída da V1 em `AGENTS.md §12`). A versão **Básica** entrega **todos** estes itens.

| Módulo | Recurso Administrativo | Status Atual | Fase Prevista |
|--------|------------------------|--------------|---------------|
| **Autenticação** | Login / Logout admin | ✅ Implementado | Fase 1 |
| | Alteração de senha (obrigatória 1º acesso, valida atual, hash) | ✅ Implementado | Fase 1 |
| | Proteção rotas (`@login_requerido`) | ✅ Implementado | Fase 1 |
| **Dashboard** | Abas: Hoje / Semana / Mês | ✅ Implementado | Fase 1/4 |
| | Indicadores: Total agendamentos, Receita prevista, Receita do período | 🔄 Parcial (corrigir cálculo) | Fase 4 |
| | Breakdown por status (agendado, realizado, não compareceu, cancelado) | ❌ | Fase 4 |
| | Tabela de agendamentos com status visível | ✅ Implementado | Fase 1/4 |
| **Serviços (CRUD)** | Listar serviços (admin) | ❌ | Fase 4 |
| | Criar serviço (nome, descrição, preço, duração, ativo) | ❌ | Fase 4 |
| | Editar serviço (todos os campos) | ❌ | Fase 4 |
| | Ativar / Desativar serviço | ❌ (coluna `ativo` faltando) | Fase 2 |
| | **Regra**: Alteração de preço/duração NÃO afeta agendamentos passados (snapshot) | 🔄 Fase 2 | Colunas em `agendamento_servico` |
| **Profissionais (CRUD)** | Listar profissionais (admin) | ❌ | Fase 4 |
| | Criar profissional (nome, ativo) | ❌ | Fase 4 |
| | Editar profissional (nome) | ❌ | Fase 4 |
| | Ativar / Desativar profissional | ❌ | Fase 4 |
| | Vincular/desvincular serviços (N:M via `profissional_servico`) | ❌ (tabela faltando) | Fase 2 |
| **Clientes (CRUD + Histórico)** | Listar clientes | ❌ (tabela `cliente` não existe) | Fase 3/4 |
| | Buscar cliente (nome/telefone) | ❌ | Fase 3/4 |
| | Ver histórico de agendamentos do cliente | ❌ | Fase 3/4 |
| | Migração dados legados (agrupar agendamentos por nome+telefone) | ❌ | Fase 3 |
| **Configurações do Estabelecimento** | Tela única consolidada: Identificação, Contato, Endereço, Identidade Visual, Funcionamento, Agendamento, Conta | ❌ (tabela `estabelecimento` não existe) | Fase 6 |
| | **Identificação**: nome interno, nome público, descrição | ❌ | Fase 6 |
| | **Contato**: telefone, WhatsApp, email | ❌ | Fase 6 |
| | **Endereço**: CEP, logradouro, número, complemento, bairro, cidade, estado | ❌ | Fase 6 |
| | **Identidade Visual**: Upload/remoção logo + exibição pública | ❌ | Fase 6 |
| | **Funcionamento**: dias, horário abertura/fechamento, intervalo slots | ✅ Em `configuracao` (migrar) | Fase 6 |
| | **Agendamento**: antecedência máxima (dias) | ✅ Em `configuracao` (migrar) | Fase 6 |
| | **Conta**: Alteração senha admin (já existe) | ✅ | Fase 1 |
| **Cancelamento** | Botão "Cancelar" na tabela do dashboard + modal confirmação | 🔄 Backend existe | Fase 4 |
| | Registro de origem (`status_origem`: cliente/admin/sistema) | ❌ | Fase 4 |
| | Entrada em `agendamento_status_historico` | ❌ | Fase 5 |
| **Reagendamento** | Fluxo admin: selecionar → nova data/horário → validar disponibilidade → confirmar | ❌ | Fase 5 |
| | Preservar status atual (não criar status "reagendado") | 🔄 Regra definida | Fase 5 |
| | Histórico em `agendamento_reagendamento` (data/hora anterior/nova, usuário) | ❌ | Fase 5 |
| | Permitir troca de profissional (validar disponibilidade) | 🔄 Decisão pendente | Fase 5 |
| **Segurança Core (V1)** | SECRET_KEY obrigatória (sem fallback) | ✅ | Fase 1 |
| | ADMIN_SENHA_INICIAL obrigatória | ✅ | Fase 1 |
| | CSRF protection (Flask-WTF) | 🔄 | Fase 2 |
| | Rate limiting login (Flask-Limiter) | 🔄 | Fase 2 |
| | Lock concorrência agendamento (advisory lock) | 🔄 | Fase 2 |
| | Validação entrada backend | 🔄 Parcial | Fase 2 |
| | Token acesso cliente (UUID + rota `/reserva/<token>`) | 🔄 | Fase 5 |
| **Backup/Recuperação** | Scripts backup/restore PostgreSQL documentados + validados | ❌ | Fase 9 |
| | Procedimentos operacionais documentados | ❌ | Fase 9 |

---

## 4. DISTRIBUIÇÃO PROPOSTA ENTRE VERSÕES

| Categoria | Recurso Administrativo | **Básica** (V1 Mínimo) | **Intermediária** | **Avançada** | Observação / Decisão Pendente |
|-----------|------------------------|:----------------------:|:-----------------:|:------------:|-------------------------------|
| **AUTENTICAÇÃO E ACESSO** | | | | | |
| | Login/Logout + alteração senha | ✅ | ✅ | ✅ | Núcleo obrigatório |
| | **Múltiplos usuários admin** (perfis/permissões) | ❌ | ❌ | 🟡 | Fora do escopo V1 (AGENTS.md §7). Avaliar pós-V1. |
| | **Recuperação de senha (e-mail)** | ❌ | ❌ | 🟡 | Fora do escopo V1. Requer infra de e-mail. |
| | **2FA / MFA** | ❌ | ❌ | 🟡 | Fora do escopo V1. |
| **DASHBOARD E INDICADORES** | | | | | |
| | Abas Hoje/Semana/Mês | ✅ | ✅ | ✅ | |
| | Indicadores básicos (total, receita prevista, receita período) | ✅ | ✅ | ✅ | |
| | Breakdown por status (4 status) | ✅ | ✅ | ✅ | Fase 4 |
| | **Indicadores avançados**: Taxa ocupação, ticket médio, no-show rate | ❌ | 🟡 | ✅ | **Decisão comercial**: definir quais métricas. |
| | **Filtros avançados** (período custom, profissional, serviço, status) | ❌ | 🟡 | ✅ | |
| | **Exportação CSV/PDF** (agenda, clientes, financeiro) | ❌ | 🟡 | ✅ | |
| | **Gráficos/visualizações** (semana/mês, comparação períodos) | ❌ | ❌ | 🟡 | |
| | **Dashboard personalizável** (widgets, layout) | ❌ | ❌ | 🟡 | |
| **SERVIÇOS** | | | | | |
| | CRUD completo (criar, editar, ativar/desativar, listar) | ✅ | ✅ | ✅ | |
| | Snapshot preço/duração imutável | ✅ | ✅ | ✅ | |
| | **Categorias/grupos de serviços** | ❌ | 🟡 | ✅ | Útil p/ negócios c/ muitos serviços. |
| | **Preços por profissional** (mesmo serviço, preço diferente) | ❌ | ❌ | 🟡 | Complexo; avaliar demanda real. |
| | **Promoções/descontos temporários** | ❌ | ❌ | 🟡 | Fora V1 (marketing). |
| | **Pacotes/combos de serviços** | ❌ | ❌ | 🟡 | Fora V1. |
| **PROFISSIONAIS** | | | | | |
| | CRUD completo + vincular serviços | ✅ | ✅ | ✅ | |
| | **Agenda individual por profissional** (visualização separada) | ❌ | ✅ | ✅ | Necessário p/ múltiplos profissionais. |
| | **Disponibilidade individual por profissional** (horários próprios) | ❌ | 🟡 | ✅ | **Decisão comercial**: V1 usa horário global do estabelecimento. |
| | **Comissão por profissional/serviço** | ❌ | ❌ | 🟡 | Fora V1 (folha/financeiro). |
| | **Bloqueios de agenda** (férias, folga, indisponibilidade pontual) | ❌ | 🟡 | ✅ | **Decisão comercial**: essencial p/ múltiplos profissionais. |
| **CLIENTES** | | | | | |
| | CRUD + histórico agendamentos | ✅ | ✅ | ✅ | |
| | **Ficha completa** (observações, preferências, tags) | ❌ | 🟡 | ✅ | Base p/ CRM futuro. |
| | **Importação/exportação clientes (CSV)** | ❌ | 🟡 | ✅ | |
| | **Busca avançada** (por telefone, nome, último agendamento, valor) | ❌ | 🟡 | ✅ | |
| | **Histórico de comunicação** (WhatsApp, e-mail, SMS) | ❌ | ❌ | 🟡 | Fora V1 (integrações). |
| | **Programa de fidelidade/pontos** | ❌ | ❌ | ❌ | Fora V1 (AGENTS.md §7). |
| **CONFIGURAÇÕES ESTABELECIMENTO** | | | | | |
| | Tela única consolidada (todas as seções) | ✅ | ✅ | ✅ | Fase 6 |
| | **Múltiplas unidades/filiais** | ❌ | ❌ | ❌ | Fora V1 (AGENTS.md §7). |
| | **Customização visual avançada** (cores, fontes, banner, galeria) | ❌ | ❌ | 🟡 | Fora V1. |
| | **Domínio próprio / subdomínio personalizado** | ❌ | ❌ | 🟡 | Infra/Deploy. |
| **CANCELAMENTO** | | | | | |
| | Cancelar pelo admin (botão + modal + origem) | ✅ | ✅ | ✅ | |
| | Cancelar pelo cliente (token) | ✅ | ✅ | ✅ | |
| | **Política de cancelamento** (prazo mínimo, taxa, regras por serviço) | ❌ | 🟡 | ✅ | **Decisão comercial**: definir modelo. |
| | **Lista de espera** (notificar quando vaga abrir) | ❌ | ❌ | 🟡 | |
| **REAGENDAMENTO** | | | | | |
| | Reagendamento admin (fluxo completo + histórico) | ✅ | ✅ | ✅ | Fase 5 |
| | **Reagendamento pelo cliente** (via token) | ❌ | 🟡 | ✅ | **Decisão comercial**: V1 = apenas admin. |
| | **Regras de reagendamento** (antecedência mínima, limite de vezes) | ❌ | 🟡 | ✅ | |
| **COMUNICAÇÃO / NOTIFICAÇÕES** | | | | | |
| | **Confirmação automática (WhatsApp/SMS/E-mail)** | ❌ | 🟡 | ✅ | **Decisão comercial**: canal, provedor, custo. |
| | **Lembrete automático** (24h, 2h antes) | ❌ | 🟡 | ✅ | Reduz no-show. |
| | **Notificação de cancelamento/reagendamento** | ❌ | 🟡 | ✅ | |
| | **Campanhas/comunicações em massa** | ❌ | ❌ | ❌ | Fora V1 (marketing). |
| **RELATÓRIOS E EXPORTAÇÃO** | | | | | |
| | Exportação agenda (CSV) | ❌ | ✅ | ✅ | |
| | Exportação clientes (CSV) | ❌ | ✅ | ✅ | |
| | Exportação financeira (receita por período/serviço/profissional) | ❌ | 🟡 | ✅ | |
| | **Relatórios gerenciais** (PDF, agendados, KPIs) | ❌ | ❌ | 🟡 | |
| | **API de integração** (webhooks, endpoints p/ sistemas externos) | ❌ | ❌ | 🟡 | |
| **BACKUP E SEGURANÇA** | | | | | |
| | Backup/restore documentado + validado | ✅ | ✅ | ✅ | Fase 9 |
| | **Backup automático agendado** (rotina) | ❌ | 🟡 | ✅ | Infra/Deploy. |
| | **Logs de auditoria** (ações admin: quem fez o quê, quando) | ❌ | 🟡 | ✅ | LGPD/Compliance. |
| | **LGPD: Exclusão/anonimização dados cliente** | ❌ | 🟡 | ✅ | Obrigatoriedade legal. |
| **SUPORTE E ONBOARDING** | | | | | |
| | Documentação de uso (manual do admin) | ✅ | ✅ | ✅ | |
| | **Onboarding guiado** (wizard primeira configuração) | ❌ | 🟡 | ✅ | Reduz atrito inicial. |
| | **Suporte prioritário / SLA** | ❌ | ❌ | 🟡 | Comercial, não técnico. |

---

## 5. LEGENDA E CONVENÇÕES

| Símbolo | Significado |
|---------|-------------|
| ✅ | **Incluso** — recurso faz parte da versão |
| ❌ | **Não incluso** — recurso não faz parte da versão |
| 🟡 | **Condicional / Decisão Pendente** — inclusão depende de decisão comercial explícita (ver §6) |
| **Negrito** | Recurso que **não existe hoje** e requer desenvolvimento |
| *Itálico* | Recurso que **já existe ou está em implementação** nas fases atuais |

> **Nota:** A coluna **Básica** reflete o **escopo contratual da V1 Comercial**. As colunas Intermediária e Avançada representam **direção de evolução pós-V1**, não compromisso de entrega imediata.

---

## 6. PONTOS QUE PRECISAM DE DECISÃO DO PROPRIETÁRIO

| # | Tema | Pergunta / Decisão Necessária | Impacto na Matriz |
|---|------|-------------------------------|-------------------|
| 1 | **Disponibilidade individual por profissional** | V1 usa horário global do estabelecimento. Permitir horários próprios por profissional na Intermediária/Avançada? | Afeta: Profissionais → Disponibilidade individual; Bloqueios de agenda |
| 2 | **Reagendamento pelo cliente** | V1 = apenas admin. Liberar para cliente na Intermediária? | Afeta: Reagendamento → Reagendamento pelo cliente |
| 3 | **Política de cancelamento** | Definir: prazo mínimo, taxa, regras por serviço? Automatizar cobrança? | Afeta: Cancelamento → Política de cancelamento; Lista de espera |
| 4 | **Notificações automáticas** | Quais canais (WhatsApp, SMS, E-mail)? Provedor? Custo por disparo? Quem paga? | Afeta: Comunicação → Confirmação, Lembrete, Notificação cancelamento |
| 5 | **Múltiplos usuários admin / permissões** | Necessário na V1? Se não, em qual versão introduzir? | Afeta: Autenticação → Múltiplos usuários admin |
| 6 | **Bloqueios de agenda (férias/folga)** | Essencial para negócios com >1 profissional. Incluir na Intermediária? | Afeta: Profissionais → Bloqueios de agenda |
| 7 | **Exportação/Relatórios** | Quais formatos (CSV, PDF, XLSX)? Quais relatórios prioritários? | Afeta: Relatórios → Exportação, Relatórios gerenciais |
| 8 | **LGPD / Exclusão de dados** | Implementar na Intermediária ou apenas Avançada? Obrigatoriedade legal. | Afeta: Backup e Segurança → LGPD |
| 9 | **Logs de auditoria** | Nível de detalhe? Retenção? Interface para visualização? | Afeta: Backup e Segurança → Logs de auditoria |
| 10 | **Onboarding guiado** | Wizard de primeira configuração reduz atrito. Prioridade? | Afeta: Suporte → Onboarding guiado |
| 11 | **Nomes comerciais definitivos** | "Básica / Intermediária / Avançada" são provisórios. Definir nomes finais. | Afeta: Todo material comercial e documentação |
| 12 | **Estratégia de precificação** | Definir preços por versão para validar se a matriz faz sentido comercial. | Afeta: Viabilidade de cada tier |

---

## 7. CONFLITOS E PONTOS INDEFINIDOS NA ESPECIFICAÇÃO ATUAL

| # | Conflito / Ponto Indefinido | Onde Aparece | Ação Necessária |
|---|----------------------------|--------------|-----------------|
| 1 | **Migração cliente: duplicatas (mesmo telefone, nomes diferentes)** | `ESPECIFICACAO-V1-CONSOLIDADA.md §5.1` | Decidir regra: agrupar por telefone normalizado; nome mais frequente + observação. |
| 2 | **Snapshot preço/duração: colunas em `agendamento_servico` vs tabela histórica** | `ESPECIFICACAO-V1-CONSOLIDADA.md §5.2` | Decisão tomada: colunas na própria `agendamento_servico`. Confirmar implementação. |
| 3 | **Reagendamento por cliente: V1 = apenas admin. Cliente cancela e faz novo?** | `ESPECIFICACAO-V1-CONSOLIDADA.md §5.3` | Confirmar: V1 = apenas admin. Revisar pós-V1. |
| 4 | **Troca de profissional no reagendamento: permitir?** | `ESPECIFICACAO-V1-CONSOLIDADA.md §5.4` | Decisão: Sim, validando disponibilidade. Implementar na Fase 5. |
| 5 | **Tabela `estabelecimento` vs `configuracao`: migrar tudo ou manter `configuracao` para parâmetros técnicos?** | `ESPECIFICACAO-V1-CONSOLIDADA.md §5.5` | Decisão: `estabelecimento` = dados do negócio; `configuracao` = parâmetros técnicos (intervalo_slot, etc.). |
| 6 | **Logo: arquivo em volume Docker vs base64 no BD** | `ESPECIFICACAO-V1-CONSOLIDADA.md §5.6` | Decisão: Arquivo em volume + caminho no BD. |
| 7 | **Índices de performance: quais criar na V1?** | `ESPECIFICACAO-V1-CONSOLIDADA.md §5.7` | Mínimo: `agendamento(profissional_id, data)`, `agendamento(cliente_id)`, `agendamento(status)`. |
| 8 | **Cancelamento pelo cliente: exigir motivo?** | `ESPECIFICACAO-V1-CONSOLIDADA.md §5.8` | Decisão: Opcional, campo `cancelamento_motivo` nullable em `agendamento`. |
| 9 | **Receita prevista: apenas `agendado` (corrigir `app.py` que soma `agendado` + `realizado`)** | `ESPECIFICACAO-V1-CONSOLIDADA.md §4` | Corrigir na Fase 4. |
| 10 | **Auto-atualização para `realizado`: remover `atualizar_agendamentos_realizados` do `init_db`** | `ESPECIFICACAO-V1-CONSOLIDADA.md §4` | Remover na Fase 2. Admin define manual. |
| 11 | **Tabela `agendamento_status_historico`: implementar na V1 ou pós-V1?** | `ESPECIFICACAO-V1-CONSOLIDADA.md §2.6` | Implementar na Fase 5 (junto com reagendamento). |
| 12 | **Profissional-serviço (N:M): impacta disponibilidade pública. Validar regra "profissional realiza TODOS os serviços selecionados"** | `ESPECIFICACAO-V1-CONSOLIDADA.md §2.12` | Implementar na Fase 2. Testar cenários múltiplos serviços + múltiplos profissionais. |

---

## 8. VERIFICAÇÃO DE ARQUITETURA — FEATURE GATING FUTURO

> **Não implementar agora.** Apenas registrar se a arquitetura atual precisará de mecanismo de plano/feature gating no futuro.

| Aspecto | Avaliação | Recomendação |
|---------|-----------|--------------|
| **Banco de dados** | Tabelas atuais não têm coluna `plano` ou `versao`. Único registro = 1 estabelecimento por instalação. | Adicionar coluna `plano` em `estabelecimento` (ou `configuracao`) quando houver necessidade real. |
| **Backend/API** | Rotas admin não verificam plano. Middleware `@login_requerido` só checa autenticação. | Criar decorator `@requer_plano('intermediaria')` ou similar quando houver gating real. |
| **Frontend/Admin** | Templates não têm lógica condicional por plano. | Manter simples. Se gating for necessário, usar variável de template `plano_atual` passada pelo backend. |
| **Multi-tenancy** | Não existe. Uma instalação = um estabelecimento. | Não antecipar. Se virar SaaS multi-tenant, arquitetura muda significativamente (isolamento de dados, routing). |
| **Billing/Assinatura** | Não existe. | Não implementar até decisão comercial de modelo de negócio (SaaS vs licença vs híbrido). |

**Conclusão:** A arquitetura atual **não impede** feature gating futuro, mas **não está preparada** para ele. Adicionar quando houver decisão comercial concreta. Não criar abstrações prematuras.

---

## 9. RESUMO DA DISTRIBUIÇÃO (VISÃO EXECUTIVA)

| Versão | Público-Alvo | Foco | Recursos-Chave Diferenciais |
|--------|--------------|------|----------------------------|
| **Básica** | Microempreendedor individual, 1 profissional, operação simples | **Operar**: receber agendamentos, gerenciar agenda, cancelar, histórico básico | Núcleo V1 completo. Dashboard básico. CRUDs essenciais. Configuração consolidada. Backup documentado. |
| **Intermediária** | Pequeno negócio c/ 2+ profissionais, necessidade de gestão e comunicação | **Gerenciar**: múltiplos profissionais, relatórios, automações básicas, ficha cliente rica | Agenda individual, bloqueios, exportações, política cancelamento, notificações (WhatsApp/SMS/E-mail), LGPD, logs auditoria. |
| **Avançada** | Negócio em crescimento, múltiplos profissionais, gestão profissionalizada | **Otimizar**: analytics, integrações, personalização, controle total | Gráficos/KPIs, relatórios gerenciais, API/webhooks, domínio próprio, onboarding guiado, suporte prioritário, comissões, pacotes. |

---

## 10. PRÓXIMOS PASSOS RECOMENDADOS

1. **Validar esta matriz com o proprietário** — confirmar/ajustar itens 🟡 (Seção 6).
2. **Resolver conflitos da Seção 7** — decisões técnicas antes da implementação das fases correspondentes.
3. **Focar 100% na entrega da V1 (Básica)** — não desviar esforços para recursos Intermediária/Avançada.
4. **Registrar decisões tomadas** — atualizar este documento e `ESPECIFICACAO-V1-CONSOLIDADA.md` conforme decisões.
5. **Revisar na fase de homologação** — validar se a Básica atende critério de saída (`AGENTS.md §12`).

---

*Documento versão 1.0 — Baseado em AGENTS.md, FOUNDATION.md, ESPECIFICACAO-V1-CONSOLIDADA.md, roadmap, REGRAS-AGENDAMENTOS.md, ARQUITETURA-BANCO.md, AMBIENTE-DESENVOLVIMENTO.md, AllLogic-Scheduler-V1-Comercial.md e estado atual do código (set/2026).*