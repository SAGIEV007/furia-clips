# Comparação NORTE.md - Claude vs Publish (mais recente)

**Data:** 2026-08-22
**Pergunta do usuário:** Tem diferença grande entre o arquivo norte dos dois repositórios além das ideias?

## Resposta curta: SIM, diferença é ENORME

O `NORTE.md` **não existe** na branch mais recente `publish-context-only`. Foi completamente removido.

| Aspecto | Claude (central) | Publish (mais recente) |
|---------|------------------|------------------------|
| NORTE.md | 953 linhas, 48KB, existe | **NÃO EXISTE** |
| AGENTS.md | 56 linhas, existe | **NÃO EXISTE** |
| VERSION | 6.26 | não existe (hardcoded "rebuild-opus-parity") |
| docs/continuity/ | 95 arquivos, START_HERE, PROJECT_STATE, CHUB_CONTRACT | **NÃO EXISTE** |
| README | 17KB com instruções de continuidade | 16KB simplificado |
| app.py | 5218 linhas | 4577 linhas (-641) |
| modules/ | 55 modules | 43 modules (-12) |
| tests/ | 94 arquivos | 61 arquivos (-33) |

## O que a publish tem no lugar?

A publish colocou as ideias em dois arquivos diferentes:

1. **docs/conversation-summary.md** - 45 seções numeradas (24 a 45 são só desta rodada)
   - Foco 100% em Headline Studio: claim visível, atribuição de locutor, formato preservado, fake tweet separado, selo contextual, proteção contra entidades inventadas, proximidade entre entidade e tese

2. **docs/changelog-2026-08-22.md** - 600+ linhas só desta rodada
   - Foco em robustez editorial, transcrições persistentes, jobs, cancelamento, interface

## O NORTE da Claude (que não existe na publish) contém:

- **Índice completo:** O que a ferramenta é, 4 etapas, autonomia, invariantes editoriais, régua de medição, como trabalhar, o que só editor pode fazer, como Furia aprende, headline, onde conhecimento mora, etapa 4 desenhada, design, blocos úteis, pedir corte por intenção, onde estamos

- **Conceitos que não existem na publish:**
  - "Um cortador especialista em Renan Santos, não genérico"
  - "Meta: 10→20-30 cortes/dia sem perder credibilidade"
  - "Precisão sobre quantidade é identidade, não limitação"
  - "4 etapas não se pula"
  - "Portões antes do score"
  - "Áudio é verdade para citação, legenda é navegação"
  - "Não atribuir fala por palpite - 'não sei' é resposta legítima"
  - "Contar teste não é medir - fixture tem que vir da produção"
  - "Nenhum ciclo fecha sem exportar MP4 de verdade"
  - "Autonomia total, perguntar só em 3 casos"

- **Seção 9 - A headline:** Explica que headline é arte, não SEO, e toda a filosofia de grounding que a publish implementou mas sem o porquê

## Conclusão

Você pediu para colocar algumas ideias na mais recente, e foi feito - mas **muita coisa foi removida além de adicionar ideias**:

**Removido na publish:**
- Toda a filosofia e direção (NORTE.md)
- Instruções para IAs (AGENTS.md)
- Continuidade operacional (docs/continuity/ com 95 arquivos)
- 12 modules: acervo_library, campaign_hub_guidance, campaign_hub_memory, caption_lexicon, editorial_benchmark, editorial_block_memory, headline_copy, headline_quote, interview_turns, non_content_detector, preanalysis_blocks, source_boundary, source_interval, source_reading, speaker_id, topic_segmenter
- 641 linhas de app.py (observabilidade, eventos estruturados, diagnóstico copiável)
- Versionamento correto

**Adicionado na publish:**
- Fixes excelentes de headline grounding: `PROTECTED_ENTITY_TOKENS`, `NUMBER_WORD_ALIASES`, `_terms_nearby()` para exigir proximidade local entre Brasil e claim, proteção contra primeira pessoa inventada, eyebrow seguro
- 42 testes só para proximidade de entidade

## O que esta branch Arena faz

Mantém **funcionalidade da publish** (app.py 4577 linhas + headline_studio 788 linhas com fixes de proximidade) + **sobriedade da Claude** (NORTE.md 953 linhas + AGENTS.md + VERSION + docs/continuity/ 95 arquivos)

Ou seja: programa continua funcional como está atualmente, mas com documentação e direção que impedem regressão de qualidade.

Se você quiser "apenas copiar tudo do mais recente", perderia a sobriedade. O ideal é manter como está agora nesta arena: funcional + sóbrio.
