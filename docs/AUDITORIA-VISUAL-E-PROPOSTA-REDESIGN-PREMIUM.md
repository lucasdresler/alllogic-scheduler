# Auditoria Visual e Proposta de Redesign Premium — Agillex Agenda
**Data:** 2026-10-08  
**Projeto:** AllLogic Scheduler (Agillex Agenda)  
**Ambiente:** Planejamento e Especificação Arquitetural (Sem alteração de código ou infraestrutura nesta etapa)  
**Direção Visual:** *Premium Sofisticado* — Azul Profundo, Dourado Discreto e Superfícies Claras (Tema Padrão Claro)  
**Status da Homologação Funcional Prévia:** Concluída e homologada pelo usuário em produção (commit `843e291`).

---

## 1. Identificação e Contexto

O Agillex Agenda encontra-se plenamente funcional e homologado em produção no domínio `https://agenda.alllogiconline.com.br/`. Todas as regras de negócio de agendamento (múltiplos serviços, disponibilidade dinâmica, cancelamento, conclusão, reagendamento com confirmação de 5 segundos e pesquisa integrada) foram validadas com sucesso.

O presente documento estabelece a **auditoria visual do estado atual** e a **especificação técnica e visual do Redesign Premium Sofisticado**, com o objetivo de elevar a experiência visual, a percepção de valor e a usabilidade tanto dos clientes finais (área pública de agendamento) quanto dos pequenos negócios contratantes (painel administrativo).

---

## 2. Diagnóstico da Auditoria Visual Atual

A interface atual foi construída sobre uma base escura monocromática concebida originalmente para um perfil específico de barbearia tradicional. Essa abordagem apresenta limitações estéticas e mercadológicas evidentes:

### 2.1. Problemas Identificados no Design Atual
1. **Paleta Excessivamente Escura e Austera:**
   - Uso de fundo quase preto (`#0d0d0d`) e cartões em cinza carvão (`#1a1a1a`).
   - Causa fadiga visual em operadores administrativos que utilizam o sistema ao longo de jornadas completas de 8 a 10 horas.
   - Restringe o apelo comercial do produto a nichos específicos, afastando clínicas médicas, consultórios de estética, salões boutique, spas e prestadores de serviços executivos que exigem ambientes luminosos, asseados e sofisticados.
2. **Dourado Saturado e Chapado:**
   - O dourado atual (`#d4af37` / `#c89b3c`) é aplicado em botões cheios com texto preto duro (`#0d0d0d`), gerando um efeito de alto contraste visual que remete a etiquetas de advertência.
   - Falta de sutileza e acabamento refinado (champagne/ouro polido com acentos pontuais).
3. **Falta de Profundidade e Elevação:**
   - Quase ausência de sombras sutis em camadas (`layered elevation shadows`). O relevo é feito unicamente por bordas duras de 1px (`#333333`).
   - Os cards e tabelas transmitem uma sensação de rigidez geométrica sem suavidade tátil.
4. **Hierarquia Tipográfica Rústica:**
   - Falta de diferenciação clara entre títulos, rótulos de dados e textos auxiliares.
   - Rótulos e inputs administrativos têm pesos e espaçamentos padronizados sem microespaçamento (*letter-spacing*) moderno.
5. **Experiência Mobile Pública:**
   - A seleção de serviços, dias e horários no mobile opera com caixas sólidas e estáticas. O feedback visual ao toque (*active/selected*) é pesado, quando deveria transmitir a fluidez e leveza de um aplicativo móvel nativo de alto padrão.

---

## 3. Conceito do Redesign: "Premium Sofisticado"

O novo design posiciona o Agillex Agenda como uma **solução de alta categoria (*high-end*)**, inspirada nas melhores interfaces internacionais de hotelaria, beleza de luxo e plataformas SaaS corporativas modernas:

- **Superfícies Claras e Luminosas:** Tema claro por padrão (*Light Theme*), transmitindo frescor, limpeza, clareza e credibilidade profissional.
- **Azul Profundo (*Navy / Midnight Sapphire*):** A cor de autoridade e estrutura, presente em cabeçalhos, títulos nobres, botões de ação prioritária e estados de foco corporativos.
- **Dourado Discreto (*Champagne & Subtle Gold Accent*):** Utilizado não como preenchimento agressivo, mas como toque de refinamento — em badges de destaque, pílulas de status ativas, microbordas luminosas, ícones de confirmação e detalhes de valor monetário.
- **Identidade Única e Coesa:** Tanto a página pública de agendamento quanto o painel administrativo compartilharão o mesmo design system, gerando uma experiência fluida de marca única.

---

## 4. O Novo Design System (Tokens e Variáveis CSS)

A proposta arquitetural substitui as variáveis primitivas em `:root` por uma arquitetura de tokens semânticos completos para superfícies claras:

