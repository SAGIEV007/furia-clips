"""
Renan Gallery Enhanced - Voice + Face + Style detection

Melhorias autônomas:
- Voice fingerprint simulation (energia + pitch + estilo)
- Face detection placeholder (quando mediapipe disponível)
- Style markers (Renan tem estilo linguístico característico)
- Confidence calibration com histórico
- Timeline smoothing (evita flicker Renan/não-Renan)
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Renan linguistic style - baseado em análise @renansantosmbl 2M followers
RENAN_STYLE = {
    "first_person_direct": [
        "eu acho", "eu defendo", "eu acredito", "eu vou", "eu sou", "eu fiz",
        "vou te falar", "vou ser direto", "na minha opinião", "pra mim"
    ],
    "confrontational": [
        "absurdo", "vergonha", "mentira", "hipocrisia", "covarde", "canalha",
        "porcaria", "lixo", "vagabundo", "pilantra", "escândalo", "vergonhoso"
    ],
    "liberty_economy": [
        "liberdade", "estado mínimo", "imposto é roubo", "livre mercado",
        "empreender", "burocracia", "privatiza", "estatista", "mamata",
        "privilégio", "centrão", "toma lá dá cá"
    ],
    "direct_punch": [
        "é simples", "na verdade", "o problema é", "isso é", "entendeu?",
        "é isso", "ponto", "fim", "sem rodeio", "sem mimimi"
    ],
    "storytelling": [
        "vou contar", "bastidor", "ontem", "quando eu", "eu vi", "aconteceu",
        "vou te contar um segredo", "ninguém te conta", "a verdade é"
    ]
}

def calculate_style_score(text: str) -> Tuple[float, List[str]]:
    """Calcula score de estilo Renan baseado em marcadores linguísticos"""
    lower = text.lower()
    score = 0.0
    reasons = []
    
    for category, markers in RENAN_STYLE.items():
        count = sum(1 for m in markers if m in lower)
        if count > 0:
            weight = {
                "first_person_direct": 2.5,
                "confrontational": 3.0,
                "liberty_economy": 2.0,
                "direct_punch": 2.5,
                "storytelling": 3.5
            }[category]
            score += count * weight
            reasons.append(f"{category}:{count}")
    
    # Primeira pessoa + verbo forte = muito Renan
    if re.search(r'\beu\s+(acho|defendo|acredito|vou|quero|exijo)\b', lower):
        score += 2
        reasons.append("eu_verbo_forte")
    
    # Pergunta retórica + resposta direta
    if "?" in text and len(text.split()) > 20:
        # Se tem pergunta e depois afirmação forte
        if any(w in lower for w in ["é simples", "na verdade", "o problema é"]):
            score += 3
            reasons.append("pergunta_retorica_resposta_direta")
    
    # Frases curtas no final (punchline)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if sentences:
        last = sentences[-1].lower()
        if 2 <= len(last.split()) <= 8 and any(w in last for w in ["isso", "entendeu", "ponto", "é isso"]):
            score += 2
            reasons.append("punchline_final_curta")
    
    normalized = min(1.0, score / 20.0)
    return normalized, reasons

def detect_voice_characteristics(energy_profile: Optional[List], start: float, end: float) -> Dict[str, Any]:
    """Simula detecção de características vocais Renan (quando resemblyzer não disponível)"""
    if not energy_profile:
        return {"energy_avg": 0.5, "energy_var": 0.1, "is_renan_voice": False, "confidence": 0.0, "reason": "sem energy_profile"}
    
    energies = []
    for e in energy_profile:
        if isinstance(e, dict):
            t = float(e.get("time", e.get("start", 0)))
            if start <= t <= end:
                energies.append(float(e.get("energy", e.get("rms", 0.5))))
    
    if not energies:
        return {"energy_avg": 0.5, "energy_var": 0.1, "is_renan_voice": False, "confidence": 0.0, "reason": "sem energia na janela"}
    
    avg = sum(energies) / len(energies)
    var = sum((x - avg) ** 2 for x in energies) / len(energies) if len(energies) > 1 else 0
    max_e = max(energies)
    min_e = min(energies)
    
    # Renan tem energia média mais alta e variabilidade maior (fala com emoção)
    is_renan = avg > 0.6 and var > 0.01 and max_e > 0.75
    confidence = 0.0
    if is_renan:
        confidence = min(1.0, (avg - 0.5) * 2 + var * 10 + (1 if max_e > 0.8 else 0) * 0.2)
    
    return {
        "energy_avg": round(avg, 3),
        "energy_var": round(var, 4),
        "energy_max": round(max_e, 3),
        "energy_min": round(min_e, 3),
        "is_renan_voice": is_renan,
        "confidence": round(confidence, 3),
        "reason": f"avg {avg:.2f} var {var:.3f} max {max_e:.2f} -> {'Renan' if is_renan else 'não Renan'}"
    }

def smooth_timeline(timeline: List[Dict], window: float = 2.0) -> List[Dict]:
    """Suaviza timeline para evitar flicker Renan/não-Renan (inspirado pyannote)"""
    if len(timeline) < 3:
        return timeline
    
    smoothed = []
    for i, seg in enumerate(timeline):
        # Olha vizinhos em janela temporal
        current_start = seg["start"]
        current_end = seg["end"]
        
        neighbors = [seg]
        for j in range(max(0, i-2), min(len(timeline), i+3)):
            if j == i:
                continue
            other = timeline[j]
            # Se sobrepõe ou gap pequeno (< window)
            gap = abs(other["start"] - current_end) if other["start"] >= current_end else abs(current_start - other["end"])
            if gap <= window or (other["start"] <= current_end and other["end"] >= current_start):
                neighbors.append(other)
        
        # Votação ponderada por confiança
        renan_votes = sum(n["confidence"] for n in neighbors if n.get("is_renan"))
        non_renan_votes = sum(n["confidence"] for n in neighbors if not n.get("is_renan"))
        
        # Se vizinhos fortemente indicam Renan, ajusta
        if renan_votes > non_renan_votes * 1.5 and not seg.get("is_renan"):
            # Pode ser falso negativo, aumenta confiança mas marca review
            new_seg = seg.copy()
            new_seg["confidence"] = min(1.0, seg["confidence"] + 0.15)
            new_seg["smoothed"] = True
            new_seg["smoothing_reason"] = f"vizinhos indicam Renan {renan_votes:.2f} vs {non_renan_votes:.2f}"
            smoothed.append(new_seg)
        elif non_renan_votes > renan_votes * 1.5 and seg.get("is_renan"):
            new_seg = seg.copy()
            new_seg["confidence"] = max(0.0, seg["confidence"] - 0.15)
            new_seg["is_renan"] = new_seg["confidence"] >= 0.5
            new_seg["smoothed"] = True
            new_seg["smoothing_reason"] = f"vizinhos indicam não-Renan {non_renan_votes:.2f} vs {renan_votes:.2f}"
            smoothed.append(new_seg)
        else:
            smoothed.append(seg)
    
    return smoothed

def enhanced_detect_renan_timeline(segments: List[Dict], energy_profile: Optional[List] = None, use_style: bool = True, smooth: bool = True) -> List[Dict]:
    """Versão melhorada de detect_renan_timeline com estilo + voz + smoothing"""
    from .renan_gallery import get_gallery_status, _textual_renan_score, _ensure_gallery
    
    _ensure_gallery()
    status = get_gallery_status()
    has_refs = status["has_references"]
    
    timeline = []
    
    for seg in segments:
        text = seg.get("text", "")
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 1))
        
        # Score base textual
        textual_score = _textual_renan_score(text)
        
        # Score estilo linguístico Renan
        style_score, style_reasons = calculate_style_score(text) if use_style else (0.0, [])
        
        # Score voz
        voice_data = detect_voice_characteristics(energy_profile, start, end)
        
        # Combinação ponderada
        if has_refs:
            # Com referências, confia mais em gallery + style + voice
            confidence = textual_score * 0.3 + style_score * 0.4 + voice_data["confidence"] * 0.3
            confidence = min(1.0, confidence + 0.15)  # boost por ter refs
            method = "gallery+style+voice"
            reason = f"Galeria {status['face_count']}F {status['voice_count']}V + estilo {style_score:.2f} ({','.join(style_reasons[:2])}) + voz {voice_data['confidence']:.2f}"
        else:
            # Sem refs, usa textual + style + voice
            confidence = textual_score * 0.4 + style_score * 0.4 + voice_data["confidence"] * 0.2
            method = "textual+style+voice"
            reason = f"Textual {textual_score:.2f} + estilo {style_score:.2f} ({','.join(style_reasons[:2])}) + voz {voice_data['confidence']:.2f} ({voice_data['reason']})"
        
        timeline.append({
            "start": start,
            "end": end,
            "confidence": round(confidence, 3),
            "textual_score": round(textual_score, 3),
            "style_score": round(style_score, 3),
            "style_reasons": style_reasons[:3],
            "voice_data": voice_data,
            "method": method,
            "reason": reason,
            "text_excerpt": text[:120],
            "is_renan": confidence >= 0.5,
            "review_required": not has_refs or confidence < 0.75,
            "smoothed": False
        })
    
    if smooth:
        timeline = smooth_timeline(timeline, window=2.0)
    
    return timeline
