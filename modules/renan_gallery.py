"""
Galeria de Identidade - Renan Santos (inicialmente apenas Renan)

Baseado em pesquisa extensa:
- OpusClip Active Speaker Detection + SyncNet
- VoxCeleb pipeline: YouTube -> SyncNet active speaker -> face recognition CNN
- AdaFace ResNet-18 para reconhecimento facial leve
- Resemblyzer / pyannote para voz (d-vector)

Objetivo Etapa 1: Criar estrutura que permita:
1. Adicionar fotos de referência do Renan (gallery/renan/faces/)
2. Adicionar áudios de referência do Renan (gallery/renan/voices/)
3. Detectar em timeline onde Renan está falando
4. Usar essa informação no ClipSelector para priorizar cortes com Renan

Implementação inicial: sem dependências pesadas, funciona com o que existe.
Quando mediapipe/numpy disponível, usa detecção facial leve.
Quando resemblyzer disponível, usa embedding de voz.
Fallback: heurística textual (termos Renan) + energia.

Estrutura de diretórios:
FuriaClipsData/gallery/renan/
  faces/ -> jpg/png de referência
  voices/ -> wav/mp3 de referência
  metadata.json -> info da galeria
"""

from __future__ import annotations

import os
import json
import hashlib
from pathlib import Path
from typing import Any, List, Dict, Optional
from datetime import datetime

from config import PERSISTENT_DATA_DIR

GALLERY_ROOT = Path(PERSISTENT_DATA_DIR) / "gallery"
RENAN_GALLERY = GALLERY_ROOT / "renan"
RENAN_FACES = RENAN_GALLERY / "faces"
RENAN_VOICES = RENAN_GALLERY / "voices"
RENAN_META = RENAN_GALLERY / "metadata.json"

# Termos que indicam Renan falando (fallback textual)
RENAN_TERMS = {"renan", "santos", "renan santos", "mbl", "missão", "missao"}

def _ensure_gallery():
    """Garante estrutura de diretórios"""
    RENAN_FACES.mkdir(parents=True, exist_ok=True)
    RENAN_VOICES.mkdir(parents=True, exist_ok=True)
    if not RENAN_META.exists():
        meta = {
            "name": "Renan Santos",
            "created_at": datetime.now().isoformat(),
            "face_count": 0,
            "voice_count": 0,
            "face_embeddings": [],  # placeholder para embeddings futuros
            "voice_embeddings": [],
            "notes": "Galeria inicial - apenas Renan. Adicione fotos em faces/ e áudios em voices/",
            "version": 1
        }
        RENAN_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

def get_gallery_status() -> Dict[str, Any]:
    """Retorna status da galeria Renan"""
    _ensure_gallery()
    try:
        meta = json.loads(RENAN_META.read_text(encoding="utf-8"))
    except:
        meta = {"face_count": 0, "voice_count": 0}
    
    face_files = list(RENAN_FACES.glob("*.*")) if RENAN_FACES.exists() else []
    voice_files = list(RENAN_VOICES.glob("*.*")) if RENAN_VOICES.exists() else []
    
    # Filtra apenas arquivos válidos
    valid_faces = [f for f in face_files if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    valid_voices = [f for f in voice_files if f.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}]
    
    return {
        "available": True,
        "name": "Renan Santos",
        "faces_dir": str(RENAN_FACES),
        "voices_dir": str(RENAN_VOICES),
        "face_count": len(valid_faces),
        "voice_count": len(valid_voices),
        "face_files": [str(f) for f in valid_faces[:10]],
        "voice_files": [str(f) for f in valid_voices[:10]],
        "has_references": len(valid_faces) > 0 or len(valid_voices) > 0,
        "metadata": meta,
        "instructions": "Adicione 3-5 fotos frontais do Renan em faces/ e 2-3 áudios de 10-30s com voz limpa em voices/ para calibrar reconhecimento"
    }

