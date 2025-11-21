import json
from google.cloud import spanner

client = spanner.Client()
instance = client.instance("demo-hp")
db = instance.database("hp-database")

# Criando o snapshot para a consulta da tabela Spells
with db.snapshot() as snap:
    spells = snap.execute_sql("SELECT SpellID, Mention FROM Spells")

# Criando um novo snapshot para a consulta da tabela Characters
with db.snapshot() as snap:
    characters = {c[1]: c[0] for c in snap.execute_sql("SELECT CharacterID, Name FROM Characters")}

# Construindo os relacionamentos entre spells e characters
for spell_id, mention in spells:
    if not mention:
        continue
    for name, cid in characters.items():
        if name.lower() in mention.lower():
            with db.batch() as batch:
                batch.insert(
                    table="CharacterSpells",
                    columns=("CharacterID", "SpellID", "MentionContext"),
                    values=[(cid, spell_id, mention)]
                )

print("Relações criadas!")
