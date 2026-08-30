import json
with open("C:/Users/70156213125/furia-clips/data/chub_transcripts_top_main.json") as f:
    data = json.load(f)
print("Type:", type(data))
if isinstance(data, list):
    print("Len:", len(data))
    for i, item in enumerate(data[:3]):
        print(f"Item {i} type:", type(item))
        if isinstance(item, dict):
            print(f"Item {i} keys:", list(item.keys()))
            if "error" in item:
                print(f"Item {i} HAS ERROR:", item["error"])
elif isinstance(data, dict):
    print("Keys:", list(data.keys()))
    if "error" in data:
        print("HAS ERROR:", data["error"])
