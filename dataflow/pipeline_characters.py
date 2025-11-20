# -*- coding: utf-8 -*-
"""
Pipeline do Apache Beam para ingestão de dados de Personagens 
(Characters) do Cloud Storage para o Cloud Spanner.
"""
import argparse
import json
import logging
from typing import Dict, List, Any

import apache_beam as beam
from apache_beam.io.gcp.spanner import WriteToSpanner
from apache_beam.options.pipeline_options import PipelineOptions

# Configurações do Spanner - Serão passadas como argumentos do pipeline
SPANNER_INSTANCE = "demo-hp" 
SPANNER_DATABASE = "hp-database"

# Configurações de Colunas - Deve espelhar a DDL do Spanner
CHARACTER_TABLE_COLUMNS = [
    'CharacterID', 'Name', 'Birth', 'Death', 'Species', 'Ancestry', 'Gender',
    'HairColor', 'EyeColor', 'Wand', 'Patronus', 'House', 'AssociatedGroups',
    'BooksFeaturedIn', 'Embedding'
]

def parse_json_to_spanner_row(element: str) -> Dict[str, Any]:
    """
    Transforma uma linha JSON (string) em um objeto de mutação para o Spanner.
    
    Aplica as transformações necessárias para corresponder ao schema, incluindo
    a serialização de listas e a criação de embeddings mock.
    """
    try:
        data = json.loads(element)
        
        # 1. Preparar listas para ARRAY<T> do Spanner
        associated_groups = data.get('associated_groups') or []
        books_featured_in = data.get('books_featured_in') or []

        # 2. Simulação de Embedding (Substituir por chamada real em produção)
        # O vetor deve ter 768 floats, por exemplo.
        # Aqui, usamos um vetor simples para garantir a estrutura ARRAY<FLOAT64>.
        embedding_mock = [0.0] * 768 
        
        # 3. Mapear para o formato de tupla do Spanner WriteToSpanner
        # A ordem deve corresponder exatamente a CHARACTER_TABLE_COLUMNS
        row = (
            data.get('id'), # Assumimos que 'id' é o INT64 CharacterID
            data.get('name'),
            data.get('birth'),
            data.get('death'),
            data.get('species'),
            data.get('ancestry'),
            data.get('gender'),
            data.get('hair_color'),
            data.get('eye_color'),
            data.get('wand'),
            data.get('patronus'),
            data.get('house'),
            associated_groups,
            books_featured_in,
            embedding_mock
        )
        return {"table": "Characters", "columns": CHARACTER_TABLE_COLUMNS, "values": row}
    except Exception as e:
        logging.error(f"Falha ao processar a linha JSON: {e} - Dados: {element}")
        # Retorna None para descartar linhas com erro
        return None

def run(argv=None):
    """Função principal para execução do pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input_path',
        dest='input_path',
        required=True,
        help='Caminho do Cloud Storage para o arquivo de entrada (ex: gs://seu-bucket/characters.jsonl).'
    )
    parser.add_argument(
        '--spanner_instance',
        dest='spanner_instance',
        default=SPANNER_INSTANCE,
        help='ID da instância do Cloud Spanner.'
    )
    parser.add_argument(
        '--spanner_database',
        dest='spanner_database',
        default=SPANNER_DATABASE,
        help='ID do banco de dados do Cloud Spanner.'
    )
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    # Adicionar o Dataflow Runner
    pipeline_args.extend([
        '--runner=DataflowRunner',
        '--project=demos-478719', # Substitua pelo seu ID de Projeto
        '--region=us-central1',   # Substitua pela sua região
        '--temp_location=gs://seu-bucket/temp_dataflow/', # Crie um bucket de temp
        '--staging_location=gs://seu-bucket/staging_dataflow/' # Crie um bucket de staging
    ])

    pipeline_options = PipelineOptions(pipeline_args)
    
    with beam.Pipeline(options=pipeline_options) as p:
        
        # Carrega o arquivo JSON Lines do Cloud Storage
        lines = p | 'ReadFromGCS' >> beam.io.ReadFromText(known_args.input_path)
        
        # Transforma cada linha em um objeto de mutação do Spanner
        mutations = (
            lines
            | 'ParseJson' >> beam.Map(parse_json_to_spanner_row)
            | 'FilterErrors' >> beam.Filter(lambda x: x is not None)
        )
        
        # Escreve no Cloud Spanner
        mutations | 'WriteToSpanner' >> WriteToSpanner(
            instance_id=known_args.spanner_instance,
            database_id=known_args.spanner_database,
            project_id=SPANNER_INSTANCE # Usa o project_id para a autenticação
        )

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
