# Ciclo 11 — Primeira onda operacional Chub–Furia

**Data:** 17 de agosto de 2026  
**Projeto:** Furia Clips  
**Branch:** `manus/rebuild-opus-parity`  
**Baseline:** release 2.0, commit `0fdac3c`  
**Release candidata:** 2.1  

## Objetivo e hipótese

A hipótese desta rodada foi:

> Se o Furia mantiver uma memória local leve e versionada do Campaign Hub, filtrar blocos pela fonte correta, priorizar Renan sem ocultar outros oradores e exportar intervalos de um MP4 já disponível, o usuário terá uma fundação real para reproduzir o fluxo do Garimpo sem depender de consulta ao Chub durante cada corte.

A rodada não tentou resolver simultaneamente diarização, reconhecimento de voz, download remoto por range, formatos sociais ou editor pós-renderização.

## Baseline

O baseline era a release 2.0, documental e operacional. O Furia já recebia MP4, transcrevia com Whisper, gerava candidatos, ranqueava localmente e renderizava cortes 16:9, mas carregava somente um snapshot pequeno do Campaign Hub. O baseline do snapshot continha priors agregados de hooks; não continha a estrutura completa de blocos, destaques, perguntas, riscos e proveniência do Acervo.

O caso de validação foi o MP4 de aproximadamente 553,527 segundos, 1920×1080, H.264/AAC, correspondente ao bloco do vídeo `Primeiro ato de Campanha - Renan Santos Presidente`, YouTube ID `57nyfP9IDW4`.

## Dados reais usados

Foi consultada diretamente, em modo de leitura, a ferramenta autorizada de blocos do Campaign Hub para o vídeo `57nyfP9IDW4`. O retorno trouxe 64 blocos do vídeo correto. O bloco de referência `b3545938-e3a5-4287-82b1-5f7dcdc218c3` foi confirmado com:

| Campo | Valor |
| --- | --- |
| Título | Kim transforma a campanha de Renan em guerra e convoca 45 dias de mobilização |
| Intervalo absoluto | 6142,56–6692,0 s |
| Duração | 549,44 s |
| Possíveis cortes | 3 |
| Destaques QA-gated | 3 |
| `renanSpeaking` | `false` |
| Pergunta-gatilho | Como Kim apresenta a campanha de Renan e mobiliza os apoiadores para os 45 dias? |
| `needsContext` | `false` |
| `selfContainedRank` | 90 |
| Riscos | jurídico sensível, linguagem ofensiva e ataque pessoal |
| Proveniência | `owner`, vídeo do canal Renan Santos |

O valor de `renanSpeaking=false` foi preservado como informação editorial importante: o bloco trata da campanha de Renan, mas é falado por Kim. A integração não converte tema em identidade de locutor.

## Implementações

### Memória local

Foi criado `modules/campaign_hub_memory.py`, com validação de esquema, manifesto, hash, instalação atômica, preservação de coleções, fusão incremental e fallback compatível com `data/editorial_priors.json`. A memória é gravada fora do checkout, não contém mídia bruta e continua disponível quando o Campaign Hub ou a internet não estão acessíveis.

Foi criado `scripts/convert_chub_blocks_export.py` para converter um retorno autorizado do Acervo em export leve. Também foi criado `scripts/update_campaign_hub_memory.py` para instalar ou mesclar esse export sem depender do Manus durante o uso diário.

O export real do vídeo correto instalou 64 blocos, 140 destaques e 2.009 frases na memória local. O arquivo de exportação e a base local não foram adicionados ao GitHub.

### Blocos

Foi criado `modules/editorial_block_memory.py`, com leitura de blocos, busca textual, filtragem por `video_id`, filtragem por YouTube ID/fonte e prioridade Renan-first. A prioridade altera a ordem, mas não oculta Kim, Vinicius, apoiadores ou outros oradores; isso é necessário em eventos complexos.

Foram adicionadas rotas para listar e abrir blocos. O painel visual foi inserido entre Fonte e Refinamento e apresenta intervalo, duração, título, resumo, pergunta-gatilho, locutor provável, quantidade de destaques, percentil de autossuficiência, riscos, tier de confiança e fonte.

### Exportação seletiva local

