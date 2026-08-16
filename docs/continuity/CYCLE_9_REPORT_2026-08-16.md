# Relatório do ciclo 9 — Prompt executor e Campaign Hub

## Identificação

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Versão planejada | 1.9 |
| Branch | `manus/rebuild-opus-parity` |
| Hipótese | Um prompt executor explícito e um benchmark read-only do Campaign Hub devem orientar futuras melhorias de precisão sem acoplar o MCP ao runtime nem expandir o escopo para edição geral. |
| Tipo da rodada | Documental/operacional; sem alteração em módulos de processamento |
| Estado | Validação automatizada aprovada; commit e push pendentes no momento deste registro |

## Contexto

A análise do checkout mostrou que o Furia Clips já usa snapshots agregados do Campaign Hub para priors fracos de hook e padrões visuais. O código não consome diretamente a camada mais rica do Acervo: blocos QA-gated, perguntas-gatilho, autossuficiência, necessidade de contexto, riscos, warnings, destaques, resumos e tópicos.

O novo contrato recomenda primeiro um benchmark temporal/editorial entre esses blocos e candidatos locais. O Campaign Hub continua sendo observação e calibração; não aprova automaticamente cortes nem substitui os gates locais.

## Alterações documentais

| Arquivo | Alteração |
| --- | --- |
| `VERSION` | Atualizado de `1.8` para `1.9`. |
| `docs/continuity/PROMPT_3_EXECUTOR_CHUB_PARITY.md` | Novo prompt copiável para futuras IAs executarem auditoria, benchmark, testes, desenvolvimento, versionamento e publicação. |
| `AGENTS.md` | Passa a apontar o prompt executor vigente e reforça que o MCP não deve ser chamado diretamente pelo runtime. |
| `docs/continuity/DECISIONS.md` | Adicionadas as decisões sobre benchmark rico do Campaign Hub e paridade profissional sem expansão indiscriminada de escopo. |
| `docs/continuity/NEXT_CYCLE.md` | Próxima hipótese passou a ser o benchmark Campaign Hub versus candidatos locais. |
| `docs/continuity/PROJECT_STATE.md` | Estado preparado para a release 1.9 e revisão ainda pendente. |
| `docs/continuity/CHANGELOG.md` | Entrada 1.9 adicionada. |
| `docs/continuity/CYCLE_9_REPORT_2026-08-16.md` | Este relatório. |

## Pesquisa externa

Foram consultadas páginas oficiais de OpusClip, Descript e Riverside. Os recursos aproveitáveis no núcleo do Furia são compreensão multimodal, seleção de highlights, busca por tema, foco por locutor, score multifatorial explicável, presets por formato, reframe com preservação de evidência e análise baseada em transcrição. Edição geral, captions, voice/avatars, branding complexo e publicação automática foram explicitamente mantidos fora da prioridade atual.

Referências: [OpusClip](https://www.opus.pro/), [OpusClip Virality Score](https://help.opus.pro/docs/article/virality-score), [Descript Video Editor](https://www.descript.com/tools/video-editor) e [Riverside Magic Clips](https://riverside.com/magic-clips).

## Validação desta etapa

`git diff --check` foi aprovado. A suíte completa passou com **306 testes**. O asset BlazeFace oficial foi baixado temporariamente fora do histórico e validado pelo SHA-256 documentado; ele não será incluído no commit.

## Não verificado nesta etapa

O benchmark ainda não foi implementado. Nenhuma melhoria editorial de seleção ou ranking pode ser declarada a partir desta rodada. A validação audiovisual não foi necessária porque os módulos de processamento não foram alterados.

## Próxima hipótese única

Comparar blocos QA-gated e transcrições reais do Campaign Hub com candidatos locais, medindo erro temporal, autossuficiência, pergunta–resposta, payoff, início abrupto, contexto e risco antes de alterar o seletor ou o ranker.

## Estado antes da publicação

O prompt executor foi escrito e apontado por `AGENTS.md` e `PROMPT_MESTRE.md`. A próxima rodada foi redefinida para o benchmark Campaign Hub versus candidatos locais. A versão 1.9 e as expectativas de identidade de runtime foram atualizadas; a suíte final permanece em 306 testes aprovados.
