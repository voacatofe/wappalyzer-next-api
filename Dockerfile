FROM python:3.12-slim

# Instalação de dependências do sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    which curl  # Verificar se curl está instalado

# Criar diretório de trabalho
WORKDIR /app

# Copiar arquivos de requisitos e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app.py .

# Criar um arquivo technologies.json vazio válido para evitar problemas
RUN echo "{}" > technologies.json

# Criar script de inicialização com verificação de curl
RUN echo '#!/bin/bash\n\
echo "Verificando instalação do curl..."\n\
if ! command -v curl > /dev/null; then\n\
  echo "ERRO: curl não está instalado, instalando agora..."\n\
  apt-get update && apt-get install -y curl && apt-get clean\n\
fi\n\
\n\
echo "Baixando technologies.json..."\n\
curl -s -o technologies.json.new https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies.json\n\
\n\
if [ $? -eq 0 ]; then\n\
  mv technologies.json.new technologies.json\n\
  echo "Download concluído com sucesso."\n\
else\n\
  echo "Falha ao baixar o arquivo. Usando arquivo padrão se existir."\n\
fi\n\
\n\
exec python app.py\n\
' > start.sh && chmod +x start.sh

# Expor porta
EXPOSE 3000

# Comando para iniciar a aplicação
CMD ["./start.sh"]
