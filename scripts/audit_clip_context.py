from pathlib import Path
import html
import json
import re

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
transcript_path = ROOT / 'docs' / 'audit-transcript-tactiq.txt'
log_path = ROOT / 'docs' / 'audit-run-log.txt'
report_path = ROOT / 'docs' / 'audit-clip-context.json'

stamp = re.compile(r'^(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+(.*)$')
def seconds(value):
    m = re.match(r'^(\d+):(\d+)(?::(\d+))?(?:\.(\d+))?$', value.strip())
    if not m:
        return None
    if m.group(3) is None:
        minutes, sec, millis = int(m.group(1)), int(m.group(2)), int((m.group(4) or '0').ljust(3, '0')[:3])
        return minutes * 60 + sec + millis / 1000
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int((m.group(4) or '0').ljust(3, '0')[:3]) / 1000

segments = []
for line in transcript_path.read_text(encoding='utf-8-sig').splitlines():
    m = stamp.match(line.strip())
    if m:
        start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000
        segments.append({'start': start, 'text': html.unescape(m.group(5)).strip()})
for idx, segment in enumerate(segments):
    segment['end'] = segments[idx + 1]['start'] if idx + 1 < len(segments) else segment['start'] + 8

lines = log_path.read_text(encoding='utf-8-sig').splitlines()
clips = []
current = None
for line in lines:
    m = re.search(r'Cortando clip (\d+)/(\d+):\s*(.*)$', line)
    if m:
        current = {'rank': int(m.group(1)), 'title': html.unescape(m.group(3)).strip()}
        clips.append(current)
        continue
    m = re.search(r'Cortando clip ([\d.]+)s - ([\d.]+)s', line)
    if m and current:
        current['start'] = float(m.group(1))
        current['end'] = float(m.group(2))

for clip in clips:
    covered = [s for s in segments if s['start'] < clip['end'] and s['end'] > clip['start']]
    text = ' '.join(s['text'] for s in covered)
    questions = [s for s in covered if '?' in s['text']]
    before = [s for s in segments if s['start'] < clip['start'] <= s['end']]
    after = [s for s in segments if s['start'] >= clip['end'] - 0.5 and s['start'] <= clip['end'] + 0.5]
    clip.update({
        'duration': round(clip['end'] - clip['start'], 3),
        'transcript_start': covered[0]['start'] if covered else None,
        'transcript_end': covered[-1]['end'] if covered else None,
        'segment_count': len(covered),
        'question_count': len(questions),
        'question_present': bool(questions),
        'starts_inside_segment': bool(before),
        'ends_near_segment_boundary': bool(after),
        'text_preview': text[:500],
    })

summary = {
    'clip_count': len(clips),
    'with_question_mark': sum(c['question_present'] for c in clips),
    'starting_inside_transcript_segment': sum(c['starts_inside_segment'] for c in clips),
    'average_duration': round(sum(c['duration'] for c in clips) / len(clips), 3) if clips else 0,
    'clips': clips,
}
report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
