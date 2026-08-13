#!/usr/bin/env bash
set -euo pipefail

out_dir="$(cd "$(dirname "$0")/.." && pwd)/docs/video-analysis"
mkdir -p "$out_dir"
prompt='Analise este vídeo curto como um editor audiovisual profissional. Descreva, com timestamps quando possível, o gancho nos primeiros segundos, cortes e ritmo, mudanças de enquadramento, imagens de apoio, legendas (posição, tamanho, cor, palavras destacadas e sincronização), música e efeitos sonoros, pausas, punchlines, construção de contexto e conclusão. Avalie o potencial viral em termos de retenção provável, conflito, especificidade, surpresa e clareza. Separe observação direta de inferência e não invente o que não estiver visível ou audível.'

analyze() {
  local slug="$1"
  local url="$2"
  local target="$out_dir/${slug}.md"
  if [[ -s "$target" ]]; then
    echo "SKIP $slug"
    return
  fi
  echo "ANALYZE $slug"
  manus-analyze-video "$url" "$prompt" > "$target" 2>&1
}

analyze "short_jwd_debates" "https://www.youtube.com/shorts/jwD9BE8swk8"
analyze "short_dhx_canceled" "https://www.youtube.com/shorts/dhxWlF2ueqc"
analyze "short_6jd_leaked_images" "https://www.youtube.com/shorts/6JD9RNDh8f4"
analyze "short_wnbe_bolsa_familia" "https://www.youtube.com/shorts/WNbevf3UM0E"
analyze "short_kf6_response_lula" "https://www.youtube.com/shorts/kF6_TlV5iv4"
analyze "short_caw_response_dirceu" "https://www.youtube.com/shorts/CAW3RKzd09M"
analyze "short_fic_proposta_bandidos" "https://www.youtube.com/shorts/FICJiJcaca0"
analyze "short_lfj_supreme_court" "https://www.youtube.com/shorts/LFJUp35HpJw"
analyze "short_5rew_government" "https://www.youtube.com/shorts/5RewWBkZjyU"
