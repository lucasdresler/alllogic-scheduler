# AllLogic Scheduler

Primeiro aplicativo oficial da plataforma AllLogic.

## Descrição

Sistema de agendamento online desenvolvido em Flask para demonstração e implantação em clientes.

## Tecnologias

- Python 3.12
- Flask
- Gunicorn
- Docker
- Traefik
- PostgreSQL

## Estrutura

```text
.
├── app.py
├── config.py
├── database.py
├── models.py
├── requirements.txt
├── Dockerfile
├── .env.example
├── static/
└── templates/
```

## Execução

O projeto possui `Dockerfile` para execução da aplicação em container.

A aplicação também possui configuração de execução com Gunicorn por meio de serviço systemd e proxy reverso Nginx.

A definição da arquitetura de publicação em produção deverá seguir a infraestrutura homologada para o ambiente onde o Scheduler for implantado.

## Status

🚧 Em desenvolvimento – Projeto Fênix / AllLogic
