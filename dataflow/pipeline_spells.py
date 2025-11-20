# -*- coding: utf-8 -*-
"""
Pipeline do Apache Beam para ingestão de dados de Feitiços 
(Spells) do Cloud Storage para o Cloud Spanner.
"""
import argparse
import json
import logging
from typing import Dict, Any

import apache_beam as beam
from apache_beam.io.gcp.spanner import WriteToSpanner
from apache_beam.options.pipeline_options import PipelineOptions

# Configurações do Spanner - Serão passadas como argumentos do pipeline
SPANNER_INSTANCE = "demo-hp" 
SPANNER_DATABASE = "hp-database"

# Configurações de Colunas - Deve espelhar a DDL da tabela Spells
SPELLS_TABLE_COLUMNS = [
    'SpellID', 'Name', 'OtherName', 'Pronunciation', 'SpellType', 
    'Description', 'Mention', 'Etymology', 'Note', 'Embedding'
]

def parse_json_to_spanner_row(element: str) -> Dict[str, Any]:
    """
    Transforma uma linha JSON (string) em um objeto de mutação para a tabela Spells.
    
    Inclui a criação de embeddings mock (vetores).
    """
    try:
        data = json.loads(element)
        
        # Simulação de Embedding (Substituir por chamada real em produção)
        # Usamos um vetor simples de 768 floats para garantir a estrutura ARRAY<FLOAT64>.
        embedding_mock = [0.0] * 768 
        
        # Mapear para o formato de tupla do Spanner WriteToSpanner
        # A ordem deve corresponder exatamente a SPELLS_TABLE_COLUMNS
        row = (
            data.get('id'), 
            data.get('name'),
            data.get('other_name'),
            data.get('pronunciation'),
            data.get('spell_type'),
            data.get('description'),
            data.get('mention'),
            data.get('etymology'),
            data.get('note'),
            embedding_mock
        )
        # O nome da tabela deve ser o mesmo do seu DDL: Spells
        return {"table": "Spells", "columns": SPELLS_TABLE_COLUMNS, "values": row}
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
        help='Caminho do Cloud Storage para o arquivo de entrada (ex: gs://seu-bucket/spells.jsonl).'
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
        '--project=demos-478719', 
        '--region=us-central1',   
        '--temp_location=gs://seu-bucket/temp_dataflow/', 
        '--staging_location=gs://seu-bucket/staging_dataflow/' 
        # ATENÇÃO: As localizações temporárias acima DEVEM estar configuradas no seu Cloud Storage
    ])

    pipeline_options = PipelineOptions(pipeline_args)
    
    with beam.Pipeline(options=pipeline_options) as p:
        
        # Carrega o arquivo JSON Lines do Cloud Storage
        lines = p | 'ReadSpellsFromGCS' >> beam.io.ReadFromText(known_args.input_path)
        
        # Transforma cada linha em um objeto de mutação do Spanner
        mutations = (
            lines
            | 'ParseSpellsJson' >> beam.Map(parse_json_to_spanner_row)
            | 'FilterSpellsErrors' >> beam.Filter(lambda x: x is not None)
        )
        
        # Escreve no Cloud Spanner
        mutations | 'WriteSpellsToSpanner' >> WriteToSpanner(
            instance_id=known_args.spanner_instance,
            database_id=known_args.spanner_database,
            project_id=SPANNER_INSTANCE 
        )

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
