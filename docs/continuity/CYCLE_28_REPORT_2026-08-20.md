# Relatório do ciclo 28 — identidade de locutor no foco Renan-first

**Data:** 2026-08-20  
**Branch:** `claude/repo-access-commits-imgjmk`  
**Release:** `6.13`  
**Hipótese:** quando o Furia está configurado para cortes do Renan Santos/MBL, uma transcrição sem diarização não deve ser tratada como contextualmente completa nem seguir como corte pronto; ela deve permanecer como candidato explicitamente revisável até que a identidade do locutor seja confirmada.

## Auditoria e baseline

A branch 6.12 estava limpa e a suíte anterior tinha 532 testes aprovados e 4 ignorados quando o asset BlazeFace era provisionado temporariamente. O banco editorial local usado pelo aplicativo continha 70 clips pendentes, zero aprovações, zero rejeições e zero feedback de headline; portanto, a calibração editorial do ranker ainda não era elegível. Esse resultado é uma limitação do histórico local, não uma permissão para inventar rótulos.

A transcrição persistida em `FuriaClipsData/editorial_sessions/project-57/transcription.json` continha 247 segmentos e aproximadamente 900 segundos, mas nenhum segmento tinha identidade de locutor. A análise local produziu 37 perguntas, 33 candidatos pergunta–resposta, 9 capítulos e 12 hooks. A cobertura temporal dessa sessão estava marcada como desconhecida; por isso, ela já exigia revisão de transcrição, mas não havia um gate específico que impedisse um corte Renan-first sem locutor confirmado.

Antes da alteração, usando o caminho compatível genérico sobre essa transcrição, 5 candidatos saíam com `context_complete=true` mesmo sem qualquer identidade de locutor. Esse comportamento era aceitável apenas para uma ferramenta genérica; era permissivo demais para o objetivo Renan-first.

## Implementação

O `ClipSelector` agora deriva a exigência de identidade a partir do foco editorial, do perfil Renan Santos/MBL e do contexto do canal. Assim, o comportamento cobre tanto o foco explícito `renan_santos` quanto o fluxo real com `editorial_focus=auto` e perfil `renan_santos_politics`.

Cada bloco e candidato carrega agora `speaker_identity_required`, `speaker_identity_available` e `speaker_identity_review_required`. O contrato é propagado por NLP, Gemini/Ollama, expansão de contexto, propostas guiadas pelo Campaign Hub e avaliação final da janela. A existência de uma fronteira de fala limpa deixou de ser confundida com prova de que o locutor é o Renan.

Quando a identidade é necessária e não está disponível, `context_complete` e `qa_bridge` não passam, o candidato recebe `review_required=true` no caminho local e o ranker aplica uma penalidade técnica limitada com motivo explícito. O modo genérico continua compatível: sem perfil/foco Renan-first, a ausência de diarização não cria um bloqueio novo.

O Campaign Hub continua sendo usado como evidência e prior fraco. A consulta read-only do Acervo confirmou que os tiers têm coberturas e tempos de rotulagem diferentes: o tier owner tinha 3 vídeos rotulados na semana observada, enquanto third_party tinha 6 e p50 de aproximadamente 572,7 minutos até rotulagem. Isso reforça a decisão de não tratar qualquer sinal de `renanSpeaking` como verdade universal; a proveniência e o tier continuam visíveis e sujeitos a revisão.

## Validação

| Verificação | Resultado |
| --- | --- |
| Regressões novas de seleção e ranker | **28 aprovadas** |
| Suíte completa com BlazeFace temporário conferido por SHA-256 | **537 aprovadas, 4 ignoradas** |
| Suíte sem o asset externo | 1 falha ambiental conhecida no teste do modelo facial |
| `git diff --check` | Aprovado |
| Comparação em transcrição persistida real | Concluída |
| Branch principal `/home/ubuntu/furia-clips` | Não alterada |
| Cookies, tokens, vídeos grandes e banco local no commit | Não incluídos |

Na comparação pós-implementação, o foco Renan-first produziu 9 candidatos, todos com `speaker_identity_available=false`, `speaker_identity_review_required=true`, `context_complete=false` e `review_required=true`. O caminho genérico permaneceu com 5 candidatos contextualmente completos e sem bloqueio novo. O resultado é uma redução deliberada de falsos positivos prontos para renderização, não uma alegação de que o Furia já sabe identificar automaticamente a voz do Renan em qualquer fonte.

## Classificação

| Conclusão | Estado |
| --- | --- |
| O gate é ativado no foco explícito Renan | **Confirmado** |
| O gate é ativado no perfil real Renan com foco `auto` | **Confirmado** |
| Candidato sem diarização passa como contexto completo no fluxo Renan-first | **Corrigido** |
| Modo genérico preserva o comportamento anterior | **Confirmado** |
| Identidade do locutor é automaticamente resolvida pelo Furia | **Não verificado** |
| Download autenticado no notebook do usuário | **Bloqueado/não verificado**; pertence ao ciclo 6.12 de ingestão |
| Ganho de recall em destaques do Campaign Hub | **Não medido nesta rodada**; a hipótese foi precisão de identidade, não cobertura |

## Escopo excluído

Este ciclo não treinou um modelo de voz, não copiou amostras vocais, não alterou pesos de viralidade, não consultou MCP durante o job local, não baixou Reels publicados e não transformou o Campaign Hub em aprovador automático. Também não implementou geração de headline, reframe ou Estúdio de Texto de Arte.

## Próxima hipótese única

> **Se o Furia receber um snapshot local autorizado do Acervo contendo `renanSpeaking`, `speakersNote`, tier e intervalos temporais alinhados à fonte em processamento, então ele poderá preencher parte da identidade de locutor como evidência de proveniência, mantendo revisão obrigatória quando o snapshot estiver ausente, desatualizado, terceiro ou temporalmente desalinhado.**

O próximo ciclo deve medir a taxa de candidatos com identidade resolvida e a precisão dessa evidência em uma fonte longa real, sem usar o sinal do Hub para liberar sozinho um corte.
