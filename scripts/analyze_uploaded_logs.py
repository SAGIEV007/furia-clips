from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

LAUNCHER = Path('/home/ubuntu/upload/pasted_content_12.txt')
PROGRAM = Path('/home/ubuntu/upload/pasted_content_13.txt')

STAMP = re.compile(r'\[(\d{2}:\d{2}:\d{2})\]')
TRANSCRIBE = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] Transcrevendo\.\.\. (\d+) segmentos')
DOWNLOAD = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] \[Download\] (.+)')

def seconds(value: str) -> int:
    h, m, s = map(int, value.split(':'))
    return h * 3600 + m * 60 + s

launcher = LAUNCHER.read_text(encoding='utf-8', errors='replace')
program = PROGRAM.read_text(encoding='utf-8', errors='replace')

print('ERROS DO LAUNCHER')
for needle in ('UnicodeDecodeError', 'AttributeError', 'HTTP Error 403', 'POST /api/source/import', 'POST /api/dialog/choose'):
    print(f'{needle}: {launcher.count(needle)}')

rows = [(seconds(t), int(n)) for t, n in TRANSCRIBE.findall(program)]
print('\nTRANSCRICAO')
print(f'blocos registrados: {len(rows)}')
if rows:
    first_t, first_n = rows[0]
    last_t, last_n = rows[-1]
    print(f'primeiro bloco: {first_n} segmentos em {first_t}s')
    print(f'ultimo bloco: {last_n} segmentos em {last_t}s')
    print(f'tempo observado: {last_t-first_t}s ({(last_t-first_t)/60:.2f} min)')
    intervals = []
    for (prev_t, prev_n), (cur_t, cur_n) in zip(rows, rows[1:]):
        if cur_n > prev_n:
            intervals.append((cur_n - prev_n, cur_t - prev_t))
    if intervals:
        per_segment = sum(dt / dn for dn, dt in intervals) / len(intervals)
        print(f'media observada: {per_segment:.2f}s de processamento por segmento')
        print('intervalos por 50 segmentos:')
        for dn, dt in intervals:
            print(f'  +{dn} segmentos em {dt}s ({dt/60:.2f} min)')

print('\nDOWNLOAD')
downloads = DOWNLOAD.findall(program)
print(f'eventos de progresso: {len(downloads)}')
if downloads:
    print(f'primeiro: {downloads[0]}')
    print(f'ultimo: {downloads[-1]}')
