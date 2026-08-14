from pathlib import Path

from modules.transcript_parser import parse_transcript_file


SOURCE = Path('/home/ubuntu/upload/RENAN_SANTOS_FAZ_PRONUNCIAMENTO_OFICIAL_ANALISES_RENAIS_06_08_2026[T3ENScVymJQ].transcript.txt')
parsed = parse_transcript_file(str(SOURCE))
print({
    'segment_count': parsed['segment_count'],
    'first': parsed['segments'][:3],
    'last': parsed['segments'][-3:],
    'html_entities_left': sum('&gt;' in segment['text'] for segment in parsed['segments']),
    'arrow_tokens_left': sum('>>' in segment['text'] for segment in parsed['segments']),
})