A rota `/api/editorial/blocks/export` agora exporta um intervalo de uma fonte local já disponível. Ela valida caminho, início, fim, duração e saída. Quando recebe timestamps absolutos do vídeo longo, mas a fonte local tem duração compatível com o bloco baixado, converte a timeline para `0–duração_do_bloco` e informa `timeline_mapping=downloaded_block_timeline`.

No caso b354, o intervalo absoluto `6142,56–6692,0` foi mapeado para `0–549,44` no MP4 local e renderizado pela aplicação real. O arquivo final foi validado com FFprobe:

| Campo | Resultado |
| --- | --- |
| Duração | 549,448900 s |
| Vídeo | H.264, 1920×1080, 30000/1001 fps |
| Áudio | AAC |
| Aspecto | 16:9 original |

### Ranking

`modules/campaign_hub.py` agora calcula `block_evidence` usando sobreposição temporal e, como fallback fraco, interseção textual. `modules/editorial_ranker.py` registra essa evidência e aplica um ajuste pequeno, explicável e limitado. O sinal de bloco não é gate, não prova identidade, não substitui contexto e não pode aprovar automaticamente um candidato.

### UX

A primeira camada visual passou a destacar memória local, status offline, atualização manual, fonte selecionada e a etapa de Blocos. A busca do painel filtra o vídeo correto quando o nome do MP4 contém um YouTube ID conhecido. A interface deixa claro que “Mostrar falas do Renan primeiro” não significa esconder outros oradores.

A inspeção visual mostrou que o UX ficou mais informativo, mas a tela continua longa e a sidebar ainda possui muitas configurações. Essa simplificação foi deliberadamente deixada para uma onda própria, porque remover handlers sem auditoria poderia causar regressões.

## Validação

A validação final executou:

- `node --check static/js/app.js`;
- `python -m compileall -q app.py modules scripts tests`;
- suíte completa com **322 testes aprovados**;
- teste real da API com 64 blocos do vídeo `57nyfP9IDW4`;
- busca e confirmação do bloco b354;
- exportação real do MP4 de bloco;
- FFprobe do arquivo exportado;
- inspeção visual da tela de Blocos no navegador Sandbox.

Os testes focados da memória, blocos, ranking e endpoints passaram com 42 casos. O teste de exportação também cobre fonte incompatível, limites inválidos e mapeamento de timeline de MP4 baixado.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | A memória local aceita dados ricos e funciona sem consulta ao Chub no corte. |
| Confirmado | O Furia lista 64 blocos reais do vídeo correto e mantém proveniência. |
| Confirmado | Renan-first pode ordenar sem eliminar falas de terceiros. |
| Confirmado | O b354 real pode ser exportado de um MP4 local com mapeamento temporal seguro. |
| Corrigido | O problema de aplicar timestamps absolutos a um MP4 que começa em zero. |
| Corrigido | O risco de misturar blocos de vídeos diferentes na lista visual. |
| Limitado | A evidência de bloco já chega ao ranking, mas como tie-breaker pequeno. |
| Não implementado | Download remoto seletivo por range para cada provedor. |
| Não implementado | Exportação de cada destaque individual como ação própria. |
| Não verificado | A arquitetura interna do Garimpo e se ele consulta o Chub em tempo real. |
| Bloqueado | Ingestão confiável do YouTube neste ambiente quando o yt-dlp encontra anti-bot. |

## Limitações e próxima hipótese

Esta rodada não implementou diarização robusta, reconhecimento de voz do Renan, benchmark persistente de recall/IoU, highlight export individual ou download remoto seletivo. Também não removeu definitivamente a sidebar extensa nem a aba de configurações secundárias.

A única próxima hipótese recomendada é:

> Se o Furia persistir um benchmark temporal/editorial entre candidatos locais e os 3 destaques do b354, e permitir exportar cada destaque com mapeamento de timeline, será possível medir recall e precisão antes de aumentar a influência do Campaign Hub no ranking.

A próxima rodada deve criar o benchmark persistente, mapear highlights para MP4 local, testar exportação de highlight e somente depois investigar range remoto. Não deve misturar diarização, reframe, headlines ou editor pós-renderização nesta hipótese.

## Segurança e privacidade

Nenhum MP4, banco local, cookie, token ou chave Gemini foi enviado ao GitHub. A memória rica e os exports ficam fora do checkout. O código publicado contém apenas adaptadores, contratos, testes e scripts para dados autorizados.
