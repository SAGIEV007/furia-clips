# Relatório do ciclo 14 — Contrato Campaign Hub→cortes

**Data:** 2026-08-17
**Versão documental:** 2.4
**Branch:** `manus/rebuild-opus-parity`
**Commit de publicação:** `b18de83` — `docs: reorientar contrato Campaign Hub para cortes (2.4)`
**Natureza:** reorientação documental e operacional; a ponte funcional Chub→cortes ainda não foi implementada nesta rodada.

## 1. Hipótese e objetivo

A prioridade real do Furia Clips é gerar cortes do universo Renan Santos/MBL que sejam precisos, completos, autossuficientes, contextualizados e editorialmente úteis. A hipótese desta rodada é que o projeto precisa usar o Campaign Hub como contexto e calibração da seleção, e não apenas como fonte de blocos para inspeção ou benchmark.

A hipótese funcional registrada para a próxima implementação é:

> Se o Furia importar um lote autorizado de unidades do Campaign Hub, transformar cada bloco/highlight em seed semântica e temporal, alinhar a seed à fonte local e expandi-la até a menor janela completa que passe pelos gates de contexto e locutor, então o recall do benchmark b354 deve sair de `0/3` sem aumentar falsos positivos, atribuições erradas ou cortes truncados.

## 2. Evidência de estado atual

A release 2.2 possui memória local, sessão de blocos, benchmark persistente e exportação individual de highlights. No caso b354, sete candidatos locais cobriram `0/3` highlights QA-gated do Campaign Hub, com IoU médio `0.0`. O mapeamento temporal e os exports funcionaram; o contexto Chub ainda não gera propostas de janela contextualizadas.

A auditoria do código separou as camadas atuais:

| Camada | Estado observado |
| --- | --- |
| Adaptador/memória Campaign Hub | Importa snapshots autorizados e preserva blocos, highlights, riscos, proveniência e métricas para uso local. |
| Sessão de blocos | Lista, filtra, mostra e exporta intervalos/highlights já conhecidos; é superfície de diagnóstico e revisão. |
| Contexto/ranking | Usa sinais Chub de forma limitada e explicável, mas ainda não transforma contexto em seed, expansão ou proposta guiada. |
| Corte contextualizado | Ainda não implementado como fluxo integrado de ponta a ponta. |

A consulta autorizada ao Campaign Hub também confirmou a necessidade de separar assunto, locutor e evidência. No vídeo analisado, a transcrição é automática e exige conferência audiovisual; `turn` e `speakerChange` não constituem identidade definitiva e `renanSpeaking=false` não pode ser convertido em fala do Renan.

## 3. Alterações documentais

Foram atualizados:

- `docs/continuity/CHUB_INTEGRATION_CONTRACT.md`, novo contrato funcional do fluxo Chub→cortes.
- `docs/continuity/PROMPT_MESTRE_IA.md`, com o Campaign Hub como motor de contexto e calibração antes do score.
- `docs/continuity/START_HERE.md`, com a nova porta de entrada, fluxo de seeds e gates e papel limitado da sessão de blocos.
- `docs/continuity/PROJECT_STATE.md`, com o novo norte e a distinção entre fundação existente e ponte ainda ausente.
- `docs/continuity/NEXT_CYCLE.md`, com a hipótese e o procedimento de implementação funcional.
- `AGENTS.md` e `README.md`, para que uma IA que receba apenas o link do GitHub leia o contrato Chub→cortes e saiba que blocos não são o produto final.
- `docs/continuity/CHANGELOG.md` e `VERSION`, registrando a revisão documental 2.4.
- `tests/test_runtime_version.py`, alinhando a expectativa do teste à versão 2.4.

## 4. Contrato funcional definido

O fluxo-alvo é:

```text
fonte local ou URL pública
  → identidade e timeline canônica
  → contexto autorizado do Campaign Hub
  → alinhamento Chub↔fonte local
  → seeds editoriais
  → expansão até janela completa
  → gates de contexto, locutor, timing, transcrição, mídia e risco
  → proposta guiada separada de corte aprovado
  → revisão e renderização original
  → benchmark antes/depois e feedback persistido
```

O job normal continua offline-first e não chama MCP a cada corte. Uma ação de atualização ou o agente deve produzir um snapshot local sanitizado, versionado, paginado, hasheado e vinculado à fonte. O snapshot ausente deve ser declarado; não pode ser tratado silenciosamente como ausência de contexto.

## 5. Validação desta rodada

Esta rodada foi documental. Foram revisados o prompt mestre, o START_HERE, o estado vivo, a próxima hipótese, o adaptador Campaign Hub, a memória local, o contexto editorial, o ranker, a sessão de blocos, o frontend e a evidência autorizada de blocos/transcrição. Nenhum módulo de seleção, ranking, ingestão ou renderização foi alterado.

A suíte funcional completa foi executada com o asset BlazeFace oficial provisionado temporariamente e terminou com **327 testes aprovados**. A primeira execução sem esse asset falhou apenas por ausência ambiental do modelo; o arquivo foi baixado depois com SHA-256 conferido e removido antes do commit. Também passaram `compileall`, `node --check`, `git diff --check` e a verificação de arquivos proibidos. A mudança de versão exige que os testes de identidade do runtime esperem `2.4`; essa alteração não muda o comportamento do pipeline.

## 6. Limitações

A integração Campaign Hub→seeds→expansão→gates ainda não existe de ponta a ponta. A sessão de blocos pode continuar parecendo genérica ou sem ação útil quando o snapshot não está presente ou quando o fluxo não encontra o MP4 correspondente. O benchmark permanece em `0/3`; não há melhoria editorial medida nesta rodada.

Não foram implementados reframe, headlines, diarização robusta, reconhecimento de voz, editor estilo CapCut, publicação automática, música, voz, avatars, múltiplas câmeras ou download remoto por range.

## 7. Próxima rodada

Implementar uma única alteração principal: consumir um snapshot Chub autorizado no pipeline de geração guiada, mapear seeds para a timeline local, expandir a janela com transcrição e contexto e produzir propostas auditáveis antes do ranking. Reprocessar b354, comparar com os sete candidatos do baseline, renderizar uma amostra aprovada e medir recall, IoU, erro temporal, autossuficiência, locutor, payoff, riscos e qualidade audiovisual.

O sucesso será considerado confirmado apenas se o ganho for reproduzível no mesmo lote e não vier acompanhado de atribuição incorreta, perda de contexto ou falsos positivos adicionais.
