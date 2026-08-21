# Relatório do ciclo 40 — hard negatives e timestamps por palavra como padrão

**Data:** 2026-08-21
**Branch:** `claude/repo-access-commits-imgjmk`
**Versão do ciclo:** `6.24`
**Hipótese:** se o Furia preservar candidatos quase válidos que perderam por duplicata, fingerprint ou vizinhança, com motivo e vencedor, a calibração humana poderá distinguir uma rejeição correta de um falso negativo sem depender de recuperar logs internos; se timestamps por palavra forem padrão, o refinamento de bordas da 6.23 terá evidência real no fluxo local.

## Implementação realizada

O seletor agora mantém um ledger limitado de `hard_negatives` em `candidate_diagnostics`. Cada item registra apenas intervalo, duração, origem, score, confiança, preview textual curto, motivo, vencedor quando aplicável e detalhes escalares limitados. A retenção máxima é de 80 itens por execução; o contador total continua registrando quantos foram observados além do limite.

O ledger é alimentado nos caminhos em que um candidato quase válido é descartado por já ter sido exportado, por duplicata temporal/lexical ou por ser irmão contíguo de uma janela preferida. O mecanismo é diagnóstico-only: ele não muda o candidato vencedor, não altera score, não promove Chub, não remove uma revisão e não contém mídia, transcrição integral, cookies ou credenciais.

A configuração `whisper_word_timestamps` passou a ser `True` por padrão. A configuração continua sobrescritível para máquinas com poucos recursos, mas o caminho editorial agora coleta por padrão os campos necessários para o refinamento conservador de bordas da 6.23. A mudança é particularmente importante para a especialização Renan/MBL porque reduz cortes que começam ou terminam entre palavras sem transformar timestamps em prova de contexto ou de locutor.

## Por que isso melhora a calibração

Um ranking final mostra somente quem venceu; um ledger de hard negatives mostra o que quase venceu e por que perdeu. Isso permite separar duplicata legítima, candidato repetido de um export anterior, janela contígua que perdeu para uma versão mais completa e candidato que talvez devesse sobreviver em outro formato. No futuro, esses pares poderão compor um benchmark pairwise por fonte, conta e formato, mas ainda não são usados para treinar ou alterar pesos automaticamente.

O núcleo continua genérico. A especialização Renan/MBL permanece em perfil: foco Renan-first, memória Chub, gates de locutor, vocabulário e famílias editoriais. Essa separação permite calibrar o motor com fontes de teste sem perder o comportamento específico do universo MBL.

## Validação

A suíte focada de hard negatives, seleção, bordas, ranking e configuração terminou com **46 aprovados**. A suíte completa terminou com **585 aprovados e 4 ignorados**. Também passaram `py_compile` nos módulos alterados, `node --check`, `git diff --check` e a remoção do modelo BlazeFace temporário após a suíte.

As regressões cobrem: duplicata com vencedor explícito; limite de 80 itens e contador total; fingerprint já exportado; preservação da escolha original; padrão de timestamps por palavra; refinamento seguro de bordas; e estados de elegibilidade editorial.

## Limites honestos

O ciclo não processou uma live real e, portanto, não comprova redução de falsos negativos ou aumento de recall editorial. O ledger registra rejeições somente nos filtros instrumentados nesta rodada; ainda não é uma taxonomia completa de todas as saídas descartadas pelo pipeline. Timestamps por palavra melhoram precisão temporal, mas não resolvem sozinhos contexto, anáfora, pergunta, payoff, locutor, risco factual ou headline.

A API do Instagram permanece habilitada na sessão, mas a consulta de conta retornou 403 por falta de permissão da aplicação. Nenhum perfil Instagram foi usado como evidência nesta rodada; a pesquisa continua sustentada pelo Chub e pelos dados locais autorizados.

## Próximo experimento

A próxima hipótese deve materializar um benchmark de hard negatives com decisões humanas: pares da mesma tese com início tardio, final precoce, locutor errado, referência anafórica sem antecedente, payoff ausente, janela duplicada e formato inadequado. O benchmark deve medir erro de borda, contexto, payoff, falso Renan, taxa de revisão e precisão@K antes de qualquer alteração de peso.

## Referências

[1]: https://cvpr.thecvf.com/virtual/2026/poster/39067 "FAVE: avaliação audiovisual temporal fina"
[2]: https://aclanthology.org/2025.emnlp-industry.185/ "HIVE/EMNLP: compreensão narrativa e edição de vídeos longos"
[3]: https://github.com/m-bain/whisperX "WhisperX: timestamps por palavra e diarização"
[4]: https://www.cv-foundation.org/openaccess/content_cvpr_2016/html/Yao_Highlight_Detection_With_CVPR_2016_paper.html "Pairwise deep ranking para highlight detection"
