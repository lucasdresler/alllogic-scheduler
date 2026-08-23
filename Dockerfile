FROM python:3.12-slim

# Evita geração de arquivos .pyc e força logs imediatos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Diretório da aplicação
WORKDIR /app

# Instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia toda a aplicação
COPY . .

# Porta utilizada pelo Gunicorn
EXPOSE 8000

# Inicializa a aplicação
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]
