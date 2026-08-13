from __future__ import annotations

import argparse
import base64
import json
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
CATALOG = ROOT / 'docs' / 'instagram-feed-catalog-full.json'

SCHEMA = {
    'type': 'object',
    'properties': {
        'hook': {'type': 'string'},
        'editorial_family': {'type': 'string'},
        'visual_structure': {'type': 'string'},
        'cut_rhythm': {'type': 'string'},
        'caption_style': {'type': 'string'},
        'framing': {'type': 'string'},
        'audio': {'type': 'string'},
        'political_context': {'type': 'string'},
        'viral_potential': {'type': 'string'},
        'recommended_furia_rule': {'type': 'string'},
        'confidence': {'type': 'number'},
        'evidence_limitations': {'type': 'string'},
    },
    'required': [
        'hook', 'editorial_family', 'visual_structure', 'cut_rhythm',
        'caption_style', 'framing', 'audio', 'political_context',
        'viral_potential', 'recommended_furia_rule', 'confidence',
        'evidence_limitations',
    ],
    'additionalProperties': False,
}


def duration(path: Path) -> float:
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(path)],
        capture_output=True, text=True, encoding='utf-8', errors='replace', check=False,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def frames(path: Path, output_dir: Path, count: int = 6) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    seconds = duration(path)
    if seconds <= 0:
        return []
    paths = []
    for index in range(count):
        timestamp = min(max(0.2, seconds * (index + 0.5) / count), max(0.2, seconds - 0.2))
        target = output_dir / f'frame_{index:02d}.jpg'
        result = subprocess.run(
            ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', f'{timestamp:.3f}', '-i', str(path), '-frames:v', '1', '-vf', 'scale=640:-2', '-q:v', '5', '-y', str(target)],
            capture_output=True, text=True, encoding='utf-8', errors='replace', check=False,
        )
        if result.returncode == 0 and target.exists():
            paths.append(target)
    return paths


def image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode('ascii')
    return f'data:image/jpeg;base64,{encoded}'


def analyze(client: OpenAI, entry: dict, video_path: Path, frame_paths: list[Path]) -> dict:
    content = [{
        'type': 'text',
        'text': (
            'Você é um pesquisador audiovisual e editor de clips políticos. Analise apenas as evidências visuais nos quadros, '
            'o caption público e os metadados abaixo. Não invente falas, cortes ou áudio que não possam ser comprovados. '
            'Descreva a estrutura editada e converta o padrão em uma regra implementável no Furia Clips. '
            'O objetivo é aprender o estilo de Reels do Renan Santos/MBL e diferenciar hook, ritmo, texto, enquadramento, áudio e potencial de compartilhamento.\n\n'
            f'Perfil: {entry.get("profile")}\nURL: {entry.get("url")}\nCódigo: {entry.get("code")}\n'
            f'Duração local: {duration(video_path):.1f}s\nCaption público: {entry.get("caption", "")}\n'
            'Os quadros estão em ordem temporal aproximada. Responda em JSON conforme o schema.'
        ),
    }]
    for frame in frame_paths:
        content.append({'type': 'image_url', 'image_url': {'url': image_data_url(frame), 'detail': 'auto'}})
    response = client.chat.completions.create(
        model='gemini-3-flash-preview',
        messages=[{'role': 'user', 'content': content}],
        max_tokens=2400,
        response_format={
            'type': 'json_schema',
            'json_schema': {'name': 'reel_editorial_analysis', 'strict': True, 'schema': SCHEMA},
        },
    )
    if not getattr(response, 'choices', None):
        try:
            raw_response = response.model_dump_json()[:2000]
        except Exception:
            raw_response = repr(response)[:2000]
        raise RuntimeError(f'proxy sem choices: {raw_response}')
    message = response.choices[0].message
    text = getattr(message, 'content', None) or '{}'
    return json.loads(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', default='renansantosmbl')
    parser.add_argument('--input', default='workspace/instagram_mbl_sample')
    parser.add_argument('--output', default='docs/instagram_mbl_sample_analysis.json')
    parser.add_argument('--limit', type=int, default=12)
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    entries = [entry for entry in catalog['profiles'][args.profile]['entries'] if entry.get('is_video')][:args.limit]
    input_dir = ROOT / args.input
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding='utf-8'))
        except Exception:
            existing = {}
    client = OpenAI()
    results = existing.copy()
    with tempfile.TemporaryDirectory(prefix='furia-reel-frames-') as temp:
        frame_root = Path(temp)
        for index, entry in enumerate(entries, 1):
            code = entry['code']
            video_path = input_dir / f'{code}.mp4'
            if not video_path.exists():
                print(index, code, 'missing-video', flush=True)
                continue
            if code in results and results[code].get('analysis'):
                print(index, code, 'exists', flush=True)
                continue
            try:
                frame_paths = frames(video_path, frame_root / code)
                if not frame_paths:
                    raise RuntimeError('nenhum quadro extraído')
                results[code] = {
                    'profile': args.profile,
                    'code': code,
                    'url': entry.get('url'),
                    'published_at': entry.get('taken_at'),
                    'duration': duration(video_path),
                    'caption': entry.get('caption', ''),
                    'analysis': analyze(client, entry, video_path, frame_paths),
                    'evidence': {'frame_count': len(frame_paths), 'method': 'local_ffmpeg_frames_plus_gemini3flash'},
                }
                output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
                print(index, code, 'ok', flush=True)
            except Exception as exc:
                results[code] = {'profile': args.profile, 'code': code, 'url': entry.get('url'), 'error': str(exc)}
                output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
                print(index, code, 'error', str(exc)[:200], flush=True)


if __name__ == '__main__':
    main()
