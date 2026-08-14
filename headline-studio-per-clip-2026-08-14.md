# Headline Studio por corte — 14/08/2026

## Objetivo

Cada candidato de corte agora pode abrir um **Estúdio do Corte** dentro do próprio card. O fluxo usa a transcrição daquele intervalo, permite corrigir o texto, aceita um minicontexto editorial e oferece seleção entre `9:16 central`, `1:1 Alfinetei`, `fake tweet` ou escolha automática.

O estúdio gera somente texto para a arte. Ele não produz SEO, hashtags, descrição de publicação ou promessa de viralização. As três famílias seguem os limites já definidos pelo projeto: headline central curta para 9:16, chamada superior e headline branca enxuta para 1:1, e rascunho de publicação para fake tweet com revisão de atribuição.

## Persistência

A análise aceita `clip_id` e recupera a transcrição persistida quando o editor não colar uma versão manual. A sugestão escolhida ou rejeitada é salva com `clip_id`, `editorial_key`, formato, texto, ação, trecho da transcrição e origem `clip_headline_studio`. Isso mantém a decisão de texto associada ao corte sem misturá-la com a decisão de aprovar ou rejeitar o vídeo.

As escolhas antigas sem `clip_id` continuam válidas e seguem calibrando apenas preferências agregadas de formato. O sistema não publica textos escolhidos no GitHub e não inclui banco local, vídeos, transcrições privadas ou chaves.

## Avaliação do caso enviado

O vídeo `RENAN SANTOS | BP NAS ELEIÇÕES` teve 2.630 segmentos manuais, 44 capítulos editoriais e 50 candidatos pergunta–resposta antes da seleção. O Gemini analisou 166 blocos e produziu 15 candidatos; 14 foram renderizados. O enquadramento foi mantido na proporção original porque não havia evidência visual suficiente de locutor único estável e o face tracking estava indisponível. Essa saída é conservadora e correta para revisão, embora indique uma oportunidade futura de análise visual mais forte.

A transcrição timestampada é útil para localizar cortes e gerar headlines, mas precisa de revisão em nomes próprios, entidades, números e termos jurídicos. O texto mistura intervenções dos entrevistadores com as de Renan e contém erros de reconhecimento como nomes deformados, repetições e hesitações. O novo estúdio, por isso, mostra a transcrição do intervalo para edição antes de gerar a arte e mantém alertas factuais ou jurídicos quando os sinais locais os identificam.

## Backup para avaliação futura

Para avaliar aprovações e rejeições, o arquivo mais importante é o SQLite persistente da instalação, junto com a transcrição original e os logs. Os logs enviados mostram chamadas `POST /api/clips/13/feedback` e `POST /api/clips/14/feedback` com HTTP 200, mas não carregam o corpo JSON; portanto, não permitem inferir quais ações foram executadas. Não é necessário enviar os vídeos para avaliar decisões textuais. Eles só são necessários para revisar enquadramento, áudio, sobreposição de locutores e qualidade visual.
