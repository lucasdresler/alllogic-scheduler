# Especificação de Implementação — Redesign Agillex Agenda Premium
**Data:** 2026-10-08  
**Projeto:** AllLogic Scheduler (Agillex Agenda)  
**Documento de Referência:** `docs/AUDITORIA-VISUAL-E-PROPOSTA-REDESIGN-PREMIUM.md`  
**Status do Projeto:** V1 Comercial implantada em produção no commit `843e291`, homologação funcional concluída pelo usuário e fundação visual inicial em CSS implementada localmente em `static/css/style.css`.  
**Classificação:** Especificação Técnica de Implementação Visual (Sem alterações de regras de negócio, rotas ou banco de dados).

---

## 1. Objetivo e Escopo

Esta especificação consolida o plano arquitetural e visual para a transformação completa da interface do **Agillex Agenda**, elevando-a ao padrão **Premium Sofisticado**.

O escopo compreende:
1. **Painel Administrativo:** Evolução da navegação por botões horizontais soltos para um **Menu Lateral (Sidebar) Elegante e Organizado** (com versão recolhível/offcanvas no mobile), cards de métricas refinados, agenda diária e semanal de alta legibilidade e formulários padronizados.
2. **Agendamento Público:** Apresentação elegante da marca, barra de progresso visual em 5 etapas (*stepper*), cards de serviços e profissionais refinados, seleção intuitiva de datas/horários e confirmação com aparência de comprovante executivo.
3. **Experiência Mobile & Acessibilidade:** Áreas de toque confortáveis (mínimo de 44px), eliminação de zoom involuntário em iOS (`font-size: 1rem` em inputs), contrastes de conformidade WCAG AA/AAA e layouts fluidos.

---

## 2. Princípios e Tokens Visuais Consolidados

A identidade visual adota a tríade **Azul Profundo, Dourado Champagne e Superfícies Claras**, com tema padrão claro:

```css
:root {
    color-scheme: light;

    /* Superfícies e Fundos (Clean & Pure) */
    --bg-app: #F8FAFC;              /* Fundo geral da página (Slate 50) */
    --bg-surface: #FFFFFF;          /* Cartões, modais e containers */
    --bg-surface-elevated: #FFFFFF; /* Superfícies elevadas com sombra suave */
    --bg-surface-subtle: #F1F5F9;   /* Slate 100 - áreas de suporte e cabeçalhos */
    --bg-surface-hover: #F8FAFC;    /* Hover de itens e linhas */

    /* Azul Profundo (Navy / Sapphire Corporate) */
    --navy-950: #070F1E;            /* Navy quase preto para contraste máximo */
    --navy-900: #0B192C;            /* Títulos máximos, cabeçalho da sidebar */
    --navy-800: #0F2042;            /* Botões primários, itens ativos */
    --navy-700: #1E3A8A;            /* Azul safira para foco, links e interações */
    --navy-600: #2563EB;            /* Azul vibrante para micro-realces */
    --navy-100: #EFF6FF;            /* Pílulas de fundo azul suave */

    /* Dourado Discreto (Champagne & Luxury Accents) */
    --gold-accent: #B89748;         /* Dourado nobre equilibrado */
    --gold-light: #DFCA8E;          /* Dourado claro para bordas finas luminosas */
    --gold-subtle: #FAF6ED;         /* Fundo champagne muito suave */
    --gold-hover: #A0833C;          /* Estado de interação do dourado */

    /* Tipografia e Textos (WCAG AA/AAA) */
    --text-title: #0F172A;          /* Slate 900 - títulos principais e ênfase */
    --text-body: #334155;           /* Slate 700 - texto corrido legível */
    --text-muted: #64748B;          /* Slate 500 - legendas, labels e auxiliares */
    --text-inverse: #FFFFFF;        /* Branco puro sobre fundos navy */

    /* Bordas e Divisores */
    --border-subtle: #E2E8F0;       /* Slate 200 - bordas elegantes de cards */
    --border-focus: #0F2042;        /* Borda de foco em formulários */
    --border-accent: #DFCA8E;       /* Destaque dourado sutil */

    /* Sombras em Camadas (Layered Elevation) */
    --shadow-sm: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
    --shadow-card: 0 4px 6px -1px rgba(15, 23, 42, 0.05), 0 2px 4px -2px rgba(15, 23, 42, 0.03);
    --shadow-hover: 0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.03);
    --shadow-modal: 0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.05);

    /* Raio de Arredondamento */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-pill: 9999px;
}
```

