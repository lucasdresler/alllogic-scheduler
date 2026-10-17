# Relatório de Migração de Infraestrutura — AllLogic Scheduler (Agillex Agenda) para Oracle Cloud

**Data:** 16/10/2026 (BRT) / 17/10/2026 (UTC)  
**Projeto:** AllLogic Scheduler (Agillex Agenda) — `~/AllLogic/Projetos/app-agendamento`  
**Origem:** VPS KingHost (`177.153.203.158`)  
**Destino:** VPS Oracle Cloud Infrastructure (`136.248.113.145`)  
**Commit Publicado:** `783945e` (`origin/main`)  
**Status da Operação:** **IMPLANTAÇÃO CONCLUÍDA NA ORACLE CLOUD — PRONTO PARA VIRADA DE DNS**

---

## 1. Justificativa Estratégica da Migração

1. **Unificação do Ecossistema Agillex:**
   - O **Agillex Atendimento (IA no WhatsApp)** e o **Agillex Hub (MATRIZ OS)** já residem na Oracle Cloud (`136.248.113.145`).
   - Ao mover a Agenda para o mesmo host, as chamadas entre o Agente de IA e o motor de agendamento passam a ocorrer via rede interna em Docker bridge (`matriz-network`), com latência na faixa de microssegundos e sem tráfego de rede pública.

2. **Folga de Recursos e Escalabilidade:**
   - A máquina da Oracle Cloud possui **5.8 GiB de RAM física (4.5 GiB livres)**, processamento dedicado e 87 GB de disco livre, operando com total folga.
   - A KingHost VPS (3.8 GiB) fica aliviada para suas rotinas e automações n8n.

3. **Limpeza de Dados de Teste Autorizada pelo Fundador:**
   - Preservadas as configurações do sistema (`configuracao`), serviços (`servico`), estabelecimento padrão (`estabelecimento`) e as credenciais de acesso do administrador (`admin` — `lucasdresler@live.com`).
   - Apagados com `TRUNCATE CASCADE` os agendamentos, clientes e profissionais de teste prévios.

---

## 2. Ações Executadas na Oracle Cloud

1. **Provisionamento do Banco no PostgreSQL 16 da Oracle:**
   - Executado `CREATE DATABASE alllogic_scheduler OWNER matriz_admin;` no container `matriz-postgres`.
   - Schema e dados base migrados com integridade.
   - Truncadas as tabelas de exemplo conforme autorização:
     ```sql
     TRUNCATE TABLE agendamento, agendamento_servico, agendamento_status_historico,
                    agendamento_reagendamento, cliente, profissional,
                    profissional_servico, profissional_disponibilidade CASCADE;
     ```

2. **Estrutura de Aplicação em `/opt/alllogic/stacks/scheduler`:**
   - Repositório clonado e sincronizado no commit `783945e`.
   - Arquivo `.env` configurado com permissões estritas `chmod 600`.
   - Conexão com Evolution API local na Oracle (`https://wa.alllogiconline.com.br`).
   - Arquivo `compose.yaml` integrado às redes `proxy` e `matriz-saas_matriz-network`.

3. **Compilação e Inicialização:**
   - Build da imagem Docker finalizado com sucesso.
   - Container `alllogic-scheduler` iniciado com 2 workers Gunicorn ativos.

---

## 3. Validação dos Testes de Fumaça (Smoke Tests)

Testes executados localmente no host da Oracle via Traefik e Gunicorn:

| Rota / Endpoint | Código HTTP | Resultado |
| :--- | :---: | :--- |
| `https://agenda.alllogiconline.com.br/` (Home / Agendamento) | **200 OK** | Página inicial pública renderizada |
| `https://agenda.alllogiconline.com.br/admin/login` | **200 OK** | Formulário de login ativo com CSRF e cookies de sessão |
| `/api/services?estabelecimento_id=1` | **200 OK** | Retorno JSON com os 7 serviços ativos |

---

## 4. Próxima Etapa: Virada de DNS no Cloudflare

Para concluir a migração pública:
- Acessar o painel do **Cloudflare** para o domínio `alllogiconline.com.br`.
- Alterar o registro **A** do subdomínio `agenda`:
  - **De:** `177.153.203.158` (KingHost)
  - **Para:** `136.248.113.145` (Oracle Cloud)
- Como a propagação no Cloudflare leva poucos segundos e o Traefik da Oracle já está com os certificados e rotas prontos, a troca será praticamente instantânea e sem indisponibilidade.
EOF
