# Base editorial de referência — esquema de anotação

A base não será tratada como “dados já treinados” no sentido de um modelo proprietário pronto. Ela será um **catálogo anotado de exemplos reais**, útil para criar regras, testes, prompts, ranking e, posteriormente, um modelo supervisionado com validação humana. Cada anotação deve manter a fonte pública, a data de coleta e o grau de certeza.

## Registro por vídeo

| Campo | Descrição |
|---|---|
| `profile` | Perfil de origem: `renansantosreserva` ou `renansantosmbl`. |
| `reel_url` e `reel_id` | URL e identificador público do Reel. |
| `published_at` | Data/hora exibida pela plataforma, quando disponível. |
| `duration_seconds` | Duração medida do vídeo. |
| `source_aspect_ratio` | Proporção da fonte e resolução observada. |
| `content_family` | Política, proposta, crítica, confronto, reação, bastidor, conversa, humor, mobilização ou outro. |
| `source_context` | Entrevista, live, rua, pronunciamento, estúdio, evento, compilado, meme, repost ou desconhecido. |
| `speaker_focus` | Renan, entrevistador, convidado, grupo, narração, B-roll ou misto. |
| `speaker_confidence` | Confiança da identificação do foco. |

## Anotação de edição

Cada vídeo deve registrar os pontos de corte observáveis, não apenas uma avaliação geral. Os intervalos podem ser anotados como `intro`, `hook`, `setup`, `question`, `answer`, `escalation`, `payoff`, `reaction`, `outro` e `transition`.

| Campo | O que observar |
|---|---|
| `edit_intervals` | Início/fim de cada bloco, texto/fala, função editorial e motivo da transição. |
| `opening_type` | Começa por tese, pergunta, reação, frase no meio, imagem de apoio, texto ou contexto. |
| `closure_type` | Conclusão forte, chamada, frase de efeito, resposta completa, corte abrupto ou loop. |
| `question_answer_structure` | Ausente, pergunta+resposta completa, resposta autossuficiente, pergunta sem resposta ou múltiplos turnos. |
| `camera_pattern` | Plano único, troca de câmera, split-screen, close, reação, B-roll, PIP ou composição híbrida. |
| `reframe_behavior` | Fixo, acompanha locutor, alterna locutores, split/PIP, original ou indeterminado. |
| `aspect_output` | 9:16, 1:1, 4:5, 16:9 ou composição híbrida. |
| `visual_safe_area` | Posição do rosto, margem para legenda, GC da emissora, elementos cortados e áreas ocupadas. |
| `caption_style` | Tipo de legenda, tamanho, posição, cor, palavra destacada, velocidade e legibilidade. |
| `music_audio` | Música, volume relativo, efeitos, ruído, pausas, risos, sobreposição e mixagem. |
| `pacing` | Densidade de cortes, duração média dos planos, pausas preservadas e aceleração. |

## Anotação editorial

O objetivo é explicar por que o vídeo funciona ou não funciona, sem confundir desempenho observado com preferência pessoal.

| Campo | Descrição |
|---|---|
| `thesis` | Ideia principal que o vídeo comunica. |
| `hook_seconds` | Quantos segundos até a tese ou conflito ficar claro. |
| `context_sufficiency` | Se o vídeo se sustenta sem assistir ao conteúdo original. |
| `completion` | Se a ideia chega ao payoff/conclusão. |
| `clarity` | Clareza da fala, da imagem e da edição. |
| `controversy_or_tension` | Conflito, surpresa, discordância ou tensão argumentativa. |
| `specificity` | Nomes, fatos, exemplos, números ou proposta concreta. |
| `emotional_signal` | Indignação, humor, surpresa, emoção, autoridade, urgência ou calma. |
| `manual_editability` | Se o vídeo oferece uma minutagem reaproveitável mesmo quando o output automático falharia. |
| `quality_label` | `gold`, `good`, `needs_edit`, `weak` ou `unknown`. |
| `evidence_notes` | Observações factuais e timestamps que justificam a anotação. |

## Desempenho e evidência

Quando métricas públicas estiverem visíveis, registrar visualizações, curtidas, comentários, compartilhamentos, data e fonte da métrica. Quando não estiverem disponíveis, usar `not_observed`, nunca estimar. Separar “padrão recorrente” de “hipótese editorial” e “correlação com desempenho”.

## Uso no Furia Clips

A base deve alimentar cinco componentes independentes: perfil editorial do Renan/MBL; exemplos para o prompt do Gemini; regras e gates do seletor; conjunto de testes de regressão; e feedback supervisionado do editor. Não deve copiar automaticamente títulos, legendas ou identidade de terceiros. O conteúdo público será usado para aprender **estruturas e decisões de edição**, não para reproduzir material ou alegar treinamento de um modelo proprietário.

## Critério de validade

Um padrão só pode ser promovido a regra automática quando aparecer em múltiplos exemplos independentes ou receber confirmação do editor. Cada regra deve manter exemplos positivos, contraexemplos, confiança e data da última revisão. O sistema deve continuar funcionando quando a plataforma mudar a interface ou quando um Reel não puder ser acessado.
