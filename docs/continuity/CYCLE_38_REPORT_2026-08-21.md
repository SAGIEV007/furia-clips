# Relatório do ciclo 38 — MCP/Chub e recuperação textual de seeds

**Data:** 2026-08-21
**Branch:** `claude/repo-access-commits-imgjmk`
**Versão local:** `6.22`
**Status:** implementação funcional publicada em `6dabc14`; fechamento documental em andamento.

## Objetivo e hipótese

O ciclo começou com uma pergunta concreta: a integração com o Campaign Hub/MCP já tinha recebido tudo que era viável e útil para calibrar os cortes? A resposta foi **não**. A 6.21 fechou a observabilidade, mas não criou uma consulta remota contínua, um sincronizador de memória ou uma recuperação robusta de seeds Chub quando timestamps de uma live original não coincidem com o MP4 local.

A hipótese única deste ciclo foi:

> Se uma seed temporal do Campaign Hub não coincidir com a timeline local, mas o texto do highlight tiver correspondência lexical conservadora na transcrição, o Furia poderá recuperar a unidade correta para revisão sem tratar timestamps incompatíveis como verdade.

## Pesquisa realizada

Foram auditados o adaptador local `modules/campaign_hub.py`, a memória `modules/campaign_hub_memory.py`, o guidance `modules/campaign_hub_guidance.py`, o seletor, o benchmark editorial e os contratos já documentados. A integração atual já importa snapshots autorizados, preserva proveniência, gera propostas guiadas e mantém o job normal offline-first; porém não chama MCP durante o corte e não deve passar a fazê-lo a cada candidato.

O MCP oficial foi estudado como arquitetura de **tools**, **resources** e prompts. A conclusão é que tools read-only são adequadas para buscar blocos, pauta, transcrição e estatísticas, enquanto resources versionados são uma boa representação conceitual para uma memória editorial com URI, paginação, cache, TTL, escopo e notificações opcionais. Segurança remota exige allowlist, escopos mínimos, verificação do servidor, timeout, fallback e proibição de token passthrough/URL arbitrária.

O Campaign Hub foi consultado apenas em modo de leitura. O Acervo mostrou fontes contínuas de lives, highlights, blocos com pergunta-gatilho, ranks de densidade/autossuficiência, riscos, tiers, proveniência e informação de locutor. A transcrição do vídeo `VLGrdyM_A7s` retornou uma janela de 98–140 segundos com frases temporizadas, `transcriptSource`, `tokenizerVersion`, `speakerChange`, `turn` e `audioCheckRanges`; o próprio servidor advertiu que legenda automática não prova identidade nem citação e exige conferência do áudio. A pauta e os outcomes foram analisados sem transformar desempenho em aprovação automática; no momento da consulta, outcomes reais de pauta estavam vazios, portanto não há base para ajustar peso de performance a partir deles.

As fontes oficiais consultadas são a documentação de arquitetura e introdução do MCP, a especificação de resources e as práticas de segurança/conexão remota:

- [MCP — Introduction](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro)
- [MCP — Architecture](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture)
- [MCP — Remote server connections](https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-remote-servers)
- [MCP — Resources specification](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)
- [MCP — Security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)

## Implementação

`modules/clip_selector.py` recebeu uma ancoragem textual conservadora para seeds Chub que não sobrepõem nenhuma frase local. O método procura janelas de até três frases, normaliza Unicode, remove palavras pouco informativas, calcula cobertura lexical e similaridade de sequência e só aceita o resultado quando a cobertura é pelo menos `0.55` e o score combinado é pelo menos `0.62`.

A ancoragem textual só ocorre depois de falhar o caminho temporal. Ela registra `alignment_method=text_anchor`, a cobertura, a similaridade, o score e até vinte palavras coincidentes. A proposta recebe `alignment_gate=review_required`, conserva os timestamps originais, não altera a identidade do locutor e não vira aprovação automática. Quando não existe correspondência suficiente, o comportamento anterior é preservado: a seed distante não é encaixada em uma frase aleatória.

A ficha de diagnóstico das propostas Chub também foi ampliada. Agora o histórico pode carregar, de forma limitada, seed, bloco, highlight, intervalo, método de alinhamento, evidência textual, resumo, pergunta-gatilho, tópicos, confiança, densidade, autossuficiência, tier, riscos, warnings, gates e estado de revisão. Nenhum desses campos inclui credenciais, cookies, mídia ou transcrição integral.

