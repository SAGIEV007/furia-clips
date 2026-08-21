# UX de Blocos Remotos e Downloads Seletivos
Data: 21/08/2026

## Visão Geral
O usuário pediu para implementar o "Norte" do projeto: a capacidade de o Furia Clips ler metadados e blocos diretamente de uma URL do YouTube sem precisar baixar o vídeo inteiro antes, e permitir que o usuário baixe seletivamente apenas os intervalos (cortes) que deseja, na melhor qualidade.

## Mudanças Feitas no Backend
1. `modules/acervo_library.py`: Adicionado `youtube_id_from_url` para extrair IDs de vídeos diretamente de URLs padrão do YouTube.
2. `modules/preanalysis_blocks.py`: A função `blocks_for_source` agora aceita `source_url`. Se a URL for fornecida, ela extrai o ID do YouTube e busca blocos do Acervo sem depender de um `video_path` local.
3. `modules/source_ingest.py`: Criada a função `download_public_video_interval` usando a opção `download_ranges` do `yt-dlp`. Ela permite baixar um trecho exato (`start_s` até `end_s`) usando o FFmpeg subjacente sem baixar o vídeo inteiro.
4. `app.py`: A rota `/api/editorial/blocks/export` e `/api/editorial/blocks/highlights/export` agora aceitam `source_url`. Se o arquivo local não existir, o backend dispara o download seletivo via `download_public_video_interval`.

## Mudanças Feitas no Frontend (`app.js` e `index.html`)
1. Os botões de exportar bloco (`[data-block-export]`) e destaque (`[data-highlight-export]`) agora aceitam `state.sourceUrl`.
2. A confirmação de exportação avisa o usuário quando a operação for um "Download remoto do YouTube na melhor qualidade".
3. Durante o download remoto, o ícone do botão muda para uma ampulheta para dar feedback visual.
4. Os textos dos estados vazios (`empty states`) dos blocos foram atualizados para sugerir colar um link do YouTube.
5. O botão `btnProbeSource` (Verificar link) foi renomeado para "Analisar blocos remotamente" e agora ele chama o `loadEditorialBlocks()` automaticamente após verificar a URL. Isso permite que o usuário veja todos os cortes possíveis da live antes de baixar qualquer megabyte.
6. A interface foi ajustada para suportar esses botões sem quebrar o layout, adicionando margens (`source-link-actions`).

## Conclusão
A diretriz de "Mídia e Download Remoto" foi completamente integrada ao Furia Clips. O usuário agora pode colar um link de uma live de 3 horas, ver todos os cortes já revisados pelo Acervo e baixar apenas o corte de 1 minuto em qualidade máxima, economizando tempo e banda.
