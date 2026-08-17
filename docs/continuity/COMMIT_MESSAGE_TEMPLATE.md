# Modelo obrigatório de commit — Furia Clips

Todo commit relevante deve explicar não apenas **o que mudou**, mas **por que mudou, como foi validado e qual é o próximo passo**. O assunto curto não substitui o corpo.

## Formato recomendado

```text
<tipo>: <mudança objetiva> (<versão, se aplicável)

Hipótese:
- Qual problema observável esta mudança testa ou resolve.

Baseline:
- Estado reproduzido antes da mudança.
- Dados, mídia, lote, benchmark ou teste usados.

Implementação:
- Arquivos e componentes modificados.
- Contratos, APIs, schemas ou documentos atualizados.

Escopo excluído:
- O que deliberadamente não foi alterado nesta rodada.

Validação:
- Testes focados:
- Suíte completa:
- compileall / node --check / git diff --check:
- Mídia, FFprobe ou inspeção visual:
- Verificação de segredos e dados privados:

Resultado:
- O que foi confirmado, reproduzido ou corrigido.
- Métricas antes/depois, quando houver.

Limitações e bloqueios:
- O que não foi verificado, permanece provável ou está bloqueado.

Continuidade:
- Relatório: docs/continuity/CYCLE_<n>_REPORT_<data>.md
- Estado: docs/continuity/PROJECT_STATE.md
- Próxima hipótese única: <descrever>
```

## Regras

O resumo pode usar Conventional Commits, como `feat:`, `fix:`, `test:`, `docs:` ou `chore:`, e deve ser curto o suficiente para o histórico. O corpo deve ser factual e não pode declarar sucesso que não foi medido. Em uma alteração exclusivamente documental, escreva explicitamente `Mudança somente documental; nenhum módulo de processamento foi alterado`.

Se uma mudança modifica comportamento observável, o commit deve apontar para a versão registrada em `VERSION` e para o relatório de ciclo. Se altera uma decisão permanente, atualize `DECISIONS.md`. Se altera a hipótese em andamento, atualize `NEXT_CYCLE.md`. Sempre atualize `PROJECT_STATE.md` com o hash final depois de criar o commit; o hash registrado precisa ser conferido contra `git rev-parse --short HEAD`.

Não inclua no commit vídeos, bancos locais, tokens, cookies, chaves, sessões, transcrições privadas, URLs privadas ou dumps. Não use um corpo vazio para uma alteração de código, uma alteração editorial, uma release ou uma mudança de continuidade.

## Exemplo preenchido para a próxima hipótese

```text
feat: expand highlight seeds to complete transcript windows (2.4)

Hipótese:
- Expandir cada highlight do b354 até a menor janela completa aumentará o recall temporal sem alterar o ranking.

Baseline:
- Benchmark b354-v1: 7 candidatos, 3 highlights, recall 0/3, IoU médio 0.0.
- MP4 local de bloco e memória autorizada local, sem chamada MCP durante o job.

Implementação:
- <listar arquivos reais alterados após a execução>.
- Proposta guiada mantida separada de corte aprovado.

Escopo excluído:
- Sem alteração de ranking, diarização, reframe, headlines ou download remoto por range.

Validação:
- <listar testes e métricas reais>.

Resultado:
- <registrar se o recall mudou e se o resultado foi reproduzido>.

Limitações e bloqueios:
- <listar fatos não verificados e divergências>.

Continuidade:
- Relatório: docs/continuity/CYCLE_<n>_REPORT_<data>.md
- Estado: docs/continuity/PROJECT_STATE.md
- Próxima hipótese única: <descrever>
```
