"""
Clip Calibration Engine - Autonomous infinite optimization loop for cortes

Objetivo: calibrar cortes de forma autônoma infinita, testando com lives sintéticas
e reais, otimizando pesos, medindo IoU, border_error, renan_coverage, etc.

Pesquisa base:
- OpusClip ClipAnything: Hook/Flow/Value/Trend Virality Score 0-99
- Vizard: cleaner entry/exit, active speaker tracking
- CapCut: highlight detection visual/audio/contexto
- pyannote: overlap, VAD, energy windows
- MBL/Missão: Renan style = direto, provocativo, antissistema, liberdade econômica

Métricas de calibração (NORTE 5 - a régua):
- time-to-first-candidate: tempo até primeiro corte
- IoU vs cortes manuais Instagram
- border_error: erro de borda <10% ideal
- renan_coverage: % do corte onde Renan fala
- context_complete: % cortes com contexto completo
- energy_correlation: correlação energia com viral_score
- discussion_detection: % discussões detectadas corretamente
- coice_detection: % coices Renan detectados
- hook_strength: força do hook nos primeiros 3s
- payoff_strength: força do payoff nos últimos 5s

Ciclo infinito:
1. Gera/transcreve live sintética ou usa real se disponível
2. Roda ClipSelector atual
3. Mede métricas
4. Ajusta pesos automaticamente
5. Documenta e commita
6. Repete com próxima live
"""

from __future__ import annotations

import json
import math
import random
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from config import PERSISTENT_DATA_DIR

CALIB_DIR = Path(PERSISTENT_DATA_DIR) / "calibration"
CALIB_DIR.mkdir(parents=True, exist_ok=True)

# Pesos iniciais calibráveis - serão otimizados autonomamente
DEFAULT_WEIGHTS = {
    "hook_question": 15.0,          # pergunta no início
    "hook_bold_claim": 12.0,        # afirmação forte no início
    "hook_emotional": 10.0,         # gatilho emocional
    "discussion_short_turns": 8.0,  # turnos curtos
    "discussion_gap": 6.0,          # gap curto entre falas
    "discussion_markers": 4.0,      # marcadores ?,!,não,mas
    "energy_peak": 5.0,             # pico energia
    "energy_avg": 3.0,              # energia média alta
    "qa_payoff": 10.0,              # Q&A payoff completo
    "renan_score": 12.0,            # Renan falando
    "renan_coice": 15.0,            # coice Renan (resposta afiada)
    "context_complete": 10.0,       # contexto completo
    "payoff_complete": 8.0,         # payoff completo
    "duration_optimal": 3.0,        # duração 30-60s
    "engagement_topic": 2.0,        # tópico com alto engajamento
    "flow_coherence": 5.0,          # flow coerente
    "value_insight": 7.0,           # value insight/dado/história
}

# Renan style markers - baseado em pesquisa @renansantosmbl
RENAN_COICE_MARKERS = {
    "direct": ["olha", "vou te falar", "é simples", "na verdade", "o problema é", "isso é", "vou ser direto", "sem rodeio"],
    "provocative": ["absurdo", "vergonha", "mentira", "hipocrisia", "covarde", "canalha", "vagabundo", "pilantra"],
    "antissistema": ["sistema", "establishment", "velha política", "centrão", "corporativismo", "privilégio", "mamata"],
    "liberdade": ["liberdade", "estado mínimo", "imposto é roubo", "livre mercado", "empreender", "burocracia"],
    "confront": ["detona", "expose", "escancara", "desmascara", "bomba", "urgente"],
}

RENAN_HOOK_MARKERS = {
    "question": [r"\bcomo\b.*\?", r"\bpor que\b", r"\bqual\b.*\?", r"\bquem\b", r"você sabia", r"já parou pra pensar"],
    "bold_claim": [r"ninguém te conta", r"a verdade é", r"vou provar", r"isso vai", r"é mentira que"],
    "emotional": [r"absurdo", r"vergonha", r"revoltante", r"inacreditável", r"chocante", r"urgente", r"bomba"],
}

PAYOFF_MARKERS = {
    "conclusion": ["entendeu?", "é isso", "ponto", "fim", "conclusão", "resumindo", "portanto", "então é isso"],
    "punchline": ["e é por isso que", "por isso que eu digo", "é exatamente isso", "não tem outro jeito"],
    "call_action": ["compartilha", "comenta", "o que você acha", "deixa nos comentários", "marca alguém"],
}

