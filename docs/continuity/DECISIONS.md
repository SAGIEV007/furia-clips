# Decisões persistentes do Furia Clips

## D-001 — Contexto vence slogan

Um corte curto e agressivo não deve vencer um trecho um pouco mais longo que seja autossuficiente. A menor janela suficiente é preferida, mas a janela só pode ser reduzida depois que setup, referência, tese e payoff continuarem compreensíveis.

## D-002 — Gates antes do ranking

Contexto ausente, início no meio da frase, pergunta sem resposta, final truncado, locutor incorreto, duração inválida, mídia sem stream e dependência visual ausente são gates ou penalidades fortes antes do score de hook. Emoção e palavras virais não podem compensar falha estrutural.

## D-003 — Campaign Hub como prior fraco

Métricas do Campaign Hub ajudam a calibrar padrões, mas não substituem a leitura do trecho. O dataset mantém separados perfil, plataforma, crosspost, métricas provisórias/estabelecidas, origem do locutor e tipo de rótulo.

## D-004 — Vídeos públicos aprovados são corpus audiovisual

Cortes publicados nos perfis públicos do Renan são exemplos de seleção editorial. Quando acessíveis, devem ser analisados por vídeo e não somente por metadata: composição, ritmo, legenda, texto em tela, headline, formato e relação entre fala e arte são sinais de treinamento.

## D-005 — Formato depende do conteúdo

`16:9 original`, `1:1 Alfinetei` e `fake tweet` são modelos editoriais diferentes, não apenas dimensões. O sistema deve recomendar formato e explicar a compatibilidade com a fala.

## D-006 — Headline fiel à fala

Headline é uma camada editorial derivada da transcrição e do contexto, não uma invenção independente. A geração deve produzir alternativas específicas por formato e avaliar fidelidade factual, clareza, impacto, legibilidade e risco de exagero.

## D-007 — Uma hipótese por ciclo

Uma rodada de melhoria deve escolher uma hipótese principal, medir o baseline, fazer a menor alteração necessária, criar regressão e comparar antes/depois. Isso permite saber o que realmente melhorou.

## D-008 — Versionamento operacional

A versão pública inicial é `1.0`, mantida em `VERSION`. O console, a API, a interface, os jobs e os pacotes de diagnóstico devem identificar a versão e a revisão Git. Mudanças observáveis devem incrementar a versão conforme `docs/VERSIONING.md`.

## D-009 — Branch antes de merge

O agente pode criar branch, commit e push no GitHub autorizado. Merge na principal exige autorização explícita. Vídeos grandes, bancos, tokens, cookies e dados pessoais ficam fora do Git.

## D-010 — Transcrição leve separada do corte

A operação somente-transcrição por URL usa áudio por padrão, arquiva timestamps e não cria projeto nem gera cortes. O download de vídeo permanece reservado à fonte operacional que será cortada.

## D-011 — Revisão técnica é fronteira de renderização

Quando o ranker marca `technical_gate_status=review`, o candidato continua disponível para diagnóstico e revisão humana, mas não deve ser renderizado como corte pronto. Perguntas sem ponte resposta–pergunta validada e alegações sensíveis sem contexto/evidência explícitos não podem ser compensadas por score alto.

## D-012 — Pré-roll é fronteira de seleção, não conteúdo editorial

Quando uma fonte longa contém propaganda ou intro antes da live, a seleção deve usar apenas a partir de uma fronteira temporal segura, enquanto a transcrição integral permanece arquivada para auditoria. O detector deve exigir evidência forte de abertura de live; uma saudação genérica isolada não autoriza corte automático. Na dúvida, preservar a timeline completa para revisão é preferível a remover conteúdo editorial válido.
