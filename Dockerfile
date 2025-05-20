FROM python:3.12-slim

# Criar diretório de trabalho
WORKDIR /app

# Copiar arquivos de requisitos e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app.py .

# Criar um arquivo technologies.json vazio válido para evitar problemas iniciais
RUN echo "{}" > technologies.json

# Criar script de inicialização
RUN echo '#!/bin/bash\n\
echo "Iniciando aplicação Wappalyzer API..."\n\
\n\
# O próprio app.py vai baixar o technologies.json na inicialização\n\
exec python app.py\n\
' > start.sh && chmod +x start.sh

# Expor porta
EXPOSE 3000

# Comando para iniciar a aplicação
CMD ["./start.sh"]
