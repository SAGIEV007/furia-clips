import json
data=json.load(open("C:/Users/70156213125/furia-clips/data/chub_top50_renansantosmbl.json")); print(type(data)); print(list(data.keys()) if isinstance(data, dict) else "list len="+str(len(data)))
