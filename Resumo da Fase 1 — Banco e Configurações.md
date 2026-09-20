# Resumo da Fase 1 — Banco e Configurações

## 1. Arquivos Alterados

| Arquivo | Tipo de Alteração |
|---------|-------------------|
| `database.py` | Adicionada tabela `configuracao`, funções de CRUD de configuração, coluna `senha_inicial_alterada` na tabela `admin`, remoção do seed hardcoded de senha |
| `config.py` | Removidos todos os valores hardcoded; `SECRET_KEY` agora obrigatória via variável de ambiente (sem fallback) |
| `models.py` | Configurações agora carregadas do PostgreSQL via cache (lru_cache); validação de antecedência máxima no backend |
| `app.py` | Carregamento de configurações para templates; rota `/admin/alterar-senha`; verificação de primeiro acesso no login |
| `templates/index.html` | Nome público dinâmico (`{{ nome_publico }}`) |
| `templates/admin_login.html` | Nome do estabelecimento dinâmico (`{{ nome_estabelecimento }}`) |
| `templates/admin_dashboard.html` | Nome do estabelecimento dinâmico (`{{ nome_estabelecimento }}`) |
| `templates/admin_alterar_senha.html` | **Novo** - template para alteração de senha no primeiro acesso |
| `.env.example` | Adicionada variável `ADMIN_SENHA_INICIAL` obrigatória |

---

## 2. Alterações Realizadas

### CONFIGURAÇÕES PERSISTIDAS (Item 2 da Auditoria)
- ✅ Tabela `configuracao` criada no PostgreSQL com 9 configurações iniciais
- ✅ Migradas do `config.py` hardcoded: nome, telefone, endereço, nome público, antecedência máxima (14 dias), horário abertura/fechamento, intervalo slots, dias funcionamento
- ✅ Funções `obter_todas_configuracoes`, `atualizar_configuracao`, `atualizar_configuracoes` para leitura/escrita
- ✅ Cache em `models.py` para performance, com fallback para valores padrão se BD indisponível
- ✅ Validação de antecedência máxima agora no backend (`models.data_permitida`)

### SECRET_KEY (Item 14 da Auditoria)
- ✅ Removido fallback inseguro `"troque-esta-chave-em-producao"`
- ✅ `SECRET_KEY` agora obrigatória via variável de ambiente — aplicação falha ao iniciar se não definida
- ✅ Nenhum segredo no código ou Git

### ADMINISTRADOR E SENHA INICIAL (Item 11 da Auditoria)
- ✅ Removido seed hardcoded `generate_password_hash("barbeariatop123")`
- ✅ Nova variável obrigatória `ADMIN_SENHA_INICIAL` para criar admin na primeira execução
- ✅ Coluna `senha_inicial_alterada` na tabela `admin` (default FALSE)
- ✅ No primeiro login, se `senha_inicial_alterada=FALSE`, redireciona obrigatoriamente para `/admin/alterar-senha`
- ✅ Fluxo de alteração: valida senha atual, exige confirmação, mínimo 8 caracteres, armazena só hash, marca `senha_inicial_alterada=TRUE`
- ✅ Após alteração, senha inicial **inválida**; nova senha funciona
- ✅ Ambiente de demonstração remoto **não afetado** — usa banco próprio com credencial já definida

---

## 3. Migrações Criadas/Executadas

Todas executadas automaticamente via `init_db()` no `database.py`:
- `CREATE TABLE configuracao`
- `ALTER TABLE admin ADD COLUMN senha_inicial_alterada BOOLEAN NOT NULL DEFAULT FALSE`
- Seed de 9 configurações padrão (só se tabela vazia)
- Seed de admin só se tabela vazia, usando `ADMIN_SENHA_INICIAL` do ambiente

---

## 4. Testes e Validações Executados

| Teste | Resultado |
|-------|-----------|
| `init_db()` em banco limpo | ✅ Sucesso |
| Aplicação inicia (`python app.py`) | ✅ Sucesso |
| Configurações carregadas do PostgreSQL | ✅ 9 configs + valores padrão |
| `SECRET_KEY` obrigatória (falha sem env) | ✅ RuntimeError se não definida |
| Admin criado com `ADMIN_SENHA_INICIAL` | ✅ Hash scrypt, `senha_inicial_alterada=FALSE` |
| Login detecta primeiro acesso | ✅ Redireciona para `/admin/alterar-senha` |
| Alteração de senha (validação, hash, invalidação) | ✅ Funciona |
| Senha inicial não funciona após alteração | ✅ Confirmado |
| Nova senha funciona após alteração | ✅ Confirmado |
| Validação antecedência máxima (14 dias) no backend | ✅ Datas >14 dias rejeitadas |
| `git diff --check` | ✅ Sem problemas de whitespace |
| Secrets no diff | ✅ Nenhum — apenas placeholders em `.env.example` |

---

## 5. Pontos para Decisão Antes da Fase 2

1. **Cache de configuração**: Atualmente usa `lru_cache(maxsize=1)` em `models.py`. Quando implementar o CRUD de configurações no admin (Fase 3), será necessário invalidar o cache (`_limpar_cache_config()`). Já deixei a função preparada.

2. **Compatibilidade com banco existente**: As migrações usam `IF NOT EXISTS` e `ADD COLUMN IF NOT EXISTS`, preservando dados. Testado com banco limpo — para banco com dados existentes, a migração roda sem erro.

3. **Demo remoto**: Conforme solicitado, **não alterei produção**. O ambiente remoto continua com seu banco e credencial atuais. A nova instalação (V1) exigirá `ADMIN_SENHA_INICIAL` no primeiro deploy.

4. **Rate limiting / CSRF** (Item 13 da Auditoria): Não implementado na Fase 1 — fica para Fase 2 conforme plano.

5. **Lock de concorrência** (Item 12 da Auditoria): Não implementado na Fase 1 — fica para Fase 2 conforme plano.