---

## 3. Diretrizes do Painel Administrativo Premium

### 3.1. Estrutura de Layout com Menu Lateral (Sidebar)
O layout atual baseia-se em um bloco vertical simples (`.container-admin`) com uma barra de links horizontais soltos (`.acoes-topo`) que quebram de maneira desordenada no mobile. A nova arquitetura administrativa introduz:

1. **Layout em Duas Colunas (Desktop / Tablet):**
   - **Sidebar Fixa/Estável (Largura: 250px):**
     - Cabeçalho da sidebar com logotipo da empresa ou nome da marca com acabamento refinado.
     - Navegação hierarquizada em lista vertical com ícones SVG limpos e rótulos claros:
       - 📅 **Agenda / Painel** (`/admin`)
       - ✂️ **Serviços** (`/admin/servicos`)
       - 👤 **Profissionais** (`/admin/profissionais`)
       - 🏢 **Dados do Estabelecimento** (`/admin/estabelecimento`)
       - ⚙️ **Configurações da Agenda** (`/admin/configuracoes`)
       - 🔒 **Alterar Senha** (`/admin/alterar-senha`)
     - Rodapé da sidebar com identificação do usuário logado e botão de **Sair** (`/admin/logout`).
     - Item ativo ganha fundo azul profundo suave (`--navy-100`), texto `--navy-800` e borda lateral esquerda de destaque champagne (`--gold-accent`).
   - **Área de Conteúdo Principal (`main.admin-content`):**
     - Topo com saudação / identificação da visualização e botão de atalho para a página pública ("Ver agendamento online").
     - Espaço arejado com fundo `--bg-app` e cartões em branco puro (`--bg-surface`).

2. **Comportamento Responsivo no Mobile (< 768px):**
   - No topo do mobile: barra de navegação com logotipo, nome do estabelecimento e botão hamburguer (☰).
   - A sidebar transforma-se em um menu offcanvas deslizante ou gaveta lateral que abre suavemente sem travar a navegação.

### 3.2. Cards de Métricas e Indicadores Refinados
Substituição do card único genérico por uma **Grade de Indicadores em Cards Independentes**:
- **Card 1: Agendamentos do Período:** Ícone de calendário, total numérico em destaque com `--navy-900` (font-size: 1.8rem, peso 700) e rótulo claro ("Total de agendamentos").
- **Card 2: Valor Financeiro:** Ícone de moeda/cifrão com acabamento champagne, valor formatado em R$ com destaque tipográfico e rótulo contextual ("Valor dos agendamentos previstos" ou "Valor dos agendamentos do período").

### 3.3. Agenda Diária e Semanal de Alta Legibilidade
- **Segmented Control das Abas:** Abas de navegação (Hoje, Semana, Mês, Pesquisa) centralizadas em container cinza suave (`#F1F5F9`), onde a aba ativa se eleva com fundo branco e sombra sutil.
- **Navegação Semanal:** Botões "Semana anterior" e "Próxima semana" com setas elegantes, delimitando o período central em negrito azul marinho.
- **Tabela de Agendamentos:**
  - Cabeçalho com fundo cinza suave e texto em caixa alta discreta (*uppercase tracking*).
  - Linhas com altura confortável (mínimo de 48px).
  - Pílulas de status coloridas em tons pastéis elegantes (sem cores fluorescentes).
  - Botões de ação alinhados com ícones/rótulos organizados (Concluir, Cancelar, Reagendar).

### 3.4. Pesquisa e Filtros Integrados Visualmente
- O card de pesquisa integra campos com rótulos superiores alinhados, seletores com padding padronizado de 10px e botões de ação ("Pesquisar" em azul marinho e "Limpar filtros" em contorno sutil).

---

## 4. Diretrizes do Fluxo Público de Agendamento

### 4.1. Apresentação Elegante do Estabelecimento
- **Header Público Nobre:** Logotipo centralizado com proporções harmônicas (altura máxima 60px), nome do estabelecimento em azul marinho nobre (`--navy-900`) e frase de boas-vindas acolhedora.
- **Rodapé com Identidade:** Endereço formatado com ícone de localização e telefone com link para discagem direta/WhatsApp.

