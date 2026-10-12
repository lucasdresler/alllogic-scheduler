# Relatório — Substituição de E-mail por WhatsApp no Botão de Teste Grátis

**Data:** 12 de Outubro de 2026  
**Projeto:** Agillex Agenda (`~/AllLogic/Projetos/app-agendamento`)  
**Arquivo modificado:** [templates/experimente.html](file:///home/dresler/AllLogic/Projetos/app-agendamento/templates/experimente.html)

---

## 1. Objetivo da Alteração

Atualizar exclusivamente o destino do botão principal da página `templates/experimente.html`, substituindo o link `mailto:` pelo canal direto do WhatsApp comercial da AllLogic Online, permitindo contato ágil e imediato pelo aplicativo de mensagens.

---

## 2. Detalhes da Implementação

### 2.1. Botão Principal Atualizado

- **Texto Preservado:** `Iniciar 14 dias de teste grátis`
- **Novo Destino (`href`):**
  `https://wa.me/5511966381915?text=Ol%C3%A1!%20Gostaria%20de%20iniciar%20meu%20teste%20gratuito%20de%2014%20dias%20do%20Agillex%20Agenda.`
- **Mensagem Pré-preenchida:** Manifestação direta de interesse no início do teste gratuito de 14 dias do produto.
- **Abertura Segura em Nova Aba:** Inclusão dos atributos `target="_blank"` e `rel="noopener noreferrer"`.
- **Acessibilidade:** `title="Solicitar início do teste gratuito pelo WhatsApp"`.
- **Classes e Estilos Preservados:** `btn-primario btn-iniciar-teste` sem qualquer alteração CSS ou de posicionamento.

---

## 3. Validação Executada

1. **Conferência Textual:** O texto renderizado permanece estritamente `Iniciar 14 dias de teste grátis`.
2. **Conferência de URL e Parâmetros:** Link do WhatsApp validado contra o número comercial oficial `(11) 96638-1915` (`5511966381915`) e mensagem URL-encoded correta.
3. **Preservação do Escopo:**
   - Textos introdutórios, badge, cards de benefícios e selo “Sem necessidade de cartão de crédito” preservados.
   - Demais canais de contato e rodapé preservados.
   - Nenhuma alteração em rotas ou lógica do servidor.
4. **Verificação de Código (`git diff --check`):**
   - Executado e finalizado com código 0 (zero erros de sintaxe ou espaços em branco).
5. **Diretrizes de Governança:**
   - Nenhum commit, push ou deploy realizado.
   - Nenhuma alteração no arquivo `.env` ou em produção.
