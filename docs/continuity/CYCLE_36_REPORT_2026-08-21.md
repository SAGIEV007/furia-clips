# Ciclo 36 — pacote amplo de inteligência editorial e proveniência

**Data:** 2026-08-21  
**Versão planejada:** 6.20  
**Branch:** `claude/repo-access-commits-imgjmk`  
**Hipótese:** implementar um pacote amplo, modular e explicável de melhorias para tornar o Furia mais inteligente em cortes de Renan Santos/MBL, sem depender de novas credenciais ou de uma execução do usuário.

## Escopo

Este ciclo avançou o núcleo de cortes, não a fase final futura de WhatsApp, smartwatch, pesquisa remota e dossiês de última hora. O objetivo foi fazer a execução local guardar melhor a identidade da faixa processada, a origem da transcrição, as evidências editoriais, os conflitos de locutor e a fidelidade das headlines.

## Implementação

### Identidade estável de intervalo

O contrato de intervalo agora produz uma identidade determinística baseada na assinatura do conteúdo da fonte, na faixa absoluta processada e na versão do contrato. O caminho temporário criado para processar uma faixa não contamina a identidade.

A identidade foi propagada para criação e atualização de projetos, fingerprints, deduplicação, transcrições, bundles, diagnósticos e payloads de conclusão. Faixas diferentes da mesma live podem coexistir; a mesma faixa pode ser reconhecida mesmo quando o arquivo temporário ou o caminho local muda. Fontes e projetos antigos continuam usando o fallback legado.

### Proveniência e digest da transcrição

O digest canônico da transcrição passou a acompanhar o projeto, o banco, o arquivo persistente e os diagnósticos. A proveniência preserva fonte, tipo de entrada manual, confirmação editorial, cobertura temporal, identidade de faixa e digest. O leitor do banco devolve intervalo e proveniência como objetos estruturados, inclusive para registros antigos com campos vazios.

Quando uma transcrição manual é fornecida, o contrato conserva se a entrada veio como texto ou segmentos. O pipeline continua usando a transcrição manual como timeline canônica e não inicia Whisper ou Gemini silenciosamente para substituí-la.

### Contrato narrativo de contexto

A pré-análise editorial agora expõe `context-contract-v1`, com requisitos mínimos de pergunta/setup, antecedente anafórico, resposta/tese e payoff. O contrato também informa evidências, score de completude, cobertura da transcrição, situação do locutor e motivos de revisão.

O contrato foi incluído no prompt local de seleção e nos dossiês dos candidatos. Ele não afirma que uma ideia é verdadeira; registra o que o corte precisa preservar para ser compreensível e onde a revisão humana ainda é necessária.

### Gate final de locutor

A identificação de voz agora influencia também a fronteira final de renderização. Quando existe um veredito confirmando outro locutor, o candidato não é renderizado como corte Renan-first. Quando o áudio não decide, o candidato é enviado para revisão. Quando não existe medição de voz, o comportamento anterior é preservado.

A regra foi aplicada tanto ao smart cut quanto ao processo completo, com quantidade e motivo das exclusões registrados nos diagnósticos.

### Campaign Hub e mapeamento temporal

A contagem de seeds guiados pelo Campaign Hub recebe a duração medida do arquivo local, reduzindo o risco de interpretar timestamps absolutos de uma live como timestamps locais de um bloco baixado. O Chub continua sendo uma fonte de descoberta, contexto e evidência limitada; ele não aprova automaticamente um corte.

### Headlines e revisão

O estúdio de headlines passou a devolver `headline-fidelity-v1`. O relatório registra quantas sugestões foram aterradas lexicalmente na transcrição, quantas ficaram sem grounding conservador e quantas citações foram verificadas como literais. O relatório não confunde sobreposição lexical com comprovação factual; alegações sobre o mundo continuam exigindo revisão.

Os formatos funcionais mantidos neste ciclo continuam sendo 9:16 e 1:1/Alfinetei. Fake tweet permanece uma composição visual observada na fonte, não um terceiro formato de headline, conforme o contrato atual do projeto.

### Compatibilidade

A consulta de fingerprints aceita a identidade de intervalo, mas mantém fallback para integrações e testes antigos que expõem somente a assinatura de fonte. Nenhum ranking, peso principal, gate Renan-first existente ou endpoint de integração externa foi removido.

## Validação

| Verificação | Resultado |
|---|---:|
| `py_compile` dos módulos alterados | aprovado |
| `node --check static/js/app.js` | aprovado |
| `git diff --check` | aprovado |
| Testes focados de intervalo, contexto, Chub, ranking e headline | 109 aprovados |
| Suíte completa com modelo BlazeFace temporário | **563 aprovados, 4 ignorados** |
| Modelo BlazeFace | removido após a validação; não será versionado |

Durante a primeira suíte completa, cinco regressões de compatibilidade apareceram porque testes antigos substituíam `get_existing_clip_fingerprints` por uma função de um argumento. A compatibilidade foi corrigida com fallback explícito e a suíte completa foi executada novamente com sucesso.

## Resultado e limites

O Furia agora é mais auditável e mais seguro para reprocessar faixas. O sistema consegue explicar qual intervalo e qual transcript produziram um candidato, impedir que um conflito confirmado de voz seja renderizado, registrar por que um contexto exige revisão e apontar se a headline está lexicalmente fundamentada.

Este ciclo ainda não comprova, sozinho, um aumento de recall editorial em fontes reais. A melhoria de ranking precisa ser medida com lives longas, blocos Chub, cortes aprovados/rejeitados e comparação de bordas. Também não foi implementada neste ciclo a fase futura de acionamento remoto e pesquisa web.

## Retomada

A próxima IA deve primeiro ler este relatório, `CUTTING_PRECISION_PLAN_2026-08-21.md`, `CUTTING_AUDIT_2026-08-21.md` e `HANDOFF_SINCE_CLAUDE_2026-08-21.md`. A hipótese seguinte recomendada é usar a nova identidade e proveniência para criar um benchmark editorial por faixa, transcrição e formato, antes de alterar novamente pesos do ranking.
