FROM python:3.12-slim

# Configurar diretório de trabalho
WORKDIR /app

# Copiar arquivos de requisitos e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app.py .

# Expor porta
EXPOSE 3000

# Comando para iniciar a aplicação
CMD ["python", "app.py"]