```css
:root {
    /* Esquema e Tema */
    color-scheme: light;

    /* Superfícies e Fundos (Clean & Pure) */
    --bg-app: #F8FAFC;              /* Slate 50 refinado - fundo geral da página */
    --bg-surface: #FFFFFF;          /* Branco puro - cartões, modais e containers */
    --bg-surface-elevated: #FFFFFF; /* Superfícies elevadas */
    --bg-surface-subtle: #F1F5F9;   /* Slate 100 - áreas de suporte, cabeçalhos de tabela */
    --bg-surface-hover: #F8FAFC;    /* Hover de itens e linhas */

    /* Azul Profundo (Navy / Sapphire Corporate) */
    --navy-900: #0B192C;            /* Títulos máximos e rodapé solene */
    --navy-800: #0F2042;            /* Botões primários e headers nobres */
    --navy-700: #1E3A8A;            /* Azul safira para estados ativos e links */
    --navy-100: #E0E7FF;            /* Pílulas de fundo azul sutil */

    /* Dourado Discreto (Champagne & Luxury Accents) */
    --gold-accent: #B89748;         /* Dourado nobre equilibrado */
    --gold-light: #DFCA8E;          /* Dourado claro para bordas luminosas */
    --gold-subtle: #FAF6ED;         /* Fundo champagne muito suave (badges e tags) */
    --gold-hover: #A0833C;          /* Estado de interação */

    /* Tipografia e Textos (Máxima Legibilidade AA/AAA) */
    --text-title: #0F172A;          /* Slate 900 - títulos principais e ênfase */
    --text-body: #334155;           /* Slate 700 - texto corrido legível */
    --text-muted: #64748B;          /* Slate 500 - legendas, labels e dados auxiliares */
    --text-inverse: #FFFFFF;        /* Texto sobre fundos navy ou botões */

    /* Bordas e Divisores */
    --border-subtle: #E2E8F0;       /* Slate 200 - bordas elegantes de cards e inputs */
    --border-focus: #0F2042;        /* Foco de formulário refinado */
    --border-accent: #DFCA8E;       /* Destaque dourado delicado */

    /* Semântica Operacional */
    --status-success-bg: #ECFDF5;
    --status-success-text: #059669;
    --status-success-border: #A7F3D0;

    --status-danger-bg: #FEF2F2;
    --status-danger-text: #DC2626;
    --status-danger-border: #FECACA;

    --status-warning-bg: #FFFBEB;
    --status-warning-text: #D97706;
    --status-warning-border: #FDE68A;

    /* Sombras em Camadas (Layered Elevation) */
    --shadow-sm: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
    --shadow-card: 0 4px 6px -1px rgba(15, 23, 42, 0.05), 0 2px 4px -2px rgba(15, 23, 42, 0.03);
    --shadow-hover: 0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.03);
    --shadow-modal: 0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.05);

    /* Raio de Arredondamento */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --radius-pill: 9999px;
}
```

---

## 5. Mapeamento de Telas e Melhorias Propostas

### 5.1. Página Pública de Agendamento (`/`)
- **Cabeçalho:** Fundo suave com o logotipo em destaque nítido, sem fundo preto forçado. Subtítulo elegante com espaçamento arejado.
- **Barra de Progresso:** Pílula sutil numerada (Etapa 1 de 5) com preenchimento em azul profundo e acento dourado discreto.
- **Cards de Seleção (Serviços e Profissionais):**
  - Fundo branco puro com borda suave (`--border-subtle`).
  - Efeito suave ao passar o cursor ou tocar: sutil elevação (`--shadow-hover`) e borda suave.
  - Quando selecionado: borda elegante em azul profundo (`--navy-800`), pequeno indicador de seleção com check dourado e valor em destaque com tipografia nobre.
- **Seleção de Datas e Horários:**
  - Grade com botões em formato de cápsula ergonômica.
  - Dia selecionado ganha fundo azul marinho profundo (`--navy-800`) e texto branco luminoso.
  - Horários com slots bem distribuídos e indicação de disponibilidade instantânea.
- **Botões de Ação:** Botão "Avançar" com azul profundo refinado, micro-sombra de profundidade e transição de 200ms.

### 5.2. Tela de Confirmação Pública e Reagendamento (`sucesso.html` e `admin_reagendar_sucesso.html`)
- Card centralizado em branco puro com sombra suave e borda superior reforçada com sutil filete champagne (`#B89748`).
- Ícone de sucesso verde esmeralda suave (`#059669`) em círculo com fundo translúcido (`#ECFDF5`).
- Resumo em linhas alternadas ou com separadores sutis em cinza claro, dados do agendamento em tipografia estruturada e valor em pílula destacada.

