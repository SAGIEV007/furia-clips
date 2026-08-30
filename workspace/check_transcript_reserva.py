import json
with open("C:/Users/70156213125/furia-clips/data/chub_transcripts_top_reserva.json") as f:
    data = json.load(f)
print("Type:", type(data))
if isinstance(data, list):
    print("Len:", len(data))
    for i, item in enumerate(data[:2]):
        print(f"Item {i} keys:", list(item.keys()))
elif isinstance(data, dict):
    print("Keys:", list(data.keys()))
