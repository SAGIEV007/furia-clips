#!/usr/bin/env bash
set -u
cd /home/ubuntu/furia-clips-rebuild
for spec in \
  '1. Olha, você pode trabalhar menos e ganhar a mesma coisa.mp4|Avalie se o gancho é autossuficiente, se começa no início de uma ideia, se a fala é a do Renan, se existe pergunta necessária antes do trecho e se o enquadramento vertical está publicável.' \
  '5. Isso é um problema social gigantesco.mp4|Avalie contexto, começo, conclusão, presença de pergunta e resposta, clareza da tese e possíveis cortes melhores dentro do mesmo trecho.' \
  '10. dura contra o crime, como articular isso.mp4|Avalie se a pergunta está preservada, se o trecho da resposta sobre segurança é completo, se há sobreposição de vozes e se o corte tem potencial editorial.' \
  '15. fazer isso se os estados cooperarem.mp4|Avalie se o trecho é um bom fechamento, se começa no meio da resposta, se conclui a ideia e se o enquadramento/áudio estão adequados.'; do
  file=${spec%%|*}
  prompt=${spec#*|}
  safe=$(printf '%s' "$file" | tr ' /,' '___' | tr -cd '[:alnum:]_-')
  echo "ANALYZING $file"
  manus-analyze-video "workspace/audit_drive_clips/$file" "Você é um editor sênior de cortes políticos brasileiros. $prompt Informe timestamps observados, participantes, problemas objetivos e uma recomendação aprovar/rejeitar/reeditar. Não invente informações." > "docs/audit-${safe}.txt" 2>&1 || true
done
