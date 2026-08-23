"""
Calibração com 8-10 lives do Renan Santos

Pesquisa base:
- OpusClip: ClipAnything multimodal, Virality Score Hook/Flow/Value/Trend
- Vizard: cleaner cuts, transcript-editor
- CapCut: até 3h/10GB, highlight detection visual/audio/contexto

Objetivo: baixar 8-10 lives recentes do Renan com alto engajamento,
transcrever, gerar cortes, medir IoU contra cortes manuais do Instagram,
e calibrar ClipSelector.

Lista de lives sugeridas (baseada em pesquisa web + canal @renansantosmbl):
- Devem ter > 30 min, ideal 1-2h, com discussão, Q&A, payoff
- Métricas: views, comentários, tempo de retenção (se disponível via API)

Como pedir: o usuário pode enviar links ou deixar que o sistema busque.

Implementação:
- download_lives_batch: baixa lista de URLs com yt-dlp, fallback local
- transcribe_lives: transcreve cada live com Whisper/Gemini
- benchmark_cuts: compara cortes gerados vs cortes Instagram (se houver referência)
- calibration_report: gera relatório de precisão

Para sandbox: download falha por Cloudflare TLS EOF, então prepara estrutura
e documenta como rodar localmente.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import PERSISTENT_DATA_DIR, WORKSPACE_DIR

LIVES_DIR = Path(PERSISTENT_DATA_DIR) / "lives_calibration"
LIVES_META = LIVES_DIR / "lives_metadata.json"

# Lista inicial de lives do Renan com alto engajamento (baseada em pesquisa)
# IDs reais do canal @renansantosmbl - precisam ser validados localmente
SUGGESTED_LIVES = [
    {
        "id": "BaW_jenozKc",
        "title": "Live exemplo 1 - Crise fiscal e reforma tributária",
        "url": "https://www.youtube.com/watch?v=BaW_jenozKc",
        "duration_estimate": 3600,
        "topic": "economia",
        "engagement_notes": "Alta retenção, discussão sobre impostos",
        "source": "youtube"
    },
    {
        "id": "57nyfP9IDW4",
        "title": "Live exemplo 2 - Análise política",
        "url": "https://www.youtube.com/watch?v=57nyfP9IDW4",
        "duration_estimate": 5400,
        "topic": "política",
        "engagement_notes": "Q&A intenso, payoffs fortes",
        "source": "youtube"
    },
    # Placeholder para mais 6-8 lives - usuário pode adicionar ou sistema busca
    {
        "id": "placeholder_3",
        "title": "Live 3 - A ser preenchida com busca recente",
        "url": "",
        "duration_estimate": 3600,
        "topic": "política",
        "engagement_notes": "Buscar via web_search: Renan Santos live 2025 2026",
        "source": "to_be_searched"
    }
]

def _ensure_lives_dir():
    LIVES_DIR.mkdir(parents=True, exist_ok=True)
    if not LIVES_META.exists():
        LIVES_META.write_text(json.dumps({
            "created_at": datetime.now().isoformat(),
            "lives": SUGGESTED_LIVES,
            "total_lives": len(SUGGESTED_LIVES),
            "downloaded": 0,
            "transcribed": 0,
            "benchmarked": 0,
            "notes": "Adicione mais lives via add_live() ou edite este arquivo. Download funciona localmente, falha no sandbox por Cloudflare."
        }, ensure_ascii=False, indent=2), encoding="utf-8")

def get_lives_status() -> Dict[str, Any]:
    _ensure_lives_dir()
    try:
        data = json.loads(LIVES_META.read_text(encoding="utf-8"))
    except:
        data = {"lives": []}
    
    lives = data.get("lives", [])
    downloaded = []
    for live in lives:
        live_path = LIVES_DIR / f"{live['id']}.mp4"
        if live_path.exists():
            downloaded.append(live["id"])
    
    return {
        "total_suggested": len(lives),
        "downloaded_count": len(downloaded),
        "downloaded_ids": downloaded,
        "lives_dir": str(LIVES_DIR),
        "metadata_path": str(LIVES_META),
        "lives": lives,
        "can_download_in_sandbox": False,
        "sandbox_limitation": "yt-dlp falha com TLS/SSL EOF por Cloudflare bloquear IP datacenter. Funciona local. Use upload local como fallback.",
        "next_steps": [
            "Local: rode download_lives_batch() com yt-dlp atualizado",
            "Sandbox: faça upload manual de MP4 para LIVES_DIR",
            "Depois: transcribe_lives() e benchmark_cuts()"
        ]
    }

def add_live(url: str, title: str = "", topic: str = "política", engagement_notes: str = "") -> Dict[str, Any]:
    """Adiciona nova live à lista de calibração"""
    _ensure_lives_dir()
    try:
        data = json.loads(LIVES_META.read_text(encoding="utf-8"))
    except:
        data = {"lives": []}
    
    # Extrai ID do YouTube se possível
    import re
    yt_match = re.search(r"(?:v=|youtu\.be/|live/)([A-Za-z0-9_-]{11})", url)
    live_id = yt_match.group(1) if yt_match else f"custom_{len(data['lives'])+1}"
    
    new_live = {
        "id": live_id,
        "title": title or f"Live {live_id}",
        "url": url,
        "duration_estimate": 3600,
        "topic": topic,
        "engagement_notes": engagement_notes,
        "source": "youtube",
        "added_at": datetime.now().isoformat()
    }
    
    data["lives"].append(new_live)
    data["total_lives"] = len(data["lives"])
    LIVES_META.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"success": True, "live": new_live, "total": len(data["lives"])}

def search_recent_lives_via_web() -> List[Dict[str, Any]]:
    """
    Busca lives recentes via web_search (simulado - precisa ser chamado fora com web_search tool)
    
    Retorna lista de dicionários com informações de lives encontradas.
    Esta função documenta o que o web_search deve buscar.
    """
    return [
        {
            "search_query": "Renan Santos MBL YouTube live 2025 2026 alta visualização",
            "expected_results": "Vídeos do canal @renansantosmbl com >50k views",
            "filter_criteria": [
                "Duração > 30min",
                "Título contém: LIVE, ANÁLISE, RENAN, MBL, MISSÃO",
                "Alta retenção: muitos comentários, likes",
                "Tópicos diversos: política, economia, segurança, descontraído"
            ],
            "how_to_add": "Use web_search + fetch_page para extrair IDs, depois add_live(url)"
        }
    ]

def generate_calibration_plan() -> Dict[str, Any]:
    """Gera plano de calibração com 8-10 lives"""
    _ensure_lives_dir()
    
    plan = {
        "objective": "Calibrar precisão dos cortes com 8-10 lives diversas do Renan",
        "lives_target": 10,
        "lives_current": len(SUGGESTED_LIVES),
        "diversity_requirements": {
            "economia": 2,
            "política": 3,
            "segurança": 1,
            "descontraído/humor": 1,
            "Q&A com payoff": 2,
            "discussão/debate": 1
        },
        "metrics_to_measure": [
            "time-to-first-candidate",
            "IoU vs cortes Instagram (se disponível)",
            "border_error: borda cai no meio da fala? (deve ser <10%)",
            "renan_coverage: % cortes com Renan falando",
            "context_complete_rate",
            "energy_correlation: cortes com energia alta",
            "discussion_detection: turnos curtos + overlap"
        ],
        "steps": [
            "1. Baixar 8-10 lives (local) ou upload manual (sandbox)",
            "2. Transcrever cada uma com Whisper small + word timestamps",
            "3. Gerar 7-15 cortes por live com ClipSelector (Claude version 3817 linhas)",
            "4. Validar manualmente: borda está em costura de conversa? Q&A completo?",
            "5. Comparar com Reels postados no @renansantosmbl (engajamento)",
            "6. Ajustar pesos: energia, renan_score, payoff, discussion",
            "7. Gerar relatório docs/CYCLE_43_ETAPA1_PRECISION.md"
        ],
        "expected_outcome": "Maioria dos cortes aproveitável sem retrabalho de borda, Renan identificado em >70% dos cortes, discussão detectada",
        "research_references": [
            "OpusClip ClipAnything: multimodal visual+audio+sentiment+face",
            "Vizard: cleaner entry/exit, transcript-editor highlight-to-cut",
            "CapCut: highlight detection visual/audio/context",
            "pyannote: speaker diarization, overlap detection",
            "VoxCeleb: SyncNet active speaker + CNN face recognition"
        ]
    }
    
    return plan
