from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gemini-3-flash-preview",
    messages=[
        {"role": "system", "content": "Responda somente JSON válido."},
        {"role": "user", "content": "Retorne {\"ok\":true}."},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "probe",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            },
        },
    },
    max_tokens=256,
)
print(response.model_dump_json(indent=2))
