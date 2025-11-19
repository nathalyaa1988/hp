# app.py
from flask import Flask, request, jsonify
from google.cloud import spanner
import os

app = Flask(__name__)

# Configurações do Spanner lidas do ambiente do Container
INSTANCE_ID = os.environ.get("INSTANCE_ID") 
DATABASE_ID = os.environ.get("DATABASE_ID")

# Inicialização do Cliente Spanner
try:
    spanner_client = spanner.Client()
    instance = spanner_client.instance(INSTANCE_ID)
    database = instance.database(DATABASE_ID)
except Exception as e:
    print(f"Erro ao inicializar cliente Spanner: {e}")
    # A aplicação irá falhar ou lidar com a exceção dependendo do tratamento de erros.

@app.route('/')
def home():
    """Rota de teste simples."""
    return f"API de Consultas Harry Potter (Spanner: {DATABASE_ID}) está rodando!", 200

@app.route('/query/graph', methods=['GET'])
def graph_query():
    """Executa uma consulta GQL contra o grafo HPGRAH."""
    character_name = request.args.get('name', 'Harry Potter')

    # Query GQL para demonstrar as relações de 2º grau
    gql_query = f"""
    MATCH 
        (c:Characters {{Name: '{character_name}'}})
        -[:UsedSpell]-> (s:Spells)
        <-[:UsedSpell]- (ally:Characters)
    WHERE ally.House = c.House AND ally.Name <> c.Name
    RETURN 
        ally.Name AS Ally, 
        s.Name AS CommonSpell
    """
    
    # Template SQL que encapsula a GQL
    sql_template = f"SELECT * FROM GRAPH_QUERY(HPGRAH, \"\"\"{gql_query}\"\"\") AS results;"

    try:
        def execute_query(txn):
            # Usar execute_sql_json para obter resultados com nomes de colunas
            # Esta função retorna um cursor; é necessário ler os resultados.
            return list(txn.execute_sql(sql_template))

        results = database.run_in_transaction(execute_query)
        
        # NOTA: O formato da função GRAPH_QUERY retorna um JSON ou um conjunto de resultados difícil de mapear
        # diretamente. Simplificamos aqui o retorno da lista de linhas.
        return jsonify({
            'query_name': f'Allies of {character_name} via Common Spell',
            'results_count': len(results),
            'results': [list(row) for row in results]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'query': sql_template}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
