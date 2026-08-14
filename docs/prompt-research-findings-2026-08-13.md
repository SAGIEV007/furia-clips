# Pesquisa de referência para o prompt profissional

## Orientação oficial do Manus

A orientação oficial do skill de backup informa que a mudança de agosto de 2026 decorre do retorno do Manus à operação independente e do cumprimento de requisitos regulatórios específicos; não deve ser descrita como vazamento ou incidente de segurança. A notificação recebida por e-mail e dentro do aplicativo é a fonte de verdade para saber se uma conta específica é afetada.

Para contas afetadas, a janela indicada é: backup até 23 de agosto de 2026 às 7:59 SGT; período de exclusão/indisponibilidade de 23 de agosto às 8:00 SGT até 25 de agosto às 7:59 SGT; restauração a partir de 25 de agosto às 8:00 SGT. O backup de tarefas é uma fotografia pontual e não é automático. Usuários Type A/B precisam do Task Data Backup; Type C precisam primeiro do Account Info Backup e depois do Task Data Backup. A restauração deve ser feita uma única vez e conectores de terceiros precisam ser reativados manualmente.

Fontes oficiais:
- https://manus.im/blog/a-note-to-our-users
- https://help.manus.im/en/articles/16147831-service-change-overview-what-s-happening-and-am-i-affected
- https://help.manus.im/en/articles/16147892-service-change-overview-how-to-back-up-your-data
- https://help.manus.im/en/articles/16147895-service-change-overview-how-to-restore-your-data
- https://manus.im/backup

## Benchmark de ferramentas

### OpusClip
A página oficial descreve dois componentes diretamente relevantes: `ClipAnything`, que tenta trabalhar com múltiplos gêneros, incluindo entrevistas, e `ReframeAnything`, que redimensiona para plataformas e mantém sujeitos em movimento centrados com rastreamento de objetos. A pesquisa também identificou a necessidade de separar seleção de highlights do reframe: encontrar um trecho viral não é o mesmo que decidir como compor a imagem.

Fonte: https://www.opus.pro/

### Vizard
A página oficial de AI Reframe descreve detecção multimodal de faces e objetos, dynamic frame tracking, múltiplas proporções (9:16, 1:1 e 4:5), priorização de face e locutor, ajuste manual posterior e batch processing. O requisito mais importante para o prompt é manter uma etapa de revisão/ajuste manual, em vez de considerar o primeiro crop automático definitivo.

Fonte: https://vizard.ai/tools/ai-reframe

### Klap
A página oficial do AI Video Clipping Tool descreve importação em lote, clips ranqueados por Virality Score, reframe orientado ao active speaker/saliência, brand kits, API, webhooks, processamento em escala e tratamento de layouts multi-pessoa. Para o Furia Clips, isso sugere um pipeline com fila, ranking explicável, metadados de cada clip e uma fase de revisão, mesmo que a implementação permaneça local.

Fonte: https://klap.app/tools/ai-video-clipping-tool

### LumiClip
A página oficial de active-speaker reframing descreve uma abordagem mais próxima da necessidade do Furia Clips: usar sinais de áudio e visual para planejar o layout por momento, alternar entre single-speaker, split e picture-in-picture, acompanhar trocas de locutor e permitir preview de cada transição, sobreposição e área segura. Isso reforça que o reframe profissional não é apenas um crop fixo no centro; é uma composição temporal que pode mudar durante o clip.

Fonte: https://lumiclip.ai/ai-active-speaker-video-reframing

## Requisitos derivados para o prompt

O prompt deve exigir: análise completa antes do corte; transcrição com timestamps; mapa de candidatos com início, fim, título, tese, pergunta, resposta, gancho, conclusão e justificativa; ranking por qualidade e potencial viral; exportação dos candidatos mesmo quando não forem escolhidos; decisão explícita entre 16:9, 1:1, 4:5 e 9:16; active-speaker com áudio + visão; split/PIP ou 16:9 quando houver múltiplos locutores ou ambiguidade; preview/revisão por clip; e comparação de desempenho com as páginas do Renan Santos e com referências políticas virais.
