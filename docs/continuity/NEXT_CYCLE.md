# Próximo ciclo de melhoria — Furia Clips v1.5

## Objetivo da rodada

Usar os candidatos reais da coletiva e da live final de análises renais para calibrar a confiabilidade semântica da transcrição local antes da geração de headlines. O Estúdio de Texto de Arte permanece fora da hipótese principal até que seleção, transcrição e estabilidade estejam mais maduras.

## Hipótese única

> Se o ASR local produzir erros prováveis em nomes próprios, entidades políticas ou termos raros, o Furia deve marcar o trecho para revisão humana e impedir headline definitiva baseada somente nessa transcrição, sem necessariamente descartar o candidato de diagnóstico.

O gate de contexto da 1.4 e o gate técnico da 1.5 permanecem ativos. Não misturar essa hipótese com novos pesos visuais, novos presets ou alteração do Estúdio.

## Procedimento

1. Ler `AGENTS.md`, `README.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/VERSIONING.md` e o `git status`.
2. Repetir a suíte existente antes da mudança e registrar a versão/revisão.
3. Usar os JSONs e transcrições reais de `calibration-collective` e `ultimo-analises-renais` como fixtures de diagnóstico; Reels publicados continuam `reference_only`.
4. Medir nomes próprios, entidades, termos raros, tokens incomuns, baixa confiança lexical quando disponível, palavras incompatíveis com o vocabulário Renan/MBL e divergência com uma legenda corrigida.
5. Criar regressões sintéticas e pelo menos uma regressão baseada em segmento real, sem publicar texto corrigido como se fosse fala original.
6. Implementar uma única alteração no diagnóstico de transcrição/headline: marcar revisão ou bloquear headline definitiva quando o risco semântico superar o limiar.
7. Reprocessar a mesma fixture e comparar falsos positivos, falsos negativos, revisão necessária e preservação da seleção de cortes.
8. Validar a transcrição, a janela temporal, os exports existentes e FFprobe quando houver novo render.
9. Só depois avaliar uma hipótese separada do Estúdio de Texto de Arte, usando headlines derivadas do trecho correto e nunca do SRT de outra fonte.
10. Se a mudança for observável, incrementar `VERSION`, atualizar `CHANGELOG.md`, `PROJECT_STATE.md`, este arquivo e o relatório do ciclo.
11. Executar suíte completa, `py_compile`, `node --check`, `git diff --check`, verificar segredos e publicar a branch de trabalho.

## Formato do relatório

O relatório deve separar o que foi confirmado, reproduzido, corrigido, não verificado ou bloqueado. Inclua versão, revisão, branch, hipótese, arquivos, testes, mídia analisada, métricas antes/depois, exemplos de segmentos com risco de ASR, qualidade editorial e uma única próxima hipótese.
