from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.video_cutter import VideoCutter
from modules.media_validation import validate_media

source = Path('/home/ubuntu/upload/MELHORES_MOMENTOS_DA_ENTREVISTA_NA_CNN[k-LjFgh5o4Y].mp4')
out = Path('/home/ubuntu/furia-clips-rebuild/workspace/smoke_framing')
out.mkdir(parents=True, exist_ok=True)

cutter = VideoCutter(preset='shorts')
cut = {'start': 382.5, 'end': 387.5, 'duration': 5.0, 'title': 'smoke'}

vertical_results = cutter.batch_cut(
    str(source), [cut], 'smoke_vertical', use_face_tracking=True,
    face_positions_map={0: [
        {'time': 382.5, 'center_x': 0.70, 'confidence': 0.92},
        {'time': 384.5, 'center_x': 0.71, 'confidence': 0.91},
        {'time': 386.5, 'center_x': 0.69, 'confidence': 0.90},
    ]}
)
original_results = cutter.batch_cut(
    str(source), [cut], 'smoke_original', original_aspect_indices={0}
)
for label, results in [('vertical', vertical_results), ('original', original_results)]:
    if not results:
        raise SystemExit(f'{label}: no result')
    validation = results[0]['validation']
    print(label, results[0]['framing_mode'], results[0]['preset'], validation['width'], validation['height'], validation['valid'])
    if not validation['valid']:
        raise SystemExit(validation)
