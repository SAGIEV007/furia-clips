"""
Aprendizado com Engajamento + Likes/Dislikes

Objetivo: aprender padrões dos vídeos com maior engajamento do Instagram do Renan
e também com likes/dislikes dentro da ferramenta.

Baseado em:
- modules/editorial_learning_store.py (Claude) - existe?
- modules/performance_metrics.py - snapshots de performance
- Instagram: Reels com mais views, likes, comentários, shares indicam o que viraliza

Implementação:
1. engagement_prior: analisa Reels do @renansantosmbl com alto engajamento
2. editor_feedback: likes/dislikes dentro da Furia Clips
3. combined_learning: mescla os dois para priorizar formatos, tópicos, duração

Para Etapa 1: estrutura + heurística baseada em performance_metrics
Para Etapa 2: integração com headline studio
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import PERSISTENT_DATA_DIR
from database import get_feedback_calibration, get_approved_clip_feature_prior, get_performance_summary, get_performance_snapshots

LEARNING_DIR = Path(PERSISTENT_DATA_DIR) / "learning"
ENGAGEMENT_PRIOR = LEARNING_DIR / "engagement_prior.json"
EDITOR_FEEDBACK_PRIOR = LEARNING_DIR / "editor_feedback_prior.json"

def _ensure_learning_dir():
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)

def get_engagement_learning_status() -> Dict[str, Any]:
    """Status do aprendizado por engajamento"""
    _ensure_learning_dir()
    
    # Performance snapshots (se existirem)
    try:
        perf_summary = get_performance_summary()
        perf_snapshots = get_performance_snapshots(limit=50)
    except:
        perf_summary = {}
        perf_snapshots = []
    
    # Feedback calibration (likes/dislikes dentro da ferramenta)
    try:
        feedback_cal = get_feedback_calibration()
    except:
        feedback_cal = {"sample_size": 0}
    
    # Approved clip prior (cortes aprovados)
    try:
        approved_prior = get_approved_clip_feature_prior()
    except:
        approved_prior = {"available": False}
    
    # Engagement prior (arquivo local)
    engagement_prior = {}
    if ENGAGEMENT_PRIOR.exists():
        try:
            engagement_prior = json.loads(ENGAGEMENT_PRIOR.read_text(encoding="utf-8"))
        except:
            engagement_prior = {}
    
    return {
        "performance_snapshots": {
            "available": len(perf_snapshots) > 0,
            "count": len(perf_snapshots),
            "summary": perf_summary
        },
        "editor_feedback": {
            "available": feedback_cal.get("sample_size", 0) > 0,
            "sample_size": feedback_cal.get("sample_size", 0),
            "eligible": feedback_cal.get("eligible", False),
            "calibration": feedback_cal
        },
        "approved_clips": {
            "available": approved_prior.get("available", False),
            "eligible": approved_prior.get("eligible", False),
            "approved_count": approved_prior.get("approved_count", 0)
        },
        "engagement_prior_file": {
            "exists": ENGAGEMENT_PRIOR.exists(),
            "path": str(ENGAGEMENT_PRIOR),
            "data": engagement_prior
        },
        "learning_dir": str(LEARNING_DIR),
        "combined_eligible": (
            len(perf_snapshots) >= 5 or 
            feedback_cal.get("sample_size", 0) >= 10 or 
            approved_prior.get("approved_count", 0) >= 5
        )
    }

def analyze_performance_patterns() -> Dict[str, Any]:
    """
    Analisa padrões de performance para aprender o que viraliza.
    
    Baseado em performance_metrics.py:
    - format_id: vertical_916, square_alfinetei, fake_tweet
    - platform: instagram, tiktok, youtube
    - metrics: views, likes, comments, shares, retention
    
    Retorna padrões como:
    - melhor duração
    - melhor formato por tópico
    - melhores horários
    - tópicos com maior engajamento
    """
    _ensure_learning_dir()
    
    try:
        snapshots = get_performance_snapshots(limit=100)
        summary = get_performance_summary()
    except:
        snapshots = []
        summary = {}
    
    if not snapshots:
        return {
            "available": False,
            "reason": "Nenhum snapshot de performance ainda. Adicione via /api/performance/snapshots",
            "patterns": {},
            "recommendations": [
                "Importe métricas de Reels do @renansantosmbl com alto engajamento",
                "Use formato: {format_id, platform, views, likes, comments, topic, duration}",
                "Quanto mais snapshots, melhor a calibração"
            ]
        }
    
    # Análise de padrões
    patterns = {
        "by_format": {},
        "by_topic": {},
        "by_duration": {"short": 0, "medium": 0, "long": 0},
        "top_performers": []
    }
    
    for snap in snapshots:
        fmt = snap.get("format_id", "unknown")
        topic = snap.get("topic", "geral")
        duration = snap.get("duration", 45)
        views = snap.get("views", 0)
        
        # Por formato
        if fmt not in patterns["by_format"]:
            patterns["by_format"][fmt] = {"count": 0, "total_views": 0, "avg_views": 0}
        patterns["by_format"][fmt]["count"] += 1
        patterns["by_format"][fmt]["total_views"] += views
        
        # Por tópico
        if topic not in patterns["by_topic"]:
            patterns["by_topic"][topic] = {"count": 0, "total_views": 0, "avg_views": 0}
        patterns["by_topic"][topic]["count"] += 1
        patterns["by_topic"][topic]["total_views"] += views
        
        # Por duração
        if duration < 30:
            patterns["by_duration"]["short"] += 1
        elif duration < 60:
            patterns["by_duration"]["medium"] += 1
        else:
            patterns["by_duration"]["long"] += 1
    
    # Calcula médias
    for fmt in patterns["by_format"]:
        c = patterns["by_format"][fmt]["count"]
        patterns["by_format"][fmt]["avg_views"] = patterns["by_format"][fmt]["total_views"] / c if c else 0
    
    for topic in patterns["by_topic"]:
        c = patterns["by_topic"][topic]["count"]
        patterns["by_topic"][topic]["avg_views"] = patterns["by_topic"][topic]["total_views"] / c if c else 0
    
    # Top performers
    top = sorted(snapshots, key=lambda s: s.get("views", 0), reverse=True)[:5]
    patterns["top_performers"] = [
        {"format": s.get("format_id"), "topic": s.get("topic"), "views": s.get("views"), "duration": s.get("duration")}
        for s in top
    ]
    
    return {
        "available": True,
        "snapshot_count": len(snapshots),
        "patterns": patterns,
        "summary": summary,
        "recommendations": [
            f"Formato com maior média: {max(patterns['by_format'].items(), key=lambda x: x[1]['avg_views'])[0] if patterns['by_format'] else 'N/A'}",
            f"Tópico com maior média: {max(patterns['by_topic'].items(), key=lambda x: x[1]['avg_views'])[0] if patterns['by_topic'] else 'N/A'}",
            f"Duração predominante: {max(patterns['by_duration'].items(), key=lambda x: x[1])[0] if patterns['by_duration'] else 'N/A'}"
        ]
    }

def save_engagement_prior(prior_data: Dict[str, Any]) -> Dict[str, Any]:
    """Salva prior de engajamento baseado em análise manual de Reels"""
    _ensure_learning_dir()
    
    # Validação básica
    required_fields = ["source", "analyzed_at", "top_topics", "top_formats"]
    for field in required_fields:
        if field not in prior_data:
            prior_data[field] = f"auto_{field}"
    
    prior_data["saved_at"] = datetime.now().isoformat()
    prior_data["version"] = 1
    
    ENGAGEMENT_PRIOR.write_text(json.dumps(prior_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"success": True, "path": str(ENGAGEMENT_PRIOR), "data": prior_data}

def get_combined_learning_for_selector() -> Dict[str, Any]:
    """
    Retorna aprendizado combinado para usar no ClipSelector e HeadlineStudio.
    
    Mescla:
    - performance_patterns (engajamento Instagram)
    - feedback_calibration (likes/dislikes na ferramenta)
    - approved_clip_prior (cortes aprovados)
    - engagement_prior (arquivo manual)
    """
    _ensure_learning_dir()
    
    status = get_engagement_learning_status()
    perf_patterns = analyze_performance_patterns()
    
    combined = {
        "available": status["combined_eligible"],
        "sources": {
            "performance": perf_patterns["available"],
            "feedback": status["editor_feedback"]["available"],
            "approved": status["approved_clips"]["available"],
            "engagement_file": status["engagement_prior_file"]["exists"]
        },
        "feedback_calibration": status["editor_feedback"]["calibration"] if status["editor_feedback"]["available"] else {},
        "performance_patterns": perf_patterns["patterns"] if perf_patterns["available"] else {},
        "recommendations": []
    }
    
    # Gera recomendações combinadas
    if perf_patterns["available"]:
        combined["recommendations"].extend(perf_patterns.get("recommendations", []))
    
    if status["editor_feedback"]["available"]:
        cal = status["editor_feedback"]["calibration"]
        combined["recommendations"].append(f"Feedback interno: {cal.get('sample_size')} decisões, use para calibrar ranking")
    
    if status["approved_clips"]["available"]:
        combined["recommendations"].append(f"Cortes aprovados: {status['approved_clips']['approved_count']} amostras para prior")
    
    return combined

def import_instagram_reels_manual(reels_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Importa dados manuais de Reels do Instagram para aprendizado.
    
    Formato esperado por reel:
    {
        "url": "https://instagram.com/reel/...",
        "views": 100000,
        "likes": 5000,
        "comments": 300,
        "topic": "economia",
        "format": "vertical_916",
        "duration": 45,
        "headline": "Texto da arte",
        "transcript_excerpt": "Trecho da legenda"
    }
    
    Salva como performance snapshots e engagement prior.
    """
    _ensure_learning_dir()
    
    imported = 0
    errors = []
    
    # Salva como engagement prior agregado
    topics_count = {}
    formats_count = {}
    total_views = 0
    
    for reel in reels_data:
        try:
            topic = reel.get("topic", "geral")
            fmt = reel.get("format", "vertical_916")
            views = int(reel.get("views", 0))
            
            topics_count[topic] = topics_count.get(topic, 0) + 1
            formats_count[fmt] = formats_count.get(fmt, 0) + 1
            total_views += views
            imported += 1
        except Exception as e:
            errors.append(str(e))
    
    # Salva prior agregado
    prior = {
        "source": "instagram_manual_import",
        "analyzed_at": datetime.now().isoformat(),
        "total_reels": imported,
        "total_views": total_views,
        "avg_views": total_views / imported if imported else 0,
        "top_topics": sorted(topics_count.items(), key=lambda x: x[1], reverse=True)[:5],
        "top_formats": sorted(formats_count.items(), key=lambda x: x[1], reverse=True)[:5],
        "raw_data": reels_data[:20]  # Salva até 20 para referência
    }
    
    save_engagement_prior(prior)
    
    return {
        "success": True,
        "imported": imported,
        "errors": errors,
        "prior": prior,
        "next_steps": [
            "Os dados foram salvos em engagement_prior.json",
            "Eles serão usados no ClipSelector para priorizar tópicos e formatos com maior engajamento",
            "Adicione mais Reels com views altas para melhorar calibração"
        ]
    }
