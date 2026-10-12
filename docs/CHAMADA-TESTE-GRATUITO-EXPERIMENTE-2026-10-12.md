# Relatório Técnico — Implementação de Chamada para Teste Gratuito e Rota /experimente

**Data:** 12/10/2026  
**Projeto Técnico:** AllLogic Scheduler (`app-agendamento`)  
**Módulo:** Agendamento Público / Canal Comercial Agillex Premium  
**Ambiente de Homologação:** Local Isolado (`127.0.0.1:5433` - `scheduler_test_homologacao`)  
**Status da Operação:** **CONCLUÍDO E HOMOLOGADO**

---

## 1. Contexto e Objetivo

Este relatório documenta a implementação de uma chamada comercial discreta, profissional e acessível na página pública de agendamento do **Agillex Agenda**, convidando proprietários de estabelecimentos a conhecerem o produto e solicitarem um teste gratuito de 14 dias.

Adicionalmente, documenta a criação da rota oficial de destino `/experimente` e sua página provisória informativa com dados de contato institucionais da AllLogic Online, sem coleta de dados pessoais e sem simulação de formulários fictícios.

---

## 2. Investigação da Página Pública e Posicionamento da Chamada

1. **Rota e Template Identificados:**
   - Rota: `GET /` (função `index()` em `app.py`).
   - Template: `templates/index.html` (estende `templates/base.html`).
2. **Elementos Existentes na Página:**
   - Topo da página: marca do estabelecimento, logotipo e título *“Agende seu horário”*.
   - Conteúdo central: fluxo interativo em etapas com cartões (`.card`) para seleção de serviços, profissionais, datas/horários e dados do cliente.
   - Base da página: rodapé público (`.rodape-publico`) contendo endereço e telefone clicável do estabelecimento.
3. **Decisão de Posicionamento:**
   - A chamada comercial foi posicionada diretamente no rodapé público (`.rodape-publico`), logo abaixo dos dados de contato do estabelecimento, separada por um divisor suave.
   - **Impacto no fluxo de agendamento:** **Nenhum**. O cliente final navega pelas etapas de escolha e confirmação sem nenhuma interrupção, mantendo o fluxo transacional desobstruído.

---

## 3. Implementação da Chamada Comercial

### 3.1. Texto e URL Definitiva
- **Texto exato do link:** **“Experimente grátis por 14 dias”**
- **URL definitiva do destino:**
  `https://agenda.alllogiconline.com.br/experimente`
- **Atributos de link:** `target="_blank" rel="noopener noreferrer"` para não fechar a página de agendamento em andamento.

### 3.2. Centralização da Configuração
A URL foi centralizada como constante em `config.py`:
```python
URL_EXPERIMENTE = "https://agenda.alllogiconline.com.br/experimente"
```
E injetada no contexto de todos os templates através de `_carregar_config_template()` em `app.py`.

### 3.3. Estrutura HTML (`templates/index.html`)
```html
<footer class="rodape-publico">
    {% if endereco_estabelecimento %}
    <p class="rodape-endereco">{{ endereco_estabelecimento }}</p>
    {% endif %}
    {% if telefone_estabelecimento %}
    <p class="rodape-telefone">
        <a href="tel:{{ telefone_limpo }}" class="link-telefone">{{ telefone_estabelecimento }}</a>
    </p>
    {% endif %}
    <div class="rodape-comercial">
        <span class="rodape-comercial-marca">Agillex Agenda</span>
        <span class="rodape-comercial-sep">·</span>
        <a href="https://agenda.alllogiconline.com.br/experimente" class="link-experimente" target="_blank" rel="noopener noreferrer">Experimente grátis por 14 dias</a>
    </div>
</footer>
```

### 3.4. Estilização CSS Agillex Premium (`static/css/style.css`)
- **Visual:** Divisor tracejado discreto (`border-top: 1px dashed var(--border-subtle)`), tipografia refinada em 0.82rem, cor dourada institucional (`#8C6D2B`) com transição para marinho profundo no hover (`#14213D`).
- **Acessibilidade:** `:focus-visible` com anel de foco visível em champanhe dourado (`outline: 2px solid var(--champagne-dourado); outline-offset: 2px;`).
- **Responsividade:** Layout flexível com quebra automática (`flex-wrap: wrap; justify-content: center;`), garantindo zero transbordamento horizontal.

---

## 4. Implementação da Rota de Destino `/experimente`

Conforme as restrições da tarefa:
- **Não foi criado formulário de cadastro fictício** nem simulação de envio com sucesso.
- **Não são coletados dados pessoais** (zero campos `input`, `textarea` ou formulários).
- Foi criada uma **página provisória informativa** que apresenta a proposta de valor do Agillex Agenda e direciona os interessados para os canais oficiais de contato da AllLogic Online.

### 4.1. Rota no Backend (`app.py`)
```python
@app.route("/experimente")
def experimente():
    return render_template(
        "experimente.html",
        **_carregar_config_template(),
    )
```