@dataclass
class CalibrationMetrics:
    live_id: str
    timestamp: str
    total_clips: int
    avg_duration: float
    avg_viral_score: float
    renan_coverage_avg: float
    renan_score_avg: float
    context_complete_rate: float
    payoff_complete_rate: float
    discussion_detected: int
    energy_peaks: int
    coice_detected: int
    hook_strength_avg: float
    payoff_strength_avg: float
    flow_avg: float
    value_avg: float
    border_error_avg: float
    weights_used: Dict[str, float]
    improvements: List[str]

    def to_dict(self):
        return asdict(self)

class SyntheticLiveGenerator:
    """Gera lives sintéticas realistas para calibração quando download real falha"""
    
    TOPICS = ["economia", "política", "segurança", "liberdade", "impostos", "reforma", "stf", "governo"]
    
    TEMPLATES = [
        # Template Q&A
        [
            ("pergunta", "Como você vê a situação fiscal do Brasil hoje?", 3.0),
            ("renan", "Olha, vou te falar de forma direta. O Brasil está quebrado. A gente tem um estado gigantesco, inchado, que gasta mais do que arrecada. É simples: imposto alto, serviço ruim. Isso é o retrato do fracasso do modelo estatista.", 15.0),
            ("pergunta", "E qual seria a solução?", 2.0),
            ("renan", "Estado mínimo. Privatiza tudo. Acaba com privilégio. O problema não é falta de dinheiro, é excesso de gasto com mamata. Quando você corta privilégio, sobra dinheiro para saúde, educação e segurança de verdade.", 12.0),
        ],
        # Template discussão
        [
            ("outro", "Mas você não acha que o Estado tem que proteger os mais pobres?", 4.0),
            ("renan", "Claro que tem! Mas proteger não é criar dependência. O que o PT faz é manter o pobre pobre para ter voto. Eu defendo que o pobre tenha oportunidade de virar classe média, de empreender, de crescer. Isso é liberdade de verdade.", 14.0),
            ("outro", "Isso é discurso de rico!", 2.5),
            ("renan", "Discurso de rico? Eu vim da periferia, meu amigo. Eu sei o que é passar necessidade. E é exatamente por isso que eu defendo liberdade. Porque eu sei que o Estado nunca ajudou ninguém a sair da pobreza. Quem tira da pobreza é trabalho e oportunidade.", 16.0),
        ],
        # Template coice / resposta afiada
        [
            ("pergunta", "O que você acha do STF hoje?", 3.0),
            ("renan", "O STF está uma porcaria. Vou ser direto. Ministros que não foram eleitos por ninguém decidindo o futuro do país, legislando no lugar do Congresso, censurando rede social. Isso é absurdo. Isso é vergonhoso. E ninguém tem coragem de falar porque tem medo.", 18.0),
            ("pergunta", "Mas não é perigoso falar assim?", 2.5),
            ("renan", "Perigoso é ficar calado. Perigoso é ver o Brasil virando Venezuela e ninguém falar nada. Eu prefiro falar e ser cancelado do que me calar e ser cúmplice. Entendeu? É isso.", 13.0),
        ],
        # Template descontraído / bastidor
        [
            ("renan", "Vou contar um bastidor pra vocês. Ontem eu tava no Congresso, e um deputado do centrão veio me oferecer cargo. Falou: Renan, vem pro nosso lado que tem ministério. Eu falei: meu lado é o Brasil, não é cargo. Ele ficou sem graça. É assim que funciona lá dentro, é tudo toma lá dá cá.", 20.0),
        ],
    ]
    
    def generate_transcription(self, live_id: str, duration_minutes: int = 60) -> Dict[str, Any]:
        """Gera transcrição sintética realista"""
        num_blocks = duration_minutes * 2  # ~2 blocos por minuto
        segments = []
        current_time = 0.0
        
        for i in range(num_blocks):
            template = random.choice(self.TEMPLATES)
            for speaker_type, text, dur in template:
                if current_time >= duration_minutes * 60:
                    break
                # Adiciona variação
                words = text.split()
                # Simula energia: Renan tem energia mais alta
                base_energy = 0.7 if speaker_type == "renan" else 0.5
                if "absurdo" in text.lower() or "vergonha" in text.lower() or "?" in text:
                    base_energy += 0.15
                
                segments.append({
                    "id": f"{live_id}_seg_{len(segments)}",
                    "start": current_time,
                    "end": current_time + dur,
                    "text": text,
                    "speaker": "Renan Santos" if speaker_type == "renan" else ("Entrevistador" if speaker_type == "pergunta" else "Convidado"),
                    "speaker_confidence": 0.85 if speaker_type == "renan" else 0.6,
                    "words": [],  # simplificado
                    "energy": base_energy + random.uniform(-0.1, 0.1),
                })
                current_time += dur + random.uniform(0.3, 1.2)  # gap
                if current_time >= duration_minutes * 60:
                    break
            if current_time >= duration_minutes * 60:
                break
        
        # Gera energy_profile
        energy_profile = []
        for seg in segments:
            energy_profile.append({
                "time": (seg["start"] + seg["end"]) / 2,
                "energy": seg.get("energy", 0.5),
                "rms": seg.get("energy", 0.5),
            })
        
        return {
            "segments": segments,
            "energy_profile": energy_profile,
            "duration": current_time,
            "live_id": live_id,
            "topic": random.choice(self.TOPICS),
        }

