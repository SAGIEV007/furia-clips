from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np, subprocess
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.crop_dynamic import CropState, kalman_smooth_crop_path
from modules.face_tracker import FaceTracker

def detect(video, max_frames=150, sample_interval=2.0):
    t = FaceTracker()
    try:
        pos = t.detect_faces_in_video(video, sample_interval=sample_interval, emit_progress=None)
    finally:
        t.close()
    if not pos:
        return []
    return [CropState(x=float(p.get("center_x",0.5)), y=float(p.get("center_y",0.5))) for p in pos[:max_frames]]

def get_source_dims(video):
    pb = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","default=noprint_wrappers=1",video], capture_output=True, text=True)
    w=h=0
    for line in pb.stdout.splitlines():
        if line.startswith("width="): w=int(line.split("=",1)[1])
        if line.startswith("height="): h=int(line.split("=",1)[1])
    return w,h

def render(video, smoothed, out, preset_width=1080, preset_height=1920):
    src_w, src_h = get_source_dims(video)
    crop_w = max(2, int(src_h * 9 / 16))
    crop_h = src_h
    pts = smoothed
    if len(pts)>200:
        step=len(pts)/200
        idx=[int(i*step) for i in range(200)]
        pts=[smoothed[i] for i in idx]+[smoothed[-1]]
    segs=[]
    for i in range(len(pts)-1):
        x0=int(pts[i].x*src_w - crop_w/2)
        x1=int(pts[i+1].x*src_w - crop_w/2)
        x0=max(0,min(x0,src_w-crop_w))
        x1=max(0,min(x1,src_w-crop_w))
        segs.append(f"between(n,{i},{i+1})*({x0}+(n-{i})*({x1}-{x0}))")
    xe="+".join(segs) if segs else str(int(pts[0].x*src_w - crop_w/2))
    vf=f"crop={crop_w}:{crop_h}:({xe}):0,scale={preset_width}:{preset_height}"
    cmd=["ffmpeg","-y","-hwaccel","none","-ss","00:00:00","-i",video,"-t",str(len(pts)),"-vf",vf,"-c:v","libx264","-preset","medium","-crf","20","-c:a","aac","-b:a","128k","-movflags","+faststart",out]
    r=subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode==0, r.stderr[-500:], vf, crop_w, crop_h

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True)
    p.add_argument("--max-frames",type=int,default=120)
    p.add_argument("--sample-interval",type=float,default=2.0)
    p.add_argument("--output-dir",default="workspace/cache")
    a=p.parse_args()
    d=Path(a.output_dir)
    d.mkdir(parents=True, exist_ok=True)
    print(f"[validate] Video: {a.video}")
    raw=detect(a.video, a.max_frames, a.sample_interval)
    print(f"[validate] Raw: {len(raw)}")
    if len(raw)<3:
        print("[validate] Insufficient faces")
        (d/"crop_dynamic_validation_report.json").write_text(json.dumps({"video":a.video,"raw_count":len(raw),"status":"insufficient_faces"},indent=2))
        return
    sm=kalman_smooth_crop_path(raw)
    jr=np.mean(np.abs(np.diff([c.x for c in raw]))) if len(raw)>1 else 0.0
    js=np.mean(np.abs(np.diff([c.x for c in sm]))) if len(sm)>1 else 0.0
    cp=d/"crop_dynamic_test_clip.mp4"
    ok,err,vf,cw,ch=render(a.video,sm,str(cp))
    print(f"[validate] render_ok={ok}")
    if not ok:
        print(f"[validate] ffmpeg stderr: {err}")
    pb=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height,duration","-of","default=noprint_wrappers=1",str(cp)],capture_output=True,text=True)
    pok=pb.returncode==0 and f"width={1080}" in pb.stdout and f"height={1920}" in pb.stdout
    rep={"video":a.video,"raw_count":len(raw),"smoothed_count":len(sm),"jitter_raw_x":jr,"jitter_smooth_x":js,"jitter_reduction":(jr/js if js>0 else None),"mean_x_raw":float(np.mean([c.x for c in raw])),"mean_x_smooth":float(np.mean([c.x for c in sm])),"render_ok":ok,"crop_src_w":cw,"crop_src_h":ch,"probe_ok":pok,"status":"ok" if (ok and pok) else "render_failed"}
    (d/"crop_dynamic_validation_report.json").write_text(json.dumps(rep,indent=2))
    print(json.dumps(rep,indent=2))

if __name__=="__main__":
    main()
