# main.py
import functions_framework
from google.cloud import spanner
from google.cloud import aiplatform
from data import characters_data, spells_data
import logging
import os
import uuid

# --- CONFIGURAÇÕES E VARIÁVEIS DE AMBIENTE (Sem inicialização Spanner/AI aqui) ---
PROJECT_ID = os.environ.get('GCP_PROJECT')
INSTANCE_ID = os.environ.get('INSTANCE_ID')
DATABASE_ID = os.environ.get('DATABASE_ID')
REGION = os.environ.get('REGION', 'us-central1')
EMBEDDING_MODEL = "text-embedding-gecko@001" 

logging.basicConfig(level=logging.INFO)

# --- FUNÇÕES CORE (DDL, EMBEDDING, INSERÇÃO) ---

def get_spanner_client(project_id, instance_id, database_id):
    """Inicializa e retorna o objeto database (FORA DO ESCOPO GLOBAL)."""
    try:
        spanner_client = spanner.Client(project=project_id)
        instance = spanner_client.instance(instance_id)
        database = instance.database(database_id)
        return database
    except Exception as e:
        logging.error(f"ERRO DE CONEXÃO SPANNER: {e}")
        # Isto é crucial: se a conexão falhar, o erro será capturado dentro do TRY/EXCEPT da função HTTP.
        raise e 

def get_embedding(text_content, project_id, region):
    """Implementação da chamada à Vertex AI (Também movida)."""
    ai_client = aiplatform.PredictionServiceClient()
    endpoint = f"projects/{project_id}/locations/{region}/publishers/google/models/{EMBEDDING_MODEL}"
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

# --- Funções de Processamento de Dados (Requerem atualização da função get_embedding) ---

def process_spells(spells_data, project_id, region):
    spells_mutations = []
    columns = ['SpellID', 'Name', 'OtherName', 'Pronunciation', 'SpellType', 'Description', 'Mention', 'Etymology', 'Note', 'Embedding']
    for spell in spells_data:
        text_to_embed = f"Feitiço: {spell.get('name', '')}. Tipo: {spell.get('spell_type', '')}. Descrição: {spell.get('description', '')}. Efeito: {spell.get('mention', '')}"
        # Chama a função com os parâmetros do projeto
        spell_embedding = get_embedding(text_to_embed, project_id, region) 
        spells_mutations.append((
            spell.get('id'), spell.get('name'), spell.get('other_name'), 
            spell.get('pronunciation'), spell.get('spell_type'), spell.get('description'), 
            spell.get('mention'), spell.get('etymology'), spell.get('note'), spell_embedding
        ))
    return 'Spells', columns, spells_mutations

def process_characters(characters_data, project_id, region):
    characters_mutations = []
    columns = ['CharacterID', 'Name', 'Birth', 'Death', 'Species', 'Ancestry', 'Gender', 'HairColor', 'EyeColor', 'Wand', 'Patronus', 'House', 'AssociatedGroups', 'BooksFeaturedIn', 'Embedding']
    for item in characters_data:
        assoc_groups = item.get('associated_groups') or []
        text_to_embed = (
            f"Personagem: {item.get('name', '')}. Casa: {item.get('house', '')}. "
            f"Espécie: {item.get('species', '')}. Ancestralidade: {item.get('ancestry', '')}. "
            f"Grupos: {', '.join(assoc_groups)}"
        )
        # Chama a função com os parâmetros do projeto
        char_embedding = get_embedding(text_to_embed, project_id, region)
        characters_mutations.append((
            item.get('id'), item.get('name'), item.get('birth'), item.get('death'), item.get('species'), 
            item.get('ancestry'), item.get('gender'), item.get('hair_color'), item.get('eye_color'), 
            item.get('wand'), item.get('patronus'), item.get('house'), assoc_groups, item.get('books_featured_in'), char_embedding
        ))
    return 'Characters', columns, characters_mutations

def ingest_relations():
    # Lógica de mapeamento de relações (não depende do cliente Spanner aqui)
    known_relations = {
        'Harry Potter': 96, 'Hermione Granger': 7, 'Severus Snape': 252, 'Draco Malfoy': 277,
    }
    char_id_map = {c['name']: c['id'] for c in characters_data}
    relations = []
    for char_name, spell_id in known_relations.items():
        char_id = char_id_map.get(char_name)
        if char_id:
             relations.append((char_id, spell_id, f"Feitiço crucial do personagem {char_name}."))
    return 'CharacterSpells', ['CharacterID', 'SpellID', 'MentionContext'], list(set(relations))


def run_ingestion_transaction(database, table_name, columns, values):
    if not values:
        logging.warning(f"Nenhum dado para inserir na tabela {table_name}.")
        return
    def insert_batch(txn):
        txn.insert(table=table_name, columns=columns, values=values)
    database.run_in_transaction(insert_batch)
    logging.info(f"Sucesso na inserção de {len(values)} linhas na tabela {table_name}.")


# --- FUNÇÃO PRINCIPAL (Ponto de entrada) ---

@functions_framework.http
def ingest_harry_potter_data(request):
    """Endpoint principal: Cria Grafo DDL e insere dados enriquecidos."""
    try:
        # ** INICIALIZAÇÃO LENTA AQUI **
        database = get_spanner_client(PROJECT_ID, INSTANCE_ID, DATABASE_ID)
        logging.info("Conexão Spanner estabelecida com sucesso.")
        
        # 1. Cria a estrutura do Grafo
        create_property_graph(database)

        # 2. Processar e Inserir Dados Enriquecidos
        
        # Inserção de Feitiços
        table_s, cols_s, vals_s = process_spells(spells_data, PROJECT_ID, REGION)
        run_ingestion_transaction(database, table_s, cols_s, vals_s)
        
        # Inserção de Personagens
        table_c, cols_c, vals_c = process_characters(characters_data, PROJECT_ID, REGION)
        run_ingestion_transaction(database, table_c, cols_c, vals_c)
        
        # Inserção de Relações
        table_r, cols_r, vals_r = ingest_relations()
        run_ingestion_transaction(database, table_r, cols_r, vals_r)
        
        return ('Ingestão de dados e criação do Grafo concluídas com sucesso! Verifique os logs para detalhes da carga.', 200)

    except Exception as e:
        logging.error(f'ERRO FATAL DE EXECUÇÃO: {e}', exc_info=True)
        return (f'Erro interno durante a ingestão. Verifique os logs do Cloud Run: {e}', 500)
