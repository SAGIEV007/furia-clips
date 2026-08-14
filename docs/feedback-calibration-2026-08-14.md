# Calibração editorial por feedback humano

## Objetivo

O Furia Clips pode usar decisões finais de revisão para ajustar o ranqueamento de forma **limitada, explicável e reversível**. Aprovações e rejeições não são tratadas como verdade estatística nem substituem contexto, completude, hook, áudio ou segurança visual.

## Elegibilidade

A calibração só fica ativa quando existe uma amostra mínima equilibrada de decisões finais. Clips pendentes, em revisão de contexto ou sem decisão final não entram no cálculo. O resultado expõe a quantidade de decisões, a separação entre aprovados e rejeitados e o estado de elegibilidade para o HUD.

## Clips legados sem fatores

Versões antigas podem ter `clip_feedback` e `review_status`, mas não possuir `score_factors`. Nessa situação, o sistema não inventa fatores ausentes. Ele pode expor apenas um sinal observável de duração, calculado pela diferença entre as médias dos intervalos aprovados e rejeitados.

> A duração é uma preferência editorial fraca. Ela nunca vira limite rígido, não remove um corte contextual e permanece limitada a uma pequena correção no score.

Quando o sinal é elegível, o ranqueador registra `feedback_calibration` no payload, incluindo `sample_size`, contagens por resultado, ajuste aplicado e `duration_signal`. O HUD mostra a origem da influência para o editor poder auditá-la.

## Compatibilidade com novas versões

Quando `score_factors` existe, os deltas por fator continuam sendo usados pelo mecanismo existente, também com limite de influência. Quando não existe, somente a duração observável pode ser usada. O score final nunca é usado sozinho para criar uma falsa causalidade; o `score_gap` é apresentado como diagnóstico e não como ajuste direto.

## ZIP manual

A restauração aceita o backup nativo com `manifest.json` e também um ZIP manual que contenha o arquivo canônico `database/editorial_learning.sqlite3`. Em ambos os casos, o programa executa verificação de integridade SQLite, confirma as tabelas editoriais obrigatórias, valida caminhos de transcrição e faz backup prévio antes da substituição.

A importação manual é marcada como `backup_kind: manual_import`. Arquivos fora de `database/` e `transcripts/`, symlinks, caminhos absolutos, `..` e transcrições com nomes não autorizados continuam bloqueados.

## Privacidade

Decisões pessoais, transcrições, bancos SQLite, vídeos, chaves de API, cookies e caminhos locais ficam em `FuriaClipsData` e não devem ser publicados no GitHub. Este documento descreve somente o contrato técnico; ele não contém a amostra privada usada para validar a calibração.
