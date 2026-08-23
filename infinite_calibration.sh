#!/bin/bash
# Infinite calibration loop - roda para sempre, 100 ciclos por vez, sem parar

cd /home/user/furia-clips

CYCLE=1
while true; do
  echo "=========================================="
  echo "INFINITE LOOP - BATCH $CYCLE - 100 ciclos"
  echo "Início: $(date -Iseconds)"
  echo "=========================================="
  
  PYTHONUNBUFFERED=1 python3 -u autonomous_calibration_loop.py --cycles 100 --delay 1
  
  echo "Batch $CYCLE finalizado: $(date -Iseconds)"
  echo "Total batches: $CYCLE, total clips: $((CYCLE * 100 * 15))"
  
  # Commit final do batch
  git add -A
  git commit -m "Arena infinite batch $CYCLE - 100 ciclos - $(date -Iseconds) - total $((CYCLE * 100 * 15)) clips" || true
  git push origin arena/01a02c77-furia-clips || true
  
  CYCLE=$((CYCLE + 1))
  sleep 2
done
