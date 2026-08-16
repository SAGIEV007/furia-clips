# Changelog de continuidade

## 1.3 — Gate de pergunta explícita e modo offline do Prompt 2

### Incluído

- Perguntas explícitas com `?` agora exigem resposta suficiente antes de um candidato ser considerado contextualmente completo.
- A flag explicável `question_requires_answer` é propagada pelo seletor e pelo ranker para revisão e diagnóstico.
- Regressões para pergunta sem resposta e para expansão até a resposta antes de avançar para a pauta seguinte.
- Prompt 2 atualizado para não presumir a versão `1.1`, registrar a versão real pelo arquivo `VERSION`, reconhecer a hipótese de payoff como concluída e continuar com melhorias offline quando navegador/Criadores/Corteiros estiverem bloqueados.
- Cópia versionada do Prompt 2 em [`PROMPT_2_EXECUTOR.md`](PROMPT_2_EXECUTOR.md).

### Validação da rodada

A suíte completa passou com `286 passed`; `py_compile` e `git diff --check` foram aprovados. Nenhum navegador, login, cookie, Reel publicado ou nova fonte longa foi necessário para esta alteração. A validação audiovisual da fonte longa do Garimpo permanece pendente.

## 1.2 — Gate de payoff e menor janela completa

### Incluído

- A duração-alvo voltou a ser tratada estritamente como uma dica suave: o seletor não encerra o candidato enquanto o pensamento/payoff estiver aberto.
- A expansão continua até encontrar a menor janela com contexto e payoff completos, sem incluir a pauta seguinte quando o bloco anterior já fecha naturalmente.
- Regressão editorial baseada no padrão observado nos outputs reais: hook forte que terminava antes da conclusão.
- A versão de runtime passa a identificar a especialização editorial desta rodada como `1.2`.

### Validação da rodada

O teste específico de concisão passou com `5 passed`; a suíte completa passou com `284 passed`; `py_compile` e `git diff --check` foram aprovados. A fonte longa do Garimpo foi localizada e o download autenticado foi solicitado, mas o Corteiros não concluiu no sandbox por limitação do helper Electron; nenhum Reel publicado foi usado como fonte de corte nesta rodada.

## 1.1 — Resiliência da análise de cenas e primeiro benchmark real

### Incluído

- Timeout configurável na detecção de cenas via `FURIA_SCENE_DETECTION_TIMEOUT_SECONDS`, com padrão de 120 segundos.
- A detecção de cenas passou a ignorar áudio desnecessário, tratar timeout/erro do ffmpeg e retornar uma linha de base segura (`[0.0]`) sem derrubar o job.
- Três testes de regressão para retorno normal, timeout e retorno não-zero do ffmpeg.
- Primeiro teste real com Reel público do Renan: download, FFprobe, transcrição com 57 segmentos e geração de três clipes verticais.
- Benchmark audiovisual dos três clipes para identificar cortes aprováveis, cortes que terminam antes do payoff e cortes que começam no meio da frase.
- Escada de ingestão legítima documentada no prompt mestre para YouTube bloqueado, plataformas públicas alternativas, Criadores/Campaign Hub e Corteiros.

### Validação da rodada

Os testes específicos passaram com `11 passed` e a suíte completa com `283 passed`; `py_compile` também foi aprovado. O job integrado após a correção permaneceu ativo, concluiu com `3` artefatos e deixou o servidor saudável. O benchmark real mostrou que a estabilidade melhorou, mas a seleção ainda precisa impedir finais antes do payoff e penalizar inícios fragmentados. A versão 1.1 foi publicada no commit `6349d37` após a atualização do estado persistente.

## 1.0 — Fundação do contrato de continuidade

### Incluído

- Fonte única de versão em [`VERSION`](../../VERSION), iniciada em `1.0`.
- Leitura da versão pelo servidor Flask, com exposição no console de progresso, na interface e em `/api/settings`.
- Contrato de versionamento em [`docs/VERSIONING.md`](../VERSIONING.md).
- Instruções de retomada para qualquer IA em [`AGENTS.md`](../../AGENTS.md).
- Estado atual persistente em [`PROJECT_STATE.md`](PROJECT_STATE.md).
- Decisões editoriais e técnicas em [`DECISIONS.md`](DECISIONS.md).
- Procedimento da próxima rodada em [`NEXT_CYCLE.md`](NEXT_CYCLE.md).
- Registro explícito de que vídeos públicos publicados nos perfis do Renan podem ser analisados como corpus audiovisual legítimo.
- Registro dos três formatos editoriais: `16:9 original`, `1:1 Alfinetei` e `fake tweet`.

### Validação concluída

A suíte completa foi executada com `280 passed`; `python -m py_compile app.py` foi aprovado; a versão foi carregada de `VERSION`; e o asset público do BlazeFace foi validado pelo tamanho e SHA-256 do manifesto. A documentação de estado foi atualizada após a publicação no commit `fbbe5ca`, na branch `manus/rebuild-opus-parity`.
