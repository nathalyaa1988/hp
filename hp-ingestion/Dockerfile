
# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos de dependência e os instala
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt --no-cache-dir

# Copia o restante do código (incluindo app.py)
COPY . .

# Variáveis de ambiente
ENV INSTANCE_ID="demo-hp"
ENV DATABASE_ID="hp-database"
ENV PORT 8080
EXPOSE 8080

# Comando para iniciar o servidor Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
