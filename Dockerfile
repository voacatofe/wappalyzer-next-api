FROM python:3.12-slim

# Criar diretório de trabalho
WORKDIR /app

# Copiar arquivos de requisitos e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação e arquivos de dados
COPY app.py .
COPY technologies.json .

# Expor porta
EXPOSE 3000

# Comando para iniciar a aplicação
CMD ["python", "app.py"]