### 4.2. Stepper Visual em 5 Etapas (Progresso do Agendamento)
Substituição da `div#progresso` com texto plano por uma **Barra de Progresso Visual Integrada**:
- 5 marcadores visuais correspondentes às etapas:
  1. *Serviços*
  2. *Profissional*
  3. *Data e Horário*
  4. *Identificação*
  5. *Confirmação*
- Etapas concluídas ganham check dourado; etapa atual recebe destaque em azul profundo e anel luminoso; etapas futuras permanecem em cinza neutro.
- No mobile: versão compacta com linha de progresso contínua e texto "Etapa X de 5: [Nome da Etapa]".

### 4.3. Cards de Seleção de Serviços e Profissionais
- **Serviços:** Cada serviço em card independente com borda sutil, nome em destaque, duração estimada em pílula cinza e preço em dourado nobre. Checkbox estilizado ou indicador de seleção que se ilumina ao ser clicado.
- **Profissionais:** Cards com avatar estilizado (iniciais em círculo azul suave), nome e indicador de disponibilidade.

### 4.4. Seleção Intuitiva de Datas e Horários
- Grade de dias em pílulas ergonômicas mostrando dia da semana abreviado (Seg, Ter, Qua...) e dia do mês.
- Seleção de horários com slots em botões limpos de 3 colunas, destacando horários disponíveis e desativando horários conflitantes com suavidade.

### 4.5. Confirmação do Agendamento (Comprovante Executivo)
- Apresentação dos dados em formato de cartão de confirmação profissional com borda superior champagne, ícone verde esmeralda em círculo translúcido, separadores pontilhados finos e botão de retorno claro.

---

## 5. Requisitos Mobile e Acessibilidade

Com base na inspeção do código atual, foram levantadas as seguintes correções mandatórias:

1. **Prevenção de Zoom Involuntário em Dispositivos iOS:**
   - *Fato Observado:* Vários campos em formulários possuíam `font-size: 0.95rem` (~15.2px), o que ativa o zoom automático do WebKit Safari em iPhones ao focar no campo.
   - *Diretriz:* Todos os `input`, `select` e `textarea` em telas menores que 768px devem possuir obrigatoriamente `font-size: 1rem` (16px) e `line-height: 1.4`.
2. **Área Mínima de Toque (Touch Targets):**
   - *Fato Observado:* Os botões `.btn-acao` de tabela mediam menos de 30px de altura em telas reduzidas.
   - *Diretriz:* Todos os elementos interativos (botões de ação, slots de horário, abas e links de tabela) devem ter uma área de toque efetiva de no mínimo **44px × 44px** (aplicando padding ou min-height adequado).
3. **Contraste de Acessibilidade (WCAG 2.1 Nível AA):**
   - Relação de contraste mínima de 4.5:1 para todo texto corrido sobre superfícies brancas (`#334155` e `#0F172A` alcançam > 7:1).
   - Textos secundários em Slate 500 (`#64748B`) alcançam relação superior a 4.6:1 sobre `#FFFFFF`.
4. **Estados de Foco Visíveis:**
   - Todo elemento focável via teclado (Tab) deve apresentar anel de foco visível em azul corporativo com transparência (`outline: none; box-shadow: 0 0 0 3px rgba(15, 32, 66, 0.15)`).

---

## 6. Inventário de Telas e Arquivos Envolvidos

