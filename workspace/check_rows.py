import json
with open("C:/Users/70156213125/furia-clips/data/chub_top50_renansantosreserva.json") as f:
    data = json.load(f)
rows = data.get("rows", [])
print("Rows:", len(rows))
for i, row in enumerate(rows[:3]):
    print(f"Row {i}:", {k: row[k] for k in list(row.keys())[:8]})
