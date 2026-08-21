# Validação e Correção: Erro _text() no Bloco Editorial (2026-08-21)

## Contexto
Durante o teste empírico do pipeline do Furia Clips, após a IA selecionar 4 candidatos e o gate editorial autorizar a renderização (graças às correções anteriores), o sistema travou com a seguinte mensagem na etapa final:
`Erro no corte: _text() takes 1 positional argument but 2 were given`

## Causa Raiz
O pipeline foi capaz de gerar os 4 vídeos `.mp4` físicos com sucesso. No entanto, ao construir o artefato JSON de publicação (o "Bloco Editorial"), a função `build_editorial_block` tentou normalizar e limitar o tamanho de algumas strings.
Em `modules/editorial_block.py`, a função auxiliar `_text(value)` aceitava apenas um argumento, mas o código estava chamando `_text(contract.get("contract_version"), 80)` e `_text(item, 160)` para limitar os caracteres.

## A Solução
Atualizei a assinatura da função `_text` em `modules/editorial_block.py` para `def _text(value: Any, limit: int | None = None) -> str:`.
A função agora aplica o limite corretamente, mantendo a compatibilidade retroativa com as chamadas que não enviam o segundo argumento (usando um limite padrão seguro de 500).

## Resultado
Após essa correção, o pipeline concluiu todas as 5 etapas sem falhas. O arquivo final de log comprovou:
`Corte completo: 4/4 clips gerados`
`Clips salvos em: /tmp/furia_data_clean_20260821_b/exports/test_video_interval_300-1200`
A inspeção via FFprobe confirmou que os vídeos físicos estão perfeitamente legíveis, com codec h264/aac e duração exata.