O desenho detalhado está em [`CYCLE_38_DESIGN_MCP_CHUB_2026-08-21.md`](CYCLE_38_DESIGN_MCP_CHUB_2026-08-21.md). A pesquisa completa está em [`RESEARCH_MCP_CHUB_2026-08-21.md`](RESEARCH_MCP_CHUB_2026-08-21.md).

## Regressões e validação

Foram adicionados testes que cobrem três comportamentos: uma seed distante sem correspondência textual continua sem proposta; uma seed com texto correspondente pode ser recuperada para revisão; e a ficha de diagnóstico preserva evidência explicável. Os testes antigos de mapeamento temporal, gates Renan-first, contexto e memória local continuam passando.

| Validação | Resultado |
| --- | ---: |
| Guidance, memória e benchmark focados | 34 aprovados |
| Testes manuais do seletor | 1 aprovado |
| Suíte completa com BlazeFace temporário | **576 aprovados, 4 ignorados** |
| `py_compile` do seletor e guidance | aprovado |
| `git diff --check` | aprovado |
| Asset BlazeFace após a suíte | removido |

A suíte completa não prova ainda ganho editorial em uma live real. Ela prova que o contrato novo é determinístico e não quebrou as regressões existentes. O benchmark real de recall com decisões humanas ainda é a validação necessária antes de qualquer alteração de pesos.

## O que o MCP pode fazer no futuro

O caminho de maior valor é um sincronizador separado do job. Ele deve chamar apenas operações permitidas, buscar dados paginados, construir um snapshot sanitizado, registrar cursor, versão, hash, conta, tier, frescor, TTL e contagens, instalar o arquivo de forma atômica e deixar o job seguinte usar a versão congelada. Um botão **Atualizar memória do Chub** é viável nesse desenho, mas não deve abrir uma conexão remota a cada candidato nem bloquear uma live por indisponibilidade do serviço.

A integração futura mais importante é recuperar janelas de transcrição sob demanda para resolver contexto, e não enviar a live inteira ao Gemini. O Furia deve continuar cortando com a transcrição local timestampada, usando o Chub como índice, evidência e referência editorial. Outcomes de aprovação/rejeição do próprio Furia devem entrar depois em um feedback estruturado e em comparações pairwise; métricas de posts publicados servem como prior de descoberta, nunca como aprovação automática.

## Limitações e decisões negativas

Não foi implementado neste ciclo um cliente remoto embutido no Furia, porque o contrato de autenticação do endpoint do Chub e a portabilidade para a instalação Windows do escritório ainda precisam ser definidos. Não foram armazenadas credenciais, cookies, snapshots reais ou mídias no Git. Não foi alterado peso de ranking, gate Renan-first, fallback de IA ou renderização.

A ancoragem textual pode recuperar uma frase semanticamente parecida em outro ponto da live. Por isso o limiar é conservador, o resultado é explicitamente revisável e o benchmark deve medir falsos alinhamentos. A correspondência textual também nunca prova que Renan fala; o gate de locutor continua independente.

## Próxima IA

1. Confirmar a branch e o estado limpo após o commit/publicação da 6.22.
2. Executar uma faixa curta pela interface e copiar `ui-diagnostic-v1`; verificar se ingestão, transcrição, contexto, ranking, renderização, fallback e cancelamento aparecem no diagnóstico.
3. Rodar o benchmark Chub em uma fonte longa com timeline incompatível e comparar baseline temporal versus `text_anchor`.
4. Medir recall, IoU, erro de borda, contexto, payoff, locutor e falsos alinhamentos separadamente.
5. Só depois desenhar e testar o sincronizador remoto read-only com snapshot local, se o contrato de autenticação portátil estiver definido.

## Arquivos alterados

- `VERSION`
- `modules/clip_selector.py`
- `tests/test_campaign_hub_guidance.py`
- `docs/continuity/RESEARCH_MCP_CHUB_2026-08-21.md`
- `docs/continuity/CYCLE_38_DESIGN_MCP_CHUB_2026-08-21.md`
- `docs/continuity/CYCLE_38_REPORT_2026-08-21.md`
- `docs/continuity/NEXT_CYCLE.md`
- `docs/continuity/PROJECT_STATE.md`
- `docs/continuity/HANDOFF_SINCE_CLAUDE_2026-08-21.md`