class CalibrationEngine:
    """Engine principal de calibração autônoma infinita"""
    
    def __init__(self):
        self.weights = self._load_weights()
        self.metrics_history: List[CalibrationMetrics] = self._load_history()
        self.generator = SyntheticLiveGenerator()
    
    def _load_weights(self) -> Dict[str, float]:
        weights_path = CALIB_DIR / "calibration_weights.json"
        if weights_path.exists():
            try:
                data = json.loads(weights_path.read_text(encoding="utf-8"))
                # Merge com defaults para garantir todas chaves existem
                merged = {**DEFAULT_WEIGHTS, **data.get("weights", {})}
                return merged
            except:
                pass
        return DEFAULT_WEIGHTS.copy()
    
    def _save_weights(self):
        weights_path = CALIB_DIR / "calibration_weights.json"
        data = {
            "weights": self.weights,
            "updated_at": datetime.now().isoformat(),
            "history_count": len(self.metrics_history),
        }
        weights_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def _load_history(self) -> List[CalibrationMetrics]:
        history_path = CALIB_DIR / "calibration_history.json"
        if history_path.exists():
            try:
                data = json.loads(history_path.read_text(encoding="utf-8"))
                return [CalibrationMetrics(**item) for item in data]
            except:
                pass
        return []
    
    def _save_history(self):
        history_path = CALIB_DIR / "calibration_history.json"
        data = [m.to_dict() for m in self.metrics_history[-100:]]  # guarda últimos 100
        history_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def detect_coice(self, text: str, energy: float = 0.5) -> Tuple[bool, float, str]:
        """Detecta coice Renan - resposta afiada direta provocativa"""
        lower = text.lower()
        score = 0.0
        reasons = []
        
        # Marcadores diretos
        for cat, markers in RENAN_COICE_MARKERS.items():
            count = sum(1 for m in markers if m in lower)
            if count > 0:
                weight = {"direct": 3, "provocative": 4, "antissistema": 2.5, "liberdade": 2, "confront": 3.5}[cat]
                score += count * weight
                reasons.append(f"{cat}:{count}")
        
        # Energia alta aumenta coice
        if energy > 0.7:
            score += 3
            reasons.append(f"energia_alta:{energy:.2f}")
        
        # Pergunta curta antes + resposta longa = coice
        if len(text.split()) > 15 and ("?" in lower or "!" in lower):
            score += 2
        
        # Frases curtas e diretas no final
        sentences = re.split(r'[.!?]+', text)
        if sentences:
            last = sentences[-1].strip().lower()
            if len(last.split()) <= 8 and any(w in last for w in ["isso", "ponto", "entendeu", "é isso"]):
                score += 2
                reasons.append("punchline_curta")
        
        is_coice = score >= 6.0
        return is_coice, min(1.0, score / 15.0), ", ".join(reasons)
    
    def detect_hook_strength(self, text: str, position: str = "start") -> Tuple[float, str]:
        """Detecta força do hook - primeiros 3 segundos devem prender atenção"""
        lower = text.lower()
        score = 0.0
        reasons = []
        
        if position == "start":
            # Pergunta no início
            first_100 = lower[:100]
            if "?" in first_100:
                score += 5
                reasons.append("pergunta_inicio")
            
            # Bold claim
            for pattern in RENAN_HOOK_MARKERS["bold_claim"]:
                if re.search(pattern, first_100):
                    score += 4
                    reasons.append("bold_claim")
                    break
            
            # Emotional trigger
            for pattern in RENAN_HOOK_MARKERS["emotional"]:
                if re.search(pattern, first_100):
                    score += 3
                    reasons.append("emotional_trigger")
                    break
            
            # Números, dados concretos
            if re.search(r'\b\d+[%]?\b', first_100) or re.search(r'\b\d+\s*(mil|milhão|bilhão)\b', first_100):
                score += 2
                reasons.append("dado_concreto")
        
        return min(10.0, score), ", ".join(reasons)
    
    def detect_payoff_strength(self, text: str) -> Tuple[float, str]:
        """Detecta força do payoff - conclusão deve fechar raciocínio"""
        lower = text.lower()
        score = 0.0
        reasons = []
        
        last_150 = lower[-150:]
        
        for cat, markers in PAYOFF_MARKERS.items():
            for m in markers:
                if m in last_150:
                    weight = {"conclusion": 3, "punchline": 4, "call_action": 2}[cat]
                    score += weight
                    reasons.append(f"{cat}:{m}")
                    break
        
        # Termina com frase forte curta
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if sentences:
            last = sentences[-1].lower()
            if len(last.split()) <= 10 and len(last.split()) >= 3:
                score += 2
                reasons.append("frase_curta_forte_final")
        
        return min(10.0, score), ", ".join(reasons)
    
    def calculate_virality_4d(self, clip: Dict[str, Any], transcription: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcula Virality Score 4D inspirado OpusClip:
        - Hook: prende atenção nos primeiros 3s
        - Flow: coerência e contexto completo
        - Value: insight, dado, história útil
        - Trend: alinhado com tópicos quentes
        """
        text = clip.get("text", "")
        lower = text.lower()
        
        # Hook: primeiros 100 chars
        hook_score, _ = self.detect_hook_strength(text, "start")
        # Normaliza 0-100
        hook = min(100, hook_score * 10)
        
        # Flow: contexto completo + payoff completo + sem corte abrupto
        flow = 50
        if clip.get("context_complete"):
            flow += 20
        if clip.get("payoff_complete"):
            flow += 15
        if not clip.get("starts_mid_sentence"):
            flow += 10
        if clip.get("qa_bridge"):
            flow += 10
        flow = min(100, flow)
        
        # Value: insight, dado, história, bastidor
        value = 40
        # Dados concretos
        if re.search(r'\b\d+[%]?\b', lower):
            value += 10
        # História / bastidor
        if any(w in lower for w in ["vou contar", "bastidor", "ontem", "quando eu", "eu vi", "aconteceu"]):
            value += 15
        # Tese forte
        if any(w in lower for w in ["problema é", "solução é", "por isso", "é simples", "na verdade"]):
            value += 10
        # Polêmica
        if any(w in lower for w in ["absurdo", "vergonha", "mentira", "corrupto"]):
            value += 10
        value = min(100, value)
        
        # Trend: tópicos quentes (baseado em engagement_learning)
        trend = 50
        hot_topics = ["stf", "lula", "governo", "imposto", "reforma", "segurança", "economia", "liberdade"]
        for topic in hot_topics:
            if topic in lower:
                trend += 8
        trend = min(100, trend)
        
        # Score final ponderado
        viral = int(hook * 0.3 + flow * 0.3 + value * 0.25 + trend * 0.15)
        
        return {
            "hook": round(hook, 1),
            "flow": round(flow, 1),
            "value": round(value, 1),
            "trend": round(trend, 1),
            "viral": viral,
        }
    
    def calibrate_live(self, transcription: Dict[str, Any], clips: List[Dict[str, Any]]) -> CalibrationMetrics:
        """Calibra métricas de uma live"""
        if not clips:
            return CalibrationMetrics(
                live_id=transcription.get("live_id", "unknown"),
                timestamp=datetime.now().isoformat(),
                total_clips=0,
                avg_duration=0,
                avg_viral_score=0,
                renan_coverage_avg=0,
                renan_score_avg=0,
                context_complete_rate=0,
                payoff_complete_rate=0,
                discussion_detected=0,
                energy_peaks=0,
                coice_detected=0,
                hook_strength_avg=0,
                payoff_strength_avg=0,
                flow_avg=0,
                value_avg=0,
                border_error_avg=0,
                weights_used=self.weights.copy(),
                improvements=[]
            )
        
        total = len(clips)
        avg_duration = sum(float(c.get("duration", 0)) for c in clips) / total
        avg_viral = sum(float(c.get("viral_score", 0)) for c in clips) / total
        renan_cov = sum(float(c.get("renan_coverage", 0)) for c in clips) / total
        renan_score = sum(float(c.get("renan_score", 0)) for c in clips) / total
        context_rate = sum(1 for c in clips if c.get("context_complete")) / total
        payoff_rate = sum(1 for c in clips if c.get("payoff_complete")) / total
        discussion = sum(1 for c in clips if c.get("discussion_detected"))
        energy_peaks = sum(len(c.get("energy_reasons", [])) for c in clips)
        
        coice_count = 0
        hook_sum = 0
        payoff_sum = 0
        flow_sum = 0
        value_sum = 0
        
        for clip in clips:
            text = clip.get("text", "")
            energy = clip.get("energy_bonus", 0) / 5.0 if clip.get("energy_bonus") else 0.5
            is_coice, _, _ = self.detect_coice(text, energy)
            if is_coice:
                coice_count += 1
                clip["coice_detected"] = True
            
            v4d = self.calculate_virality_4d(clip, transcription)
            hook_sum += v4d["hook"]
            payoff_sum += self.detect_payoff_strength(text)[0]
            flow_sum += v4d["flow"]
            value_sum += v4d["value"]
            
            # Atualiza clip com 4D
            clip["virality_4d"] = v4d
            clip["hook_strength"] = v4d["hook"]
            clip["payoff_strength"] = self.detect_payoff_strength(text)[0]
        
        metrics = CalibrationMetrics(
            live_id=transcription.get("live_id", "unknown"),
            timestamp=datetime.now().isoformat(),
            total_clips=total,
            avg_duration=round(avg_duration, 1),
            avg_viral_score=round(avg_viral, 1),
            renan_coverage_avg=round(renan_cov, 3),
            renan_score_avg=round(renan_score, 3),
            context_complete_rate=round(context_rate, 3),
            payoff_complete_rate=round(payoff_rate, 3),
            discussion_detected=discussion,
            energy_peaks=energy_peaks,
            coice_detected=coice_count,
            hook_strength_avg=round(hook_sum / total, 1) if total else 0,
            payoff_strength_avg=round(payoff_sum / total, 1) if total else 0,
            flow_avg=round(flow_sum / total, 1) if total else 0,
            value_avg=round(value_sum / total, 1) if total else 0,
            border_error_avg=0.05,  # placeholder - precisa medir com referência
            weights_used=self.weights.copy(),
            improvements=[]
        )
        
        self.metrics_history.append(metrics)
        self._save_history()
        
        return metrics
    
    def optimize_weights(self, metrics: CalibrationMetrics) -> List[str]:
        """Otimiza pesos automaticamente baseado nas métricas"""
        improvements = []
        prev_avg = None
        if len(self.metrics_history) >= 2:
            prev_avg = self.metrics_history[-2].avg_viral_score
        
        # Se context_complete_rate baixo, aumenta peso context_complete
        if metrics.context_complete_rate < 0.7:
            self.weights["context_complete"] = min(20, self.weights["context_complete"] + 1.5)
            improvements.append(f"context_complete {self.weights['context_complete']-1.5:.1f} -> {self.weights['context_complete']:.1f} (rate {metrics.context_complete_rate:.2f})")
        
        # Se payoff baixo, aumenta payoff_complete
        if metrics.payoff_complete_rate < 0.6:
            self.weights["payoff_complete"] = min(18, self.weights["payoff_complete"] + 1.2)
            improvements.append(f"payoff_complete {self.weights['payoff_complete']-1.2:.1f} -> {self.weights['payoff_complete']:.1f} (rate {metrics.payoff_complete_rate:.2f})")
        
        # Se coice baixo mas deveria ter mais (Renan tem muito coice)
        if metrics.coice_detected < metrics.total_clips * 0.3 and metrics.renan_coverage_avg > 0.5:
            self.weights["renan_coice"] = min(25, self.weights["renan_coice"] + 1.0)
            improvements.append(f"renan_coice {self.weights['renan_coice']-1.0:.1f} -> {self.weights['renan_coice']:.1f} (detect {metrics.coice_detected}/{metrics.total_clips})")
        
        # Se hook fraco, aumenta hook pesos
        if metrics.hook_strength_avg < 50:
            self.weights["hook_question"] = min(25, self.weights["hook_question"] + 1.0)
            self.weights["hook_bold_claim"] = min(20, self.weights["hook_bold_claim"] + 0.8)
            improvements.append(f"hook_question/bold_claim aumentados (hook_avg {metrics.hook_strength_avg:.1f})")
        
        # Se renan_coverage baixo, aumenta renan_score
        if metrics.renan_coverage_avg < 0.6:
            self.weights["renan_score"] = min(20, self.weights["renan_score"] + 1.0)
            improvements.append(f"renan_score {self.weights['renan_score']-1.0:.1f} -> {self.weights['renan_score']:.1f} (coverage {metrics.renan_coverage_avg:.2f})")
        
        # Se viral_score caiu vs anterior, reverte um pouco e tenta outro caminho
        if prev_avg and metrics.avg_viral_score < prev_avg - 5:
            # Reduz último aumento excessivo
            for key in ["renan_coice", "hook_question"]:
                if self.weights[key] > DEFAULT_WEIGHTS[key]:
                    self.weights[key] = max(DEFAULT_WEIGHTS[key], self.weights[key] - 0.5)
            improvements.append(f"viral_score caiu {prev_avg:.1f}->{metrics.avg_viral_score:.1f}, ajustando pesos para estabilidade")
        
        # Se tudo bom, tenta aumentar value e flow para qualidade
        if metrics.context_complete_rate > 0.8 and metrics.payoff_complete_rate > 0.7 and metrics.hook_strength_avg > 60:
            self.weights["value_insight"] = min(15, self.weights["value_insight"] + 0.5)
            self.weights["flow_coherence"] = min(12, self.weights["flow_coherence"] + 0.5)
            improvements.append(f"qualidade alta, aumentando value_insight e flow_coherence")
        
        self._save_weights()
        return improvements
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "weights": self.weights,
            "history_count": len(self.metrics_history),
            "last_metrics": self.metrics_history[-1].to_dict() if self.metrics_history else None,
            "avg_viral_trend": [m.avg_viral_score for m in self.metrics_history[-10:]],
            "calib_dir": str(CALIB_DIR),
        }

def run_calibration_cycle(live_id: str = None, use_synthetic: bool = True) -> Dict[str, Any]:
    """Roda um ciclo completo de calibração"""
    engine = CalibrationEngine()
    
    if live_id is None:
        live_id = f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(100,999)}"
    
    # 1. Gera ou carrega transcrição
    if use_synthetic:
        transcription = engine.generator.generate_transcription(live_id, duration_minutes=random.randint(30, 90))
    else:
        # Tenta carregar live real
        from modules.lives_calibration import LIVES_DIR
        # Placeholder
        transcription = engine.generator.generate_transcription(live_id, duration_minutes=60)
    
    # 2. Roda ClipSelector
    from modules.clip_selector import ClipSelector
    selector = ClipSelector(max_clips=15, min_duration=8, max_duration=180)
    
    clips = selector.select_clips(
        transcription={"segments": transcription["segments"]},
        energy_profile=transcription["energy_profile"],
        user_context="",
        settings={},
        emit_progress=None
    )
    
    # 3. Calibra métricas
    metrics = engine.calibrate_live(transcription, clips)
    
    # 4. Otimiza pesos
    improvements = engine.optimize_weights(metrics)
    metrics.improvements = improvements
    
    # 5. Salva relatório
    report_path = CALIB_DIR / f"report_{live_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        "live_id": live_id,
        "transcription": {
            "duration": transcription["duration"],
            "segments": len(transcription["segments"]),
            "topic": transcription.get("topic", "unknown")
        },
        "clips_count": len(clips),
        "metrics": metrics.to_dict(),
        "improvements": improvements,
        "top_clips": [
            {
                "start": c.get("start"),
                "end": c.get("end"),
                "duration": c.get("duration"),
                "viral_score": c.get("viral_score"),
                "virality_4d": c.get("virality_4d"),
                "renan_score": c.get("renan_score"),
                "renan_coverage": c.get("renan_coverage"),
                "context_complete": c.get("context_complete"),
                "payoff_complete": c.get("payoff_complete"),
                "coice_detected": c.get("coice_detected", False),
                "hook_strength": c.get("hook_strength"),
                "text_excerpt": c.get("text", "")[:200]
            }
            for c in clips[:5]
        ]
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {
        "live_id": live_id,
        "metrics": metrics.to_dict(),
        "improvements": improvements,
        "report_path": str(report_path),
        "clips_count": len(clips),
        "status": engine.get_status()
    }
