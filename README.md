App de Agendamento

Aplicação web de agendamento online da AllLogic, inicialmente direcionada a pequenos negócios e empresas de bairro.

Status

🚧 Em evolução — desenvolvimento da V1 Comercial.

O projeto parte de uma aplicação funcional existente e está sendo evoluído de forma incremental.

Objetivo

Oferecer ao pequeno negócio uma solução simples para:

disponibilizar serviços;
cadastrar profissionais;
configurar horários de atendimento;
receber agendamentos online;
administrar a agenda;
manter o histórico de clientes e atendimentos.
Visão de Evolução

A primeira etapa é consolidar uma solução comercial de agendamento.

A arquitetura deverá permitir evolução futura para recursos de relacionamento com clientes e CRM, sem antecipar funcionalidades que ainda não foram priorizadas.

Stack Atual
Python
Flask
SQLite
HTML
CSS
JavaScript
Gunicorn
Nginx
Estrutura
app-agendamento/
├── app.py
├── config.py
├── database.py
├── models.py
├── requirements.txt
├── static/
├── templates/
├── barbearia-top.service
├── nginx_barbearia_top.conf
├── FOUNDATION.md
├── README.md
└── .gitignore
Desenvolvimento

O desenvolvimento deve ocorrer em ambiente local/homologação.

A produção existente não deve ser alterada diretamente durante o desenvolvimento.

Documentação
FOUNDATION.md — princípios e fundamentos do projeto.
README.md — visão geral e orientação inicial.
AGENTS.md — regras operacionais para desenvolvimento com agentes e IA.
Projeto

AllLogic — Engenharia de Soluções Digitais

O App de Agendamento é um projeto independente dentro da AllLogic.

Não confundir com o projeto OfertaIA.