### 4.2. Template Informativo Provisório (`templates/experimente.html`)
- **Cabeçalho:** Badge dourado *“TESTE GRÁTIS POR 14 DIAS”*, título principal e subtítulo destacando os benefícios para negócios que atendem por hora marcada.
- **Card de Recursos:** Destaque dos 4 pilares comerciais (Agendamento Online 24/7, Equipe e Horários sob Controle, Painel Administrativo Completo e 14 Dias de Avaliação Gratuita).
- **Aviso de Fluxo Provisório:** Caixa informativa com aviso claro:
  > *“O provisionamento automatizado de novas contas está em fase final de homologação. Durante este período, a ativação do seu teste gratuito de 14 dias é realizada diretamente com o suporte da AllLogic Online. Esta página informativa é provisória e antecipa o futuro fluxo de pré-cadastro automatizado do produto.”*
- **Contatos Oficiais:**
  - Botão WhatsApp em destaque: `https://wa.me/5511966381915?text=...`
  - Telefone institucional: `(11) 96638-1915` (`tel:+5511966381915`)
  - E-mail institucional: `contato@alllogiconline.com.br` (`mailto:contato@alllogiconline.com.br`)
  - Site institucional: `alllogiconline.com.br` (`https://alllogiconline.com.br`)
- **Ação de Retorno:** Botão secundário para retornar ao agendamento público (`/`).

---

## 5. Homologação e Testes Realizados

### 5.1. Validação Visual e Navegação (Headless Chrome via CDP)

| Teste | Critério de Aceite | Resultado Obtido | Status |
| :--- | :--- | :--- | :---: |
| **Página Pública Desktop (1280 px)** | Rodapé com link exato “Experimente grátis por 14 dias” e URL definitiva | Link presente, texto e href exatos | **APROVADO** |
| **Página Pública Mobile 390 px** | Link visível sem rolagem horizontal | `scrollWidth = 390 px` / `temRolagemHorizontal = false` | **APROVADO** |
| **Página Pública Mobile 375 px** | Link visível sem rolagem horizontal | `scrollWidth = 375 px` / `temRolagemHorizontal = false` | **APROVADO** |
| **Página Pública Mobile 360 px** | Link visível sem rolagem horizontal | `scrollWidth = 360 px` / `temRolagemHorizontal = false` | **APROVADO** |
| **Rota `/experimente` Desktop** | Status HTTP 200, texto informativo, contatos oficiais, 0 inputs | `status = 200`, `totalInputs = 0`, sem rolagem | **APROVADO** |
| **Rota `/experimente` Mobile (390/375/360)** | Responsividade dos cards e contatos | Sem cortes ou overflow em todas as viewports | **APROVADO** |

### 5.2. Evidências Gráficas Geradas
- `pos_publico_desktop_1280.png` (31.059 bytes)
- `pos_publico_rodape_zoom.png` (10.488 bytes)
- `pos_publico_mobile_390.png` (61.433 bytes)
- `pos_publico_mobile_375.png` (59.360 bytes)
- `pos_publico_mobile_360.png` (59.919 bytes)
- `pos_experimente_desktop_1280.png` (108.109 bytes)
- `pos_experimente_mobile_390.png` (216.766 bytes)
- `pos_experimente_mobile_375.png` (169.900 bytes)
- `pos_experimente_mobile_360.png` (179.838 bytes)

### 5.3. Suíte de Testes Automatizados e Linter
- **Pytest:** Suíte completa executada em banco de teste efêmero isolado:
  ```text
  48 passed in 23.39s (100% de sucesso)
  ```
- **Linter e Formatação (`git diff --check`):** **0 advertências / limpo**.

---

## 6. Arquivos Alterados no Repositório

1. `config.py`: Definição centralizada da constante `URL_EXPERIMENTE`.
2. `app.py`: Injeção de `url_experimente` e registro da rota pública `/experimente`.
3. `templates/index.html`: Inclusão da chamada comercial com link e marca no rodapé público.
4. `templates/experimente.html`: Criação da página provisória informativa.
5. `static/css/style.css`: Estilização Agillex Premium da chamada comercial e dos componentes de `/experimente`.

---

## 7. Conformidade com as Restrições

- **Produção VPS (`177.153.203.158`):** Nenhuma alteração, deploy ou conexão remota realizada.
- **Banco de Homologação (`scheduler_test_homologacao`):** Auditado pós-testes e mantido **100% limpo** (0 agendamentos, 0 serviços, 0 profissionais).
- **Banco de Dados Local Regular (`alllogic_scheduler`):** 100% intocado.
- **Painel Administrativo:** Preservado sem nenhuma alteração.
- **Regras Comerciais e Preços:** Não modificados.
- **Git:** Sem commit, push ou comandos destrutivos.
- **Servidor Local:** Ativo e respondendo em `http://127.0.0.1:5000/` e `http://127.0.0.1:5000/experimente`.
