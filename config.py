# Configurações centrais do negócio — carregadas do PostgreSQL

import os

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY não definida. "
        "Defina a variável de ambiente SECRET_KEY para iniciar a aplicação."
    )