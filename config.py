# Configurações centrais do negócio — usadas tanto pela página pública quanto pelo painel admin

import os

HORARIO_ABERTURA = "09:00"
HORARIO_FECHAMENTO = "19:00"
INTERVALO_SLOT_MINUTOS = 30
DIAS_FUNCIONAMENTO = [0, 1, 2, 3, 4, 5]  # segunda(0) a sábado(5); domingo(6) fechado
DIAS_ANTECEDENCIA_AGENDAMENTO = 14  # quantos dias pra frente o cliente pode marcar

# Em produção, defina a variável de ambiente SECRET_KEY (ex: no arquivo de serviço systemd).
# O valor abaixo só é usado como fallback em ambiente de desenvolvimento local.
SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
