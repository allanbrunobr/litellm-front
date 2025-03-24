FROM python:3.12-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar arquivos do projeto
COPY . .

# Configurar o SQLite como banco de dados padrão
ENV DATABASE_URL="file:./litellm_keys.db"
ENV LITELLM_HOST="http://localhost:8000"
ENV LITELLM_MASTER_KEY="metatron123"
ENV PORT=8080
ENV FLASK_ENV=production

# Executar configuração inicial
RUN mkdir -p /app/static/css /app/static/js /app/templates
RUN python -c "import web_manager; web_manager.init_app()"

# Expor a porta
EXPOSE 8080

# Iniciar o servidor web
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 web_manager:app
