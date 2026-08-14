from pathlib import Path

from modules.transcript_archive import archive_transcription
from modules.transcript_parser import parse_transcript_file


SOURCE = Path('/home/ubuntu/upload/RENAN_SANTOS_FAZ_PRONUNCIAMENTO_OFICIAL_ANALISES_RENAIS_06_08_2026[T3ENScVymJQ].transcript.txt')
parsed = parse_transcript_file(str(SOURCE))
result = archive_transcription(
    parsed,
    source_video='RENAN_SANTOS_FAZ_PRONUNCIAMENTO_OFICIAL_ANALISES_RENAIS_06_08_2026[T3ENScVymJQ]',
    source='user_uploaded_transcript',
    source_artifact=str(SOURCE),
    archive_name=SOURCE.stem,
)
print(result)
