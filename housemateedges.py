from google.cloud import spanner

# Configuração do cliente do Spanner
client = spanner.Client()
instance = client.instance("demo-hp")
db = instance.database("hp-database")

# Criando o relacionamento entre personagens que compartilham a mesma casa
with db.snapshot() as snap:
    # Consulta para pegar os personagens e suas casas
    characters = {c[0]: c[1] for c in snap.execute_sql("SELECT CharacterID, House FROM Characters WHERE House IS NOT NULL")}

# Para cada par de personagens na mesma casa, criamos um relacionamento
for character_id, house_name in characters.items():
    for target_id, target_house in characters.items():
        # Garantir que não se relacionem com eles mesmos
        if character_id != target_id and house_name == target_house:
            with db.batch() as batch:
                # Inserindo o relacionamento na tabela HouseMateEdges
                batch.insert(
                    table="HouseMateEdges",
                    columns=("SourceCharacterID", "TargetCharacterID", "HouseName"),
                    values=[(character_id, target_id, house_name)]
                )

print("Relacionamentos de casas entre personagens criados!")
