# main.py
import functions_framework
from google.cloud import spanner
from google.cloud import aiplatform
from data import characters_data, spells_data 
import logging
import os

# Variáveis de Configuração
PROJECT_ID = os.environ.get('GCP_PROJECT')
INSTANCE_ID = "demo-hp" 
DATABASE_ID = "hp-database"     
REGION = os.environ.get('FUNCTION_REGION', 'us-central1') # Pega a região da função
EMBEDDING_MODEL = "text-embedding-gecko@001" 

logging.basicConfig(level=logging.INFO)

# --- FUNÇÕES CORE (DDL, EMBEDDING, INSERÇÃO) ---

def get_embedding(text_content):
    # Implementação da chamada à Vertex AI
    ai_client = aiplatform.PredictionServiceClient()
    endpoint = f"projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/{EMBEDDING_MODEL}"
    instance = aiplatform.types.instance.TextEmbeddingModel.to_dict({"content": text_content})
    request = aiplatform.types.PredictRequest(endpoint=endpoint, instances=[instance])
    try:
        response = ai_client.predict(request=request)
        return response.predictions[0]["embedding"]
    except Exception as e:
        logging.error(f"Erro ao gerar embedding: {e}")
        return None

def create_property_graph(database):
    """Executa a DDL para criar/substituir a estrutura do grafo."""
    graph_ddl = """
    CREATE OR REPLACE PROPERTY GRAPH HPGRAH
    NODE TABLES (
        Characters
            KEY (CharacterID),
            PROPERTIES (Name, House, Species, Ancestry),
        Spells
            KEY (SpellID),
            PROPERTIES (Name, SpellType, Description)
    )
    EDGE TABLES (
        CharacterSpells AS UsedSpell
            KEY (CharacterID, SpellID),
            SOURCE (CharacterID) REFERENCES Characters,
            DESTINATION (SpellID) REFERENCES Spells,
            PROPERTIES (MentionContext)
    )
    """
    operation = database.update_ddl([graph_ddl])
    operation.result() 
    logging.info("PROPERTY GRAPH HPGRAH criado/atualizado com sucesso via SDK.")

# Funções de Processamento/Ingestão (process_spells, process_characters, ingest_relations, run_in_transaction)
# **NOTA:** Inclua as implementações completas dessas funções do nosso último guia aqui.

# --- FUNÇÃO PRINCIPAL ---

@functions_framework.http
def ingest_harry_potter_data(request):
    """Endpoint principal: Cria Grafo DDL e insere dados enriquecidos."""
    try:
        spanner_client = spanner.Client(project=PROJECT_ID)
        instance = spanner_client.instance(INSTANCE_ID)
        database = instance.database(DATABASE_ID)
        
        # 1. Cria a estrutura do Grafo
        create_property_graph(database)

        # 2. Processar e Inserir Dados Enriquecidos
        
        # Inserção de Feitiços
        table_s, cols_s, vals_s = process_spells(spells_data)
        run_ingestion_transaction(database, table_s, cols_s, vals_s)
        
        # Inserção de Personagens
        table_c, cols_c, vals_c = process_characters(characters_data)
        run_ingestion_transaction(database, table_c, cols_c, vals_c)
        
        # Inserção de Relações
        table_r, cols_r, vals_r = ingest_relations()
        run_ingestion_transaction(database, table_r, cols_r, vals_r)
        
        return ('Ingestão de dados e criação do Grafo concluídas com sucesso!', 200)

    except Exception as e:
        logging.error(f'Erro fatal na ingestão: {e}', exc_info=True)
        return (f'Erro interno durante a ingestão: {e}', 500)
