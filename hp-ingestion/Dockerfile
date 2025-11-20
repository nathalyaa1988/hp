# Define a imagem base: Essencial para rodar Python 3.11
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos de dependência e os instala
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt --no-cache-dir

# Copia o restante do código (incluindo main.py e data.py)
COPY . .

# Variáveis de ambiente
ENV INSTANCE_ID="demo-hp"
ENV DATABASE_ID="hp-database"
ENV PORT 8080
EXPOSE 8080

# Comando para iniciar o servidor Flask
# Isso garante que o servidor Flask (que chamará o main.py via gatilho HTTP) esteja rodando
CMD ["functions-framework", "--target", "ingest_harry_potter_data", "--port", "8080"]
# Dockerfile na pasta hp-ingestion/
# ... (outras etapas)