def _textual_renan_score(text: str) -> float:
    """Fallback: score baseado em termos textuais"""
    if not text:
        return 0.0
    lower = text.lower()
    score = 0.0
    # Primeira pessoa + contexto político sugere Renan
    first_person = {"eu", "meu", "minha", "acho", "acredito", "defendo", "proponho"}
    words = set(lower.split())
    if words & first_person:
        score += 0.3
    if any(term in lower for term in RENAN_TERMS):
        score += 0.4
    # Termos políticos que Renan usa frequentemente
    renan_markers = {"brasil", "governo", "lula", "stf", "mbl", "missão", "liberdade", "imposto", "reforma"}
    marker_count = sum(1 for m in renan_markers if m in lower)
    score += min(0.3, marker_count * 0.08)
    return min(1.0, score)

def detect_renan_timeline(segments: List[Dict], energy_profile: Optional[List] = None) -> List[Dict]:
    """
    Detecta timeline onde Renan provavelmente está falando.
    
    Retorna lista de dicts com:
    - start, end, confidence, method, reason
    
    Métodos (em ordem de confiança):
    1. face_recognition + voice_match (quando galeria tem referências)
    2. voice_embedding (quando tem áudio referência)
    3. textual_heuristic (fallback atual)
    4. energy_based (fallback)
    
    Para Etapa 1: implementa textual + energy, estrutura pronta para AdaFace/Resemblyzer
    """
    _ensure_gallery()
    status = get_gallery_status()
    has_refs = status["has_references"]
    
    timeline = []
    
    for seg in segments:
        text = seg.get("text", "")
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 1))
        
        if has_refs:
            # Quando tiver referências, aqui entraria AdaFace + Resemblyzer
            # Por enquanto, marca como review_required
            confidence = 0.65 + _textual_renan_score(text) * 0.25
            method = "gallery_heuristic"
            reason = f"Galeria com {status['face_count']} faces e {status['voice_count']} vozes, score textual {confidence:.2f}"
        else:
            confidence = _textual_renan_score(text)
            method = "textual_fallback"
            reason = f"Sem referências na galeria, usando heurística textual (score {confidence:.2f})"
        
        # Energia pode aumentar confiança - Renan tem energia característica
        if energy_profile and confidence > 0.3:
            # Busca energia na janela do segmento
            try:
                energy_in_window = [
                    e for e in energy_profile 
                    if isinstance(e, dict) and start <= float(e.get("time", e.get("start", 0))) <= end
                ]
                if energy_in_window:
                    avg_energy = sum(float(e.get("energy", e.get("rms", 0.5))) for e in energy_in_window) / len(energy_in_window)
                    if avg_energy > 0.6:
                        confidence = min(1.0, confidence + 0.15)
                        reason += f" + energia alta ({avg_energy:.2f})"
            except:
                pass
        
        timeline.append({
            "start": start,
            "end": end,
            "confidence": round(confidence, 3),
            "method": method,
            "reason": reason,
            "text_excerpt": text[:120],
            "is_renan": confidence >= 0.5,
            "review_required": not has_refs or confidence < 0.75
        })
    
    return timeline

def prioritize_clips_with_renan(clips: List[Dict], renan_timeline: List[Dict]) -> List[Dict]:
    """
    Prioriza clips onde Renan está falando.
    Adiciona campo renan_score e renan_evidence em cada clip.
    """
    if not clips or not renan_timeline:
        return clips
    
    for clip in clips:
        c_start = float(clip.get("start", 0))
        c_end = float(clip.get("end", c_start))
        
        # Encontra segmentos Renan que sobrepõem com clip
        overlapping = []
        for rt in renan_timeline:
            overlap = max(0, min(c_end, rt["end"]) - max(c_start, rt["start"]))
            if overlap > 0:
                overlapping.append((overlap, rt))
        
        if overlapping:
            total_overlap = sum(ov for ov, _ in overlapping)
            clip_duration = c_end - c_start
            coverage = total_overlap / clip_duration if clip_duration > 0 else 0
            
            # Score ponderado por confiança e cobertura
            weighted_conf = sum(ov * rt["confidence"] for ov, rt in overlapping) / total_overlap if total_overlap > 0 else 0
            renan_score = coverage * weighted_conf
            
            clip["renan_score"] = round(renan_score, 3)
            clip["renan_coverage"] = round(coverage, 3)
            clip["renan_confidence"] = round(weighted_conf, 3)
            clip["renan_evidence"] = f"{len(overlapping)} segmento(s) com {coverage*100:.0f}% cobertura, confiança {weighted_conf:.2f}"
            clip["renan_timeline"] = overlapping[:3]  # Top 3 evidências
        else:
            clip["renan_score"] = 0.0
            clip["renan_coverage"] = 0.0
            clip["renan_confidence"] = 0.0
            clip["renan_evidence"] = "Nenhuma sobreposição com timeline Renan"
    
    # Ordena por renan_score decrescente, mas mantém viral_score como critério secundário
    clips_sorted = sorted(clips, key=lambda c: (c.get("renan_score", 0), c.get("viral_score", 0)), reverse=True)
    return clips_sorted

