#!/usr/bin/env bash
set -u
cd /home/ubuntu/furia-clips-rebuild
mkdir -p docs/instagram_reserva_analysis
PROMPT='Analise este Reel como editor de vídeo profissional. Responda em português brasileiro, sem inventar: duração e resolução; proporção; estrutura temporal com timestamps; gancho; cada corte ou mudança visual relevante; quem fala e em que momentos; enquadramento e se acompanha o locutor; legendas/GC, posição, estilo, palavras destacadas e legibilidade; música, efeitos, mixagem e pausas; ritmo e densidade de informação; pergunta e resposta; contexto; conclusão; e decisões de edição que devem virar critérios do Furia Clips. Separe fatos observados de hipóteses. Dê uma classificação final gold, good, needs_edit ou weak e uma recomendação concreta para automação.'
for id in Db_OfZDjKMW Db_R92njTCq Db_VUXqjnyO Db_Y07LFV7J; do
  video="workspace/instagram_reserva/${id}.mp4"
  echo "ANALYZE $id"
  manus-analyze-video "$video" "$PROMPT" > "docs/instagram_reserva_analysis/${id}.stdout.txt" 2>&1 || true
  latest=$(ls -t video_${id}_analysis_*.md 2>/dev/null | head -1 || true)
  if [[ -n "$latest" ]]; then cp "$latest" "docs/instagram_reserva_analysis/${id}.md"; fi
done
