from pathlib import Path
import html
import json
import re

source = Path('/home/ubuntu/furia-clips-rebuild/docs/drive-folder.html').read_text(encoding='utf-8')
# Drive embeds a JSON-like file listing in the public folder HTML. Capture the
# visible names and nearby opaque IDs, then leave a reviewable JSON artifact.
entries = []
for match in re.finditer(r'(\d+\.\s[^"\\]{6,120}\.mp4)', source):
    name = html.unescape(match.group(1)).replace('\\u003d', '=').strip()
    window = source[max(0, match.start() - 1000):match.end() + 1000]
    ids = re.findall(r'[-_A-Za-z0-9]{20,}', window)
    candidates = [value for value in ids if len(value) <= 80 and value != name]
    file_id = candidates[-1] if candidates else ''
    if name not in [item['name'] for item in entries]:
        entries.append({'name': name, 'file_id_candidate': file_id})
Path('/home/ubuntu/furia-clips-rebuild/docs/drive-folder-files.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(entries, ensure_ascii=False, indent=2))
