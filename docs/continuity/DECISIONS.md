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


## D-013 — Transcrição manual é timeline canônica

Quando o editor fornece uma transcrição ou segmentos timestampados, o sistema deve marcá-los como confirmados pelo editor, usá-los como referência temporal principal e nunca iniciar Whisper silenciosamente por falta de um marcador de origem. A qualidade e a cobertura continuam sujeitas a revisão, mas a proveniência precisa ser visível.

## D-014 — Multimodal usa proxy descartável

A análise audiovisual opcional deve enviar uma cópia compactada e temporária, preservando o vídeo original e a transcrição canônica. A compactação reduz resolução, amostragem visual e bitrate de áudio de modo adaptativo à duração; falha ou limite do Gemini deve produzir fallback local explícito, não bloquear a seleção.

## D-015 — Evidência editorial fica fora do Git

Transcrições, dossiês de contexto, headlines geradas, escolhas/rejeições e aprovações/rejeições de clips são evidências de sessão e devem ser arquivadas em `FuriaClipsData/editorial_sessions`, sem entrar no repositório. O banco continua sendo a fonte operacional; os arquivos humanamente legíveis são a trilha para calibração futura.

## D-016 — AV1 não depende de aceleração de hardware

Fontes AV1 devem usar decodificação FFmpeg por software nas etapas de análise e renderização. Se o layout facial não puder ser validado com segurança, o Furia deve preservar o enquadramento original e registrar o fallback, em vez de insistir em OpenCV/MediaPipe e gerar erros repetidos.

## D-017 — Cobertura acompanha a timeline de seleção

Quando a transcrição integral é recortada para remover pré-roll, a transcrição de seleção deve preservar cobertura temporal, proveniência e qualidade da fonte canônica. Perder esses metadados não pode transformar uma transcrição válida em “não validada” nem adiar todos os candidatos por um falso gate técnico.

## D-019 — Campaign Hub rico é benchmark antes de ser peso

O Furia Clips pode aproveitar blocos QA-gated, perguntas-gatilho, autossuficiência, payoff, destaques, riscos, tópicos, transcrições e relações temporais do Campaign Hub para calibrar a seleção. A primeira integração deve comparar essas unidades com candidatos locais em um benchmark versionado e read-only. Nenhum campo do Campaign Hub aprova automaticamente um corte, e nenhuma métrica histórica pode compensar gates de contexto, transcrição, locutor ou evidência visual.

O aplicativo local continua usando snapshots autorizados fora do checkout. O agente pode consultar o MCP para pesquisa e gerar o snapshot, mas o processamento local não deve depender de uma chamada MCP por job. Contas, plataformas, crossposts, métricas settled/provisórias e rótulos de publicação devem permanecer separados. A release 2.2 materializou esta decisão em um benchmark persistente; no caso b354, sete candidatos cobriram `0/3` destaques temporais, sem transformar o resultado em peso automático.

## D-020 — Ferramentas profissionais inspiram capacidades, não escopo indiscriminado

Recursos observados em OpusClip, Descript e Riverside — foco por locutor/tópico, busca editorial, score multifatorial, presets, reframe com preservação de evidência e edição baseada em transcrição — podem orientar melhorias no núcleo de seleção. Editor geral estilo CapCut, edição pós-renderização de legendas/headlines, avatars, voz, música e publicação automática permanecem adiados até que precisão contextual, benchmark e estabilidade estejam maduros.

## D-021 — Cookies de navegador são locais e descartáveis
A ingestão pública pode aceitar apenas o nome normalizado do navegador local e um User-Agent opcional. O yt-dlp pode ler a base de cookies no mesmo computador por `cookiesfrombrowser`, mas o Furia não deve receber, armazenar, logar, versionar ou transmitir o conteúdo dos cookies, tokens ou senhas. A preferência persistida deve começar vazia, e mensagens anti-bot/403 devem oferecer fallback seguro por MP4 local sem prometer que retries idênticos resolverão o bloqueio.

## D-022 — Fronteira de fala não prova identidade Renan-first

Uma transcrição pode ter timestamps limpos e ainda não informar quem falou. No foco Renan Santos/MBL, `speaker_turn_valid` ou uma fronteira de entrevista não substitui `speaker_identity_available`. Sem diarização, marcador confiável ou evidência temporal alinhada do Campaign Hub, `context_complete` e `qa_bridge` não liberam o candidato como corte pronto; ele permanece disponível para diagnóstico e revisão humana. O modo genérico não herda esse bloqueio automaticamente.

## D-023 — Snapshot rico melhora cobertura antes de melhorar precisão

O Campaign Hub é útil quando fornece blocos, highlights, intervalos, riscos e `renanSpeaking` alinhados à fonte local, mas sua influência deve ser medida separadamente em cobertura, borda, contexto, locutor e aprovação humana. Um match temporal com `renanSpeaking=true` só pode preencher evidência de identidade quando cobre substancialmente o candidato e vem de tier `owner` ou `allied`; permanece `evidence_only` e não libera renderização sozinho. Tiers `third_party`, `critical`, `renanSpeaking=false`, snapshots ausentes ou desalinhados ficam em revisão. A concatenação de propostas guiadas antes do pool local não é considerada fusão final; o próximo ciclo deve usar quota, deduplicação e ranking conjunto.

## D-024 — Benchmark divergente bloqueia calibração

Uma integração do Campaign Hub não pode ser considerada útil nem publicada porque anexou evidência a candidatos: ela precisa demonstrar ganho reproduzível em cobertura, borda, contexto ou revisão contra o mesmo manifesto de benchmark. Quando dois harnesses produzem resultados incompatíveis na mesma fonte e fixture, a divergência é o problema principal do ciclo; pesos, quotas e precedência permanecem congelados até que cada seed, fusão e descarte seja auditável. A release 6.14 continua sendo a referência funcional enquanto essa reconciliação não estiver concluída.
