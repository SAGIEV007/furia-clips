# Estado do Projeto — Furia Clips

**Versão:** 6.63
**Branch:** furia-treino-noturno
**HEAD:** cdcca32
**Divergência origin:** 0 ahead / 0 behind (sincronizada)
**Working tree:** limpo
**Suíte:** 1221 passed, 13 skipped, 3 xfailed (~100s)

## Métricas atuais (régua — sabatina Band)
Fonte: `scripts/regua.py` em `tests/fixtures/acervo_sabatina_band.json` (1923s).
- Cortes entregues: 11 · Adiados pelo portão: 1 · Acervo diz que cabem: 32
- Blocos do Acervo alcançados: 8/10 (80%) — subir
- Abre junto com o assunto: 1/8 (12%) — subir
- Atravessa dois assuntos: 2/11 (18%) — baixar
- Pior repetição entre cortes: 0%
- Blocos engolidos por um corte: 0
- Auto-avaliação: contexto completo 11/11, fecho completo 11/11, abre no meio 0/11, abre fora do entrevistado 0/11

## Bloqueios
- Bug conhecido ffmpeg MSYS2: expressões de crop dinâmico com parênteses/vírgulas causam erro no Windows; fallback estático por segmento ativo.
- Nenhum bloqueio novo.

## Próxima hipótese
- Validar crop estático por segmento em vídeo real do Renan; continuar reframe vertical.
- Integrar `segment_speech` no pipeline de corte automático.
- Aumentar alcance de blocos de 80% para >=90% (ajustar janela/overlap/gates).
- Reduzir abertura junto com assunto de 12% para <=10%.