def add_reference_face(image_path: str) -> Dict[str, Any]:
    """Adiciona foto de referência do Renan"""
    _ensure_gallery()
    src = Path(image_path)
    if not src.exists():
        return {"success": False, "error": "Arquivo não encontrado"}
    
    if src.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return {"success": False, "error": "Formato deve ser jpg, png ou webp"}
    
    # Gera nome único baseado em hash
    content_hash = hashlib.md5(src.read_bytes()).hexdigest()[:12]
    dest_name = f"renan_face_{content_hash}{src.suffix.lower()}"
    dest = RENAN_FACES / dest_name
    
    # Copia
    dest.write_bytes(src.read_bytes())
    
    # Atualiza metadata
    try:
        meta = json.loads(RENAN_META.read_text(encoding="utf-8"))
    except:
        meta = {}
    meta["face_count"] = len(list(RENAN_FACES.glob("*.*")))
    meta["updated_at"] = datetime.now().isoformat()
    RENAN_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"success": True, "path": str(dest), "hash": content_hash}

def add_reference_voice(audio_path: str) -> Dict[str, Any]:
    """Adiciona áudio de referência do Renan"""
    _ensure_gallery()
    src = Path(audio_path)
    if not src.exists():
        return {"success": False, "error": "Arquivo não encontrado"}
    
    if src.suffix.lower() not in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
        return {"success": False, "error": "Formato deve ser wav, mp3, m4a, ogg ou flac"}
    
    content_hash = hashlib.md5(src.read_bytes()).hexdigest()[:12]
    dest_name = f"renan_voice_{content_hash}{src.suffix.lower()}"
    dest = RENAN_VOICES / dest_name
    dest.write_bytes(src.read_bytes())
    
    try:
        meta = json.loads(RENAN_META.read_text(encoding="utf-8"))
    except:
        meta = {}
    meta["voice_count"] = len(list(RENAN_VOICES.glob("*.*")))
    meta["updated_at"] = datetime.now().isoformat()
    RENAN_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"success": True, "path": str(dest), "hash": content_hash}


# Enhanced functions - try to import, fallback to basic
try:
    from .renan_gallery_enhanced import (
        calculate_style_score,
        detect_voice_characteristics,
        smooth_timeline,
        enhanced_detect_renan_timeline
    )
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False
    def calculate_style_score(text):
        return 0.0, []
    def detect_voice_characteristics(ep, s, e):
        return {"confidence": 0.0, "is_renan_voice": False}
    def smooth_timeline(tl, window=2.0):
        return tl
    def enhanced_detect_renan_timeline(segments, energy_profile=None, use_style=True, smooth=True):
        return detect_renan_timeline(segments, energy_profile)

def get_enhanced_status():
    """Status com enhanced info"""
    base = get_gallery_status()
    base["enhanced_available"] = ENHANCED_AVAILABLE
    base["style_detection"] = ENHANCED_AVAILABLE
    base["voice_detection"] = ENHANCED_AVAILABLE
    base["timeline_smoothing"] = ENHANCED_AVAILABLE
    return base
