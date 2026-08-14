# Política de formato visual e preservação de composição

## Objetivo

O Furia Clips precisa distinguir um monólogo com uma face estável de uma entrevista, um react com evidência externa, um split-screen, uma peça institucional ou uma convocação de campanha. A classificação orienta a revisão e o enquadramento; ela **não é uma previsão de viralidade, não comprova fatos e não substitui a decisão editorial humana**.

## Evidência utilizada

A política foi refinada a partir de uma amostra verificável das grades autenticadas dos perfis `@renansantosmbl` e `@renansantosreserva`, incluindo contagens de visualizações observadas na interface e inspeção visual de Reels de maior alcance. A amostra mostrou talking heads com texto amarelo, entrevistas e podcasts com múltiplos interlocutores, reacts em split-screen, cards e telas externas, peças institucionais com pouca fala, campanhas com assinatura e CTA, além de testemunhais com objeto ou material impresso. A contagem de views é armazenada como snapshot com data; não é tratada como retenção, compartilhamento ou causalidade.

## Famílias e política de reframe

| Família | Sinal principal | Política padrão |
| --- | --- | --- |
| `talking_head` | Uma face estável e fala contínua | Reframe 9:16 somente se a confiança facial for suficiente |
| `selfie_proximo` | Uma face em close com gestualidade | Reframe conservador, preservando olhos, boca, mãos e headline |
| `entrevista` | Pergunta, resposta ou mais de uma face | Preservar composição; manter a pergunta quando ela for necessária |
| `podcast` | Microfone, interlocutores e cortes de reação | Preservar quadro amplo ou usar active speaker seguro |
| `react` | Reação ligada a notícia, tela, CCTV ou fala externa | Manter evidência e reação no mesmo arco visual |
| `split_screen` | Duas fontes ou áreas simultâneas | Preservar os dois lados e todo o texto |
| `evidencia_externa` | Documento, tela, card, imagem ou ocorrência externa | Preservar a evidência e a transição para a interpretação |
| `b_roll_argumentativo` | B-roll intercalado a uma fala âncora | Pausar tracking durante o insert e retornar após validação |
| `palco` | Microfone, plateia e gestos amplos | Preservar mãos, microfone e relação com a plateia |
| `institucional` | Cartela, evento, assinatura ou narrativa visual | Preservar margens, identidade e proporção original |
| `campanha` | Símbolos, slogan, CTA e assinatura política | Tratar como portfólio de campanha; proteger a peça integral |
| `testemunhal`/`unboxing` | Emoção seguida de objeto, livro ou material | Preservar rosto, mãos e prova material |
| `desconhecido` | Evidência insuficiente | Preservar composição e marcar revisão |

## Implementação

O novo módulo `modules/editorial_format.py` privilegia os campos estruturados `visual_format`, `format_family`, `layout_family` e `source_family`. Depois considera split-screen, evidência externa, institucional, campanha, entrevista, podcast, palco, testemunho, número de faces e confiança de locutor. Se nenhum sinal for suficiente, retorna `desconhecido` com baixa confiança e política conservadora.

O `EditorialRanker` expõe no resultado `visual_format`, `visual_format_confidence`, `visual_format_reason`, `reframe_policy` e `preserve_composition`. Esses metadados também entram em `review_flags`, mas **não alteram a fórmula principal do score nesta rodada**. Assim, um formato visual não recebe pontuação artificial por parecer viral; ele apenas direciona o enquadramento e a revisão.

O portfólio diário passa a registrar `daily_portfolio_format` e `format_counts`. Essa telemetria permite verificar se uma seleção de 39–50 cortes ficou concentrada em talking heads, reacts, entrevistas ou campanhas sem transformar diversidade visual em quota rígida.

## Limitações e revisão

Texto sozinho não é evidência suficiente para confirmar um formato visual. As heurísticas lexicais só desempatarão sinais estruturados; sem metadados de visão, o módulo permanece conservador. A classificação também não valida acusações, números, alegações jurídicas ou captions. Esses casos continuam sujeitos aos flags de revisão factual e jurídica já existentes.

## Extensão baseada na janela pública de 14/08/2026

A análise incremental dos dois perfis mostrou três sinais visuais que merecem rotas explícitas no classificador, sem alterar o score editorial por aparência.

| Família | Evidência mínima | Política de enquadramento |
| --- | --- | --- |
| `text_panel` | Painel branco, amarelo ou vermelho com headline incorporada e fala/imagem em outro bloco | Preservar o painel e o conteúdo inferior; não recortar apenas a face |
| `fake_tweet` | Publicação social, comentário de seguidor ou recorte de post usado como evidência/reação | Manter post, reação e relação de resposta no mesmo corte |
| `visual_meme` | Arte composta, montagem ou imagem visual usada como punchline/evidência | Preservar a composição inteira; reframe somente após confirmação visual forte |

Essas famílias foram adicionadas de forma determinística a `modules/editorial_format.py`, recebem `preservar_composicao` e aparecem com rótulos explicáveis no HUD. A decisão continua dependente de campos estruturados do pipeline; texto sozinho não inventa um formato audiovisual. A suíte passou de 165 para 168 testes aprovados após a inclusão das regressões.

Os casos observados no perfil reserva também reforçam uma regra de produto: a ausência do rosto de Renan não elimina um candidato quando a tese é sustentada por footage externo, post social, palco, entrevistado ou arte. O sistema deve reduzir a confiança do reframe, preservar a composição e encaminhar a revisão humana quando a fala e a evidência visual precisarem permanecer juntas.

## Referências

A base editorial consolidada e o catálogo incremental estão em [`instagram-mbl-catalog-analysis.md`](instagram-mbl-catalog-analysis.md). A auditoria autenticada do Criadores/Missão está em [`criadores-auditoria-2026-08-14.md`](criadores-auditoria-2026-08-14.md). A política de enquadramento anterior está em [`layout-planner-editorial-policy-2026-08-14.md`](layout-planner-editorial-policy-2026-08-14.md).
