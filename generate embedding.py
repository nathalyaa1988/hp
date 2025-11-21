import json
from google.cloud import spanner
from google.cloud import aiplatform
import numpy as np  # Para lidar com arrays de floats

# Inicializa a plataforma AI
aiplatform.init(location="us-central1")

# ID do Endpoint dedicado fornecido
ENDPOINT_ID = "mg-endpoint-619db8cd-0722-4dc2-91a2-eaa7fe473936"
REGION = "us-central1"

# Função para gerar embeddings de texto usando o endpoint dedicado
def embed(text):
    if not text or text.strip() == "":  # Verifica se o texto está vazio ou contém apenas espaços
        raise ValueError("O texto fornecido está vazio ou inválido.")
    
    # Conecta ao endpoint dedicado
    endpoint = aiplatform.Endpoint(ENDPOINT_ID)
    
    # Faz a previsão no endpoint com o texto fornecido
    response = endpoint.predict(instances=[{"inputs": text}])
    
    # Obtém o vetor de embeddings gerado pela previsão
    embedding = response.predictions[0]
    
    # Verificar o formato do vetor de embeddings
    if isinstance(embedding, list) and isinstance(embedding[0], list):
        # Descompacta o vetor para garantir que seja uma lista de floats (ARRAY<FLOAT64>)
        embedding = embedding[0]  # Descompactando a lista interna
        print(f"Embedding gerado: {embedding[:5]}...")  # Exibe os primeiros 5 valores para visualização
        
        # Certifica-se de que o embedding é uma lista de floats e converte para FLOAT64
        embedding_float64 = np.array(embedding, dtype=np.float64).tolist()  # Convertendo para lista de floats (FLOAT64)
        return embedding_float64
    else:
        raise ValueError("O formato do embedding gerado não é válido. Esperado uma lista de floats.")

# Função para carregar JSON
def load_json(path):
    with open(path) as f:
        return json.load(f)

# Carregar Feitiços e Personagens
spells = load_json("spells.json")
characters = load_json("characters.json")

# Conectar com o Spanner
client = spanner.Client()
instance = client.instance("demo-hp")
db = instance.database("hp-database")

# Embeddings para Feitiços
with db.snapshot() as snap:
    rows = snap.execute_sql("SELECT SpellID, Description FROM Spells")
    for row in rows:
        sid, desc = row
        # Gera o vetor para a descrição do feitiço
        try:
            vector = embed(desc or "")
            with db.batch() as batch:
                # Inserção no banco de dados com a lista de floats (FLOAT64)
                batch.update(
                    table="Spells",
                    columns=("SpellID", "Embedding"),
                    values=[(sid, vector)]
                )
        except ValueError as e:
            print(f"Atenção: Falha ao gerar embedding para o feitiço {sid}: {e}")

# Embeddings para Personagens
with db.snapshot() as snap:
    rows = snap.execute_sql("SELECT CharacterID, Description FROM Characters")
    for row in rows:
        cid, desc = row
        # Gera o vetor para a descrição do personagem
        try:
            vector = embed(desc or "")
            with db.batch() as batch:
                # Inserção no banco de dados com a lista de floats (FLOAT64)
                batch.update(
                    table="Characters",
                    columns=("CharacterID", "Embedding"),
                    values=[(cid, vector)]
                )
        except ValueError as e:
            print(f"Atenção: Falha ao gerar embedding para o personagem {cid}: {e}")

print("Embeddings gerados com sucesso!")
