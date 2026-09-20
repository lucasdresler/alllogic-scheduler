# Decisão de Documentação — Fase 1

## Análise baseada no AGENTS.md

### Regras Aplicáveis (AGENTS.md §21, §22, §24)

| Regra | Aplicação |
|-------|-----------|
| **§21** "Mudanças relevantes de arquitetura, banco de dados, infraestrutura ou comportamento devem ser documentadas" | Auditorias, resumos de implementação, correções de problemas críticos |
| **§21** "A documentação do projeto deve ser versionada junto ao código quando fizer parte do repositório" | Arquivos na raiz do projeto que registram decisões técnicas |
| **§21** "Documentações específicas devem ser criadas quando a complexidade ou importância do assunto justificar" | Auditoria técnica (17 itens), plano de fases, decisões de escopo |
| **§22** Hierarquia: AGENTS.md > FOUNDATION.md > README.md > **documentações específicas** | Estes arquivos são "documentações específicas" do projeto |
| **§24** "Decisões permanentes de produto, arquitetura, escopo ou operação devem ser registradas no documento apropriado" | Auditoria define escopo e sequência; Resumo registra implementação; Conclusão corrigida registra resolução de problemas |

---

## Classificação dos 5 Arquivos

| Arquivo | Classificação | Justificativa |
|---------|---------------|---------------|
| **AUDITORIA-TECNICA-V1.md** | ✅ **VERSIONAR** | Documenta a auditoria técnica completa: 17 itens classificados, plano de 4 fases, decisões de escopo (itens A/B/C/D), sequência oficial de evolução. Registra decisões permanentes de arquitetura e priorização. |
| **Resumo da Fase 1 — Banco e Configurações.md** | ✅ **VERSIONAR** | Registra o que foi implementado na Fase 1: arquivos alterados, migrações executadas, testes validados, pontos para decisão na Fase 2. É o "changelog" oficial da Fase 1. |
| **CONCLUSAO-REVISAO-FASE1-CORRIGIDA.md** | ✅ **VERSIONAR** | Documenta a resolução dos 3 problemas críticos/médios/menores encontrados na revisão inicial: conflitos de nomes, cache de configuração, fluxo primeiro_acesso. Registra validações técnicas e confirmação de conformidade. |
| **conclusao.md** | ❌ **TEMPORÁRIO** | Revisão inicial que identificou problemas **já corrigidos** e registrados em CONCLUSAO-REVISAO-FASE1-CORRIGIDA.md. Artefato intermediário superseded. Não adiciona informação permanente. |
| **REVISAO-FINAL-FASE1.md** | ❌ **TEMPORÁRIO** | Checklist de verificação pré-commit (git status, diff, secrets, escopo). Artefato de processo/quality gate. Não registra decisão técnica permanente — apenas valida prontidão. |

---

## Decisão Final

### ✅ Manter e Versionar (3 arquivos)
```
AUDITORIA-TECNICA-V1.md
Resumo da Fase 1 — Banco e Configurações.md
CONCLUSAO-REVISAO-FASE1-CORRIGIDA.md
```

### ❌ Remover / Não Versionar (2 arquivos)
```
conclusao.md
REVISAO-FINAL-FASE1.md
```

---

## Ação Recomendada

Antes do commit da Fase 1:

```bash
# Remover artefatos temporários
rm conclusao.md REVISAO-FINAL-FASE1.md

# Adicionar documentação permanente
git add AUDITORIA-TECNICA-V1.md "Resumo da Fase 1 — Banco e Configurações.md" CONCLUSAO-REVISAO-FASE1-CORRIGIDA.md

# Commit junto com o código da Fase 1
git commit -m "Fase 1: Banco e Configurações + documentação técnica"
```

---

## Rationale

- **Princípio §24**: "Decisões relevantes não devem depender exclusivamente do histórico de conversas" → Auditorias, resumos e correções ficam versionados
- **Princípio §21**: "Evitar complexidade prematura" → Não versionar checklists de processo ou revisões superseded
- **Hierarquia §22**: Estes são "documentações específicas" justificadas pela complexidade da auditoria (17 itens, 4 fases) e pela correção de problemas críticos