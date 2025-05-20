FROM python:3.12-slim

# Configurar diretório de trabalho
WORKDIR /app

# Instalar curl usando apt-get e garantir que apt-get funcione
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar arquivos de requisitos e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app.py .

# Criar um script para baixar o arquivo technologies.json
RUN echo '#!/bin/bash\n\
if [ ! -f technologies.json ]; then\n\
  echo "Baixando technologies.json..."\n\
  curl -s -o technologies.json https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies.json\n\
  echo "Download concluído."\n\
fi\n\
exec python app.py\n\
' > start.sh && chmod +x start.sh

# Expor porta
EXPOSE 3000

# Comando para iniciar a aplicação
CMD ["./start.sh"]
