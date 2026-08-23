#!/usr/bin/env python3
"""
Autonomous infinite calibration loop - roda indefinidamente otimizando cortes
Sem parar, sem perguntar, só otimizando

Ciclo:
1. Gera live sintética ou usa real se disponível
2. Roda ClipSelector com pesos atuais
3. Mede métricas (IoU, border_error, renan_coverage, context_complete, hook, payoff, coice, discussion, energy)
4. Otimiza pesos automaticamente
5. Salva relatório
6. Commita e push
7. Repete com próxima live

Para rodar: python autonomous_calibration_loop.py --cycles 100 --delay 2
"""

import time
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
import subprocess

from modules.clip_calibration_engine import run_calibration_cycle, CalibrationEngine

def git_commit_push(message: str):
    try:
        subprocess.run(["git", "add", "-A"], check=False, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], check=False, capture_output=True)
        subprocess.run(["git", "push", "origin", "arena/01a02c77-furia-clips"], check=False, capture_output=True)
        return True
    except Exception as e:
        print(f"Git commit/push falhou: {e}")
        return False

def run_infinite_loop(cycles: int = 100, delay: int = 2, use_synthetic: bool = True):
    print(f"🚀 Iniciando loop autônomo infinito - {cycles} ciclos, delay {delay}s, synthetic={use_synthetic}")
    print(f"Branch: arena/01a02c77-furia-clips")
    print(f"Início: {datetime.now().isoformat()}")
    
    engine = CalibrationEngine()
    initial_weights = engine.weights.copy()
    
    best_viral = 0
    best_context = 0
    total_clips_generated = 0
    
    for cycle in range(1, cycles + 1):
        live_id = f"auto_loop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cycle:04d}_{random.randint(100,999)}"
        
        print(f"\n{'='*80}")
        print(f"CICLO {cycle}/{cycles} - {live_id}")
        print(f"{'='*80}")
        
        try:
            result = run_calibration_cycle(live_id=live_id, use_synthetic=use_synthetic)
            metrics = result['metrics']
            improvements = result['improvements']
            
            total_clips_generated += metrics['total_clips']
            
            # Tracking best
            if metrics['avg_viral_score'] > best_viral:
                best_viral = metrics['avg_viral_score']
            if metrics['context_complete_rate'] > best_context:
                best_context = metrics['context_complete_rate']
            
            print(f"📊 Métricas:")
            print(f"  Clips: {metrics['total_clips']} | Viral: {metrics['avg_viral_score']:.1f} (best {best_viral:.1f}) | RenanCov: {metrics['renan_coverage_avg']:.3f}")
            print(f"  Context: {metrics['context_complete_rate']:.3f} (best {best_context:.3f}) | Payoff: {metrics['payoff_complete_rate']:.3f}")
            print(f"  Coice: {metrics['coice_detected']}/{metrics['total_clips']} | Discussion: {metrics['discussion_detected']} | EnergyPeaks: {metrics['energy_peaks']}")
            print(f"  Hook: {metrics['hook_strength_avg']:.1f} | Flow: {metrics['flow_avg']:.1f} | Value: {metrics['value_avg']:.1f}")
            print(f"  AvgDur: {metrics['avg_duration']:.1f}s")
            
            if improvements:
                print(f"🔧 Otimizações aplicadas:")
                for imp in improvements[:5]:
                    print(f"  - {imp}")
            else:
                print(f"✅ Nenhuma otimização necessária - métricas boas!")
            
            # A cada 5 ciclos, commita
            if cycle % 5 == 0:
                msg = f"Arena auto-calibration ciclo {cycle}/{cycles} - viral {metrics['avg_viral_score']:.1f} context {metrics['context_complete_rate']:.2f} coice {metrics['coice_detected']}/{metrics['total_clips']} hook {metrics['hook_strength_avg']:.1f} total_clips {total_clips_generated}"
                git_commit_push(msg)
                print(f"📤 Commit + push ciclo {cycle}")
            
            # Log para arquivo
            log_path = Path.home() / "FuriaClipsData" / "calibration" / "autonomous_log.jsonl"
            log_entry = {
                "cycle": cycle,
                "timestamp": datetime.now().isoformat(),
                "live_id": live_id,
                "metrics": metrics,
                "improvements": improvements,
                "total_clips_generated": total_clips_generated,
                "best_viral": best_viral,
                "best_context": best_context,
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            time.sleep(delay)
            
        except Exception as e:
            print(f"❌ Erro no ciclo {cycle}: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(delay)
            continue
    
    print(f"\n{'='*80}")
    print(f"🏁 Loop finalizado - {cycles} ciclos")
    print(f"Total clips gerados: {total_clips_generated}")
    print(f"Best viral: {best_viral:.1f} | Best context: {best_context:.3f}")
    print(f"Fim: {datetime.now().isoformat()}")
    print(f"{'='*80}")
    
    # Final commit
    final_status = CalibrationEngine().get_status()
    msg = f"Arena auto-calibration final {cycles} ciclos - total {total_clips_generated} clips best_viral {best_viral:.1f} best_context {best_context:.3f} history {final_status['history_count']}"
    git_commit_push(msg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=20, help="Número de ciclos")
    parser.add_argument("--delay", type=int, default=2, help="Delay entre ciclos em segundos")
    parser.add_argument("--real", action="store_true", help="Tenta usar lives reais se disponíveis")
    args = parser.parse_args()
    
    run_infinite_loop(cycles=args.cycles, delay=args.delay, use_synthetic=not args.real)