### 6.1. Arquivos de Estilos e Scripts
- [static/css/style.css](file:///home/dresler/AllLogic/Projetos/app-agendamento/static/css/style.css) — Arquivo central do Design System.
- [static/js/agendamento.js](file:///home/dresler/AllLogic/Projetos/app-agendamento/static/js/agendamento.js) — Script do agendamento público (deve ter seus IDs e eventos estritamente preservados).

### 6.2. Layout Compartilhado e Área Pública
| Template | Finalidade | Principais Elementos |
| :--- | :--- | :--- |
| [templates/base.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/base.html) | Shell base HTML | Meta tags, fontes, inclusão de CSS. |
| [templates/base_admin.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/base_admin.html) | Layout mestre administrativo | Sidebar fixa desktop, topbar responsiva, menu mobile offcanvas, rodapé com logout. |
| [templates/index.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/index.html) | Fluxo público de agendamento | Cabeçalho, stepper, 5 etapas de formulário, rodapé. |
| [templates/sucesso.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/sucesso.html) | Confirmação pública | Card de comprovante, resumo do agendamento, botão novo agendamento. |

### 6.3. Painel Administrativo
| Template | Finalidade | Principais Elementos |
| :--- | :--- | :--- |
| [templates/admin_login.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_login.html) | Autenticação administrativa | Card centralizado claro, inputs de usuário/senha, link esqueci senha. |
| [templates/admin_dashboard.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_dashboard.html) | Painel principal e Agenda | Sidebar, cards de resumo, abas (Hoje/Semana/Mês/Pesquisa), tabela, modais de cancelamento/conclusão. |
| [templates/admin_servicos.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_servicos.html) | Gestão de serviços | Tabela de serviços, pílulas de status ativo/inativo, botão novo serviço. |
| [templates/admin_servico_form.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_servico_form.html) | Cadastro/Edição de serviço | Formulário com nome, preço, duração e status. |
| [templates/admin_profissionais.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_profissionais.html) | Gestão de profissionais | Tabela de profissionais, serviços associados, botão novo profissional. |
| [templates/admin_profissional_form.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_profissional_form.html) | Cadastro/Edição de profissional | Dados básicos, vínculo de serviços e tabela de jornada/disponibilidade individual. |
| [templates/admin_estabelecimento.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_estabelecimento.html) | Dados do estabelecimento | Upload de logotipo com preview, endereço, telefone e identificação. |
| [templates/admin_configuracoes.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_configuracoes.html) | Configurações da agenda | Antecedência máxima, horários de funcionamento e dias ativos. |
| [templates/admin_reagendar.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_reagendar.html) | Tela de reagendamento | Formulário com seleção de nova data, horários dinâmicos e profissional. |
| [templates/admin_reagendar_sucesso.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_reagendar_sucesso.html) | Confirmação de reagendamento | Resumo dos dados, temporizador de 5s e botão de retorno imediato. |
| [templates/admin_alterar_senha.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_alterar_senha.html) | Alteração de credencial | Validação de senha atual, nova senha e confirmação. |
| [templates/admin_configuracao_inicial.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_configuracao_inicial.html) | Primeiro acesso | Definição da primeira senha administrativa. |
| [templates/admin_esqueci_senha.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_esqueci_senha.html) | Recuperação de acesso | Formulário de solicitação de token. |
| [templates/admin_redefinir_senha.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/admin_redefinir_senha.html) | Redefinição via token | Entrada da nova senha via link seguro. |

---

## 7. Rastreabilidade e Preservação de Comportamentos

Para assegurar **zero regressão funcional**, a implementação deve seguir as seguintes garantias de preservação:

1. **Seletores do Fluxo Público (`agendamento.js`):**
   - Os IDs `#progresso`, `#mensagem-erro-global`, `#etapa-1`, `#etapa-2`, `#etapa-3`, `#etapa-4`, `#etapa-5`, `#btn-avancar-1`, `#btn-avancar-2`, `#btn-avancar-3`, `#btn-avancar-4`, `#btn-confirmar`, `#dias-grid`, `#horarios-grid`, `#input-nome`, `#input-telefone` e os spans `#resumo-*` **devem permanecer intactos**.
   - Os atributos `data-etapa="servico"`, `data-id`, `data-nome`, `data-preco`, `data-voltar` e a classe `.selecionado` não podem sofrer qualquer alteração.
2. **Seletores Administrativos e de Testes:**
   - Os links de aba `.tab-link`, o filtro de profissional `#filtro-prof`, os botões `#btn-semana-anterior`, `#btn-proxima-semana`, `#btn-pesquisar`, `#btn-limpar-filtros`, `#btn-retorno-agenda` e as classes `.tabela-agendamentos`, `.badge-status`, `.badge-agendado`, `.badge-realizado`, `.badge-cancelado`, `.badge-falta`, `.btn-acao-*` são validados pelas suítes automatizadas de testes e **devem ser preservados integralmente**.
3. **Formulários e Tokens CSRF:**
   - Todos os inputs ocultos `input[name="csrf_token"]` e métodos POST/GET devem ser rigorosamente mantidos.

---

## 8. Sequência Incremental de Implementação e Estado Real dos Blocos

A execução do redesign foi estruturada em blocos de trabalho delimitados, permitindo testes e homologações isoladas:

```
Bloco 1: Layout Mestre & Sidebar Administrativa [CONCLUÍDO]
   │  (Estrutura de layout responsivo, sidebar limpa, topo administrativo)
   │  Refinamentos 1.1 e 1.2: Paleta clara Marfim/Champagne e contenção de tabela [CONCLUÍDOS]
   ▼
Bloco 2: Dashboard & Agenda (Hoje, Semana, Mês, Pesquisa) [PLANEJADO]
   │  (Cards de métricas em grade, abas segmented control e novos modais)
   ▼
Bloco 3: Formulários Administrativos e Gestão [PLANEJADO]
   │  (Polimento avançado de inputs e cadastros secundários)
   ▼
Bloco 4: Agendamento Público & Experiência Mobile [PLANEJADO]
      (Apresentação elegante, stepper visual em 5 etapas, cards de seleção e comprovante)
```

### Detalhamento do Estado dos Blocos:
- **Bloco 1 (Layout Mestre & Sidebar Administrativa):** **CONCLUÍDO**.
  - Criação de `templates/base_admin.html` com layout de duas colunas, navegação semântica na sidebar desktop, topbar unificada e menu mobile offcanvas acessível (com overlay e tecla `Escape`).
  - Refatoração dos 10 templates administrativos para herdar de `base_admin.html`.
- **Blocos 1.1 e 1.2 (Refinamentos Visuais da Paleta e Sidebar Clara):** **CONCLUÍDOS**.
  - Consolidação da paleta definitiva clara em `static/css/style.css`: Azul-marinho profundo (`#14213D`), Champagne dourado (`#E5C78B` / `#B89748`) e Marfim suave (`#F6F1E8`).
  - Substituição da barra lateral escura legada por acabamento claro marfim/champagne.
  - Dimensionamento estrutural e defensivo na tabela de agendamentos (`.col-hora`, `.col-cliente`, `.col-telefone`, `.col-servico`, `.col-profissional`, `.col-status`, `.col-preco`, `.col-acoes`) e classe `.celula-texto-longo` com truncamento e tooltips.
- **Bloco 2 (Dashboard & Agenda — Métricas em Grade e Novos Controles):** **PLANEJADO**.
  - Apenas as correções estruturais de dimensionamento da tabela foram incorporadas. A reestruturação de métricas em grade independente e abas avançadas permanece planejada para ciclo posterior.
- **Bloco 3 (Polimento Secundário de Formulários Administrativos):** **PLANEJADO**.
  - A herança de `base_admin.html` foi aplicada nos formulários administrativos; refinamentos visuais secundários de campos individuais permanecem planejados.
- **Bloco 4 (Agendamento Público & Experiência Mobile — Stepper em 5 etapas):** **PLANEJADO**.
  - Permanece explicitamente planejado para ciclo futuro, preservando a área pública de agendamento estável e inalterada nesta entrega.

---

## 9. Critérios Objetivos de Validação

Cada bloco de implementação deverá cumprir com sucesso a seguinte bateria de critérios antes de ser dado como concluído:

1. **Validação Estrutural e de Sintaxe:**
   - Sintaxe Jinja2 validada sem erros em todos os 18 templates (incluindo o layout mestre `base_admin.html`).
   - Sintaxe CSS validada com chaves perfeitamente balanceadas e `git diff --check` sem erros de formatação.
2. **Suíte Completa de Testes Automatizados:**
   - Execução com sucesso dos **48 testes no pytest** contra banco PostgreSQL isolado (0 falhas).
3. **Responsividade Multi-Dispositivo:**
   - Validação da renderização correta em resoluções Desktop (1280px+), Tablet (768px a 1024px) e Mobile (360px a 430px).
   - Sidebar funcionando como gaveta/menu acessível no mobile.
4. **Usabilidade e Acessibilidade:**
   - Nenhuma área clicável interativa menor que 44px × 44px no mobile.
   - Nenhum input disparando zoom indesejado no mobile (font-size >= 16px).
   - Contraste de texto aprovado nos padrões WCAG AA.
