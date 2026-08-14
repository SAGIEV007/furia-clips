#!/usr/bin/env bash
set -u
cd /home/ubuntu/furia-clips-rebuild
mkdir -p docs/instagram_reserva_transcripts
for id in Db_OfZDjKMW Db_R92njTCq Db_VUXqjnyO Db_Y07LFV7J; do
  if [[ -f "docs/instagram_reserva_transcripts/${id}.txt" ]]; then continue; fi
  manus-speech-to-text "workspace/instagram_reserva/${id}.mp4" > "docs/instagram_reserva_transcripts/${id}.txt" 2>&1 || true
done
