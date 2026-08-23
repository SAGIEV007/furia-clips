# Relatório do ciclo 39 — precisão de bordas e elegibilidade editorial

**Data:** 2026-08-21
**Branch:** `claude/repo-access-commits-imgjmk`
**Versão do ciclo:** `6.23`
**Publicação:** funcional `ee2cc6d`; fechamento documental `7950346`.
**Hipótese:** se as bordas finais puderem ser refinadas por timestamps de palavra, sem deslocamento amplo, e se o resultado separar prontidão editorial de score, o Furia reduzirá cortes com seams imprecisos e deixará claro quais candidatos ainda exigem revisão, sem alterar silenciosamente o ranking legado.

## Pesquisa realizada

O ciclo consolidou pesquisas sobre avaliação audiovisual temporal, edição narrativa, produtos profissionais, alinhamento de transcrição, detecção de cena e aprendizagem de ranking. O benchmark FAVE separa alinhamento audiovisual, relações temporais e descrição de momentos; HIVE decompõe o clipping em entendimento narrativo, highlight detection, escolha de abertura/encerramento e poda; WhisperX mostra o valor de forced alignment, word timestamps e diarização, mas também alerta para fala sobreposta, vocabulário e idioma; PySceneDetect oferece sinais de mudança de cena; e trabalhos de pairwise ranking indicam que comparações relativas entre candidatos são mais adequadas ao feedback humano que uma nota absoluta de viralidade [1] [2] [3] [4] [5].

A pesquisa também confirmou que a arquitetura mais forte para o Furia é um **núcleo genérico com perfil especializado Renan/MBL**. O núcleo deve cuidar de transcrição, palavras, pausas, cenas, contexto, payoff, ranking explicável e formatos. O perfil deve fornecer vocabulário, fontes, contas, gates Renan-first, famílias editoriais, padrões de headline e priors Chub/Instagram limitados. Um fork totalmente especializado dificultaria testes e reutilização; um motor totalmente genérico desperdiçaria a memória editorial MBL.

## Implementação

### Refinamento conservador por timestamps de palavra

`ClipSelector._refine_boundaries_with_words()` coleta timestamps `start`, `end` e `word` já existentes na transcrição canônica. O refinamento só é aplicado quando há pelo menos três palavras sobrepondo a janela, cobertura lexical mínima de `0.55`, deslocamento máximo de `3` segundos por borda e duração resultante dentro dos limites do seletor. Sem timestamps por palavra, o caminho é no-op e registra `sem_timestamps_por_palavra`. Quando o candidato é distante ou a cobertura é insuficiente, as bordas permanecem intactas e o motivo aparece na ficha.

O refinamento é executado depois de reparos de abertura, pergunta–resposta, turnos e início do pensamento, mas antes de remoção de irmãos, filtros de não-conteúdo, deduplicação e limite final. Ele não descobre candidatos, não promove seeds Chub, não prova locutor e não muda o score.

### Ledger de elegibilidade editorial

`EditorialRanker._eligibility_ledger()` agora expõe três estados: `ready`, `review` e `blocked`. O score legado continua sendo calculado e ordenado da mesma forma. A nova camada informa se há bloqueio duro, itens de revisão, contexto ou payoff não confirmados, identidade Renan ainda desconhecida, transcrição que exige conferência ou sobreposição de fala/timestamps.

O objetivo é impedir que um candidato com hook alto seja confundido com um corte automaticamente publicável. Todos os candidatos continuam disponíveis para revisão, mas a interface e o diagnóstico agora podem distinguir “melhor pontuação” de “pronto sem revisão”.

## Validação

A suíte focada de precisão terminou com **32 aprovados**. A suíte completa terminou com **582 aprovados e 4 ignorados**. Também passaram `py_compile` para os módulos alterados e `git diff --check`. O modelo BlazeFace foi baixado apenas para a suíte, validado pelo hash esperado e removido depois; nenhum MP4, WAV, SRT, banco SQLite, token ou credencial foi incluído na release.

As novas regressões cobrem: refinamento de ambas as bordas; preservação de candidato mal localizado; no-op sem timestamps por palavra; candidato pronto; candidato em revisão por contexto; bloqueio por sobreposição; e preservação do campo de score histórico.

## Publicação e continuidade

O commit funcional `ee2cc6d` e o fechamento documental `7950346` estão publicados em `origin/claude/repo-access-commits-imgjmk`. O checkout final foi confirmado limpo, com branch local e remoto alinhados. A branch principal não foi alterada.

## Limites honestos

O ciclo não prova ganho editorial em uma live real porque nenhum arquivo de mídia real foi processado nesta rodada. Também não ativa word timestamps automaticamente no transcritor: ele aproveita a informação quando já existe. O próximo experimento deve avaliar custo e benefício de habilitar timestamps por palavra apenas no estágio de refinamento, em vez de pagar esse custo em todas as transcrições.

O ledger de elegibilidade ainda não remove candidatos bloqueados da fila de revisão nem altera a ordem do ranking. Isso é deliberado: primeiro a interface deve mostrar o contrato, depois o benchmark deve medir se a separação reduz falsos aprovados sem esconder bons candidatos.

## Próximos ciclos recomendados

1. Criar um benchmark de hard negatives com cortes quase idênticos: começo sem antecedente, final antes do payoff, fala de terceiro, mesma tese com borda errada, propaganda/jingle e headline infiel.
2. Medir baseline temporal versus palavra/pausa em erro de borda, contexto, payoff, locutor e taxa de revisão.
3. Implementar expansão de candidato em duas passagens: recall barato amplo e refinamento narrativo caro.
4. Fazer a fila de revisão consumir `ready/review/blocked`, com checklist e motivo de rejeição.
5. Só depois testar pairwise ranking por live, formato e conta, com aprovados/rejeitados humanos suficientes.
6. Em seguida aprofundar validação visual seletiva, presets 9:16/1:1/fake tweet, headline grounded e reprocessamento seletivo.

## Referências

[1]: https://cvpr.thecvf.com/virtual/2026/poster/39067 "FAVE: A Structured Benchmark for Fine-Grained Audio-Visual Temporal Evaluation in Multimodal LLMs"
[2]: https://aclanthology.org/2025.emnlp-industry.185/ "From Long Videos to Engaging Clips: A Human-Inspired Video Editing Framework with Multimodal Narrative Understanding"
[3]: https://github.com/m-bain/whisperX "WhisperX: Automatic Speech Recognition with Word-level Timestamps and Diarization"
[4]: https://www.scenedetect.com/docs/latest/api/detectors.html "PySceneDetect detectors"
[5]: https://www.cv-foundation.org/openaccess/content_cvpr_2016/html/Yao_Highlight_Detection_With_CVPR_2016_paper.html "Highlight Detection With Pairwise Deep Ranking for First-Person Video Summarization"