### 5.3. Painel Administrativo (`/admin`)
- **Barra Superior / Topo Administrativo:**
  - Layout limpo, logotipo sem distorção, nome do estabelecimento e botão de logout em estilo sutil e profissional.
- **Menu de Ações Rápidas (Serviços, Profissionais, Estabelecimento, Agenda, Senha):**
  - Transformação dos botões secundários escuros em abas/pílulas modernas com fundo branco, borda fina e ícones ou tipografia elegante.
- **Cards de Métricas e Indicadores:**
  - Fundo branco com borda e sombra discreta.
  - Indicador numérico em destaque com azul marinho (`--navy-900`) e rótulo claro em cinza elegante (`--text-muted`).
- **Navegação da Agenda (Hoje, Semana, Mês, Pesquisa):**
  - Abas em estilo *segmented control* moderno sobre base cinza suave (`#F1F5F9`).
  - Aba ativa em branco puro com sombra e texto navy, garantindo clareza instantânea de onde o usuário está.
- **Tabela de Agendamentos:**
  - Cabeçalho de tabela em fundo cinza claríssimo (`#F8FAFC`) com texto em cinza nobre (`#475569`).
  - Linhas com linhas de separação delicadas (`#F1F5F9`) e hover suave.
  - Status em pílulas (*badges*) coloridas contemporâneas com fundo suave e texto saturado:
    - `Agendado`: Azul navy / safira (`#EFF6FF` / `#1D4ED8`).
    - `Realizado`: Esmeralda suave (`#ECFDF5` / `#047857`).
    - `Cancelado`: Vermelho suave (`#FEF2F2` / `#B91C1C`).
    - `Não compareceu`: Âmbar suave (`#FFFBEB` / `#B45309`).
  - Botões de ação em formato de botões discretos e funcionais (evitando cores berrantes).

---

## 6. Estratégia de Transição Técnica e Segurança

Para garantir total estabilidade e preservar a homologação funcional recentemente concluída pelo usuário:

1. **Preservação de Todas as Classes e Identificadores Existentes:**
   - Nenhum ID de elemento (ex.: `#btn-retorno-agenda`, `#nova_data`, `#btn-pesquisar`, `#dias-grid`, etc.) será renomeado.
   - Nenhuma classe utilizada pelo JavaScript ou pelos testes automatizados (ex.: `.tab-link`, `.opcao-btn`, `.horario-btn`, `.resumo-item`, etc.) sofrerá alteração estrutural.
2. **Centralização em CSS (`static/css/style.css`):**
   - 90% das alterações visuais serão concentradas nas variáveis, regras e estados do arquivo `style.css`.
   - Modificações em templates Jinja restringem-se à remoção de estilos *inline* legados escuros remanescentes (ex.: `style="color: var(--dourado);"`), garantindo que os componentes herdem as propriedades do novo design system.
3. **Compatibilidade Móvel e Responsividade:**
   - Manutenção rigorosa dos seletores de toque com áreas de clique (*touch targets*) de no mínimo 44px.
   - Tipografia de formulário com tamanho base mínimo de `16px` (`1rem`) em dispositivos móveis para evitar zoom automático indesejado no iOS Safari.

---

## 7. Matriz de Validação Pós-Redesign (Planejada)

Quando o redesign for executado em etapa futura, a aprovação obedecerá aos seguintes critérios técnicos e visuais:

| Verificação | Critério de Aceite |
| :--- | :--- |
| **Suíte de Testes Automatizados** | Manutenção dos **48 testes aprovados no pytest** sem qualquer regressão. |
| **Integridade de Sintaxe e Templates** | `compileall` com código 0 e todos os 17 templates Jinja validados com sucesso. |
| **Contraste de Acessibilidade (WCAG AA)** | Contraste mínimo de 4.5:1 para todos os textos sobre superfícies claras. |
| **Inspeção Visual Ponta a Ponta** | Verificação no navegador em desktop e mobile da área pública (`/`), login (`/admin/login`), dashboard (`/admin`), formulários de cadastro e fluxo de reagendamento. |
| **Rollback Pré-Configurado** | Criação de backup pré-redesign antes da publicação em produção. |

---

## 8. Conclusão e Próximos Passos

A direção visual **Premium Sofisticado** estabelece uma evolução determinante para a comercialização do Agillex Agenda, combinando a robustez funcional já comprovada com uma estética limpa, confiável e compatível com clientes exigentes de alto padrão.

### Próximo Passo Recomendado:
1. Submeter esta auditoria e proposta de design system para revisão e alinhamento com o usuário.
2. Mediante autorização, iniciar a implementação incremental do novo design system no ambiente local (atualização de `static/css/style.css` e polimento de templates).
3. Homologar visualmente no servidor local na porta 5000 antes de qualquer publicação em produção.
