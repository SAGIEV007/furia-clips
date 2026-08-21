# Pesquisa técnica para precisão de cortes — 2026-08-21

## Entendimento temporal fino

O TemporalBench argumenta que vários benchmarks de vídeo são grosseiros demais ou podem ser resolvidos por uma única imagem/texto, sem provar entendimento temporal. O benchmark usa descrições humanas detalhadas, pares positivos/negativos com diferenças temporais finas e avaliações em vídeos curtos e longos. A lição para o Furia é que um corte não deve ser avaliado somente por tópico ou frame atraente: é preciso testar a sequência, a ordem das ações, a progressão da fala, a relação causa–consequência e a presença do momento correto.

A consequência prática é criar testes negativos difíceis: janela que contém o mesmo tema mas perde a pergunta; janela que mantém a frase viral mas elimina o antecedente; janela que inclui o começo mas termina antes do payoff; e janela que parece correta em um frame, mas atribui a ação ao locutor errado. Isso é mais informativo que apenas medir se o texto tem palavras do tema.

## Detecção de highlights multimodal

O trabalho WACV 2025 sobre detecção não supervisionada de highlights aprende com sinais de áudio e visuais e avalia em datasets de YouTube Highlights, TVSum e QVHighlights. A direção confirma que energia de áudio isolada não basta: sinais acústicos, visuais e temporais precisam ser combinados e avaliados contra janelas de referência. Para o Furia, energia, mudança de cena, reação, voz, texto e sinais do Campaign Hub devem ser candidatos/priors, não gates independentes.

A estratégia recomendada é um primeiro passe barato de recall, com áudio/transcrição/VAD/cenas, seguido de refinamento visual e contextual somente nos candidatos. O sistema deve guardar os sinais por intervalo para explicar por que um momento entrou no pool.

## Grounding temporal

A survey de Temporal Sentence Grounding trata o problema de localizar em vídeo não recortado o intervalo que corresponde a uma consulta textual. A aplicação direta ao Furia é converter cada seed Chub, pedido do usuário ou tema em uma consulta temporal e produzir intervalos candidatos com início/fim, confiança e evidência textual. O processo deve permitir mais de uma janela e usar a menor janela suficiente após uma fase de expansão contextual.

A avaliação deve separar localização e qualidade editorial: IoU/erro de borda mede se o intervalo encontrou a região certa, mas não garante que o corte seja autossuficiente. É necessário medir também início natural, contexto, payoff, locutor, evidência visual, headline e decisão humana.

## Transcrição com locutor e timestamps de palavra

A documentação da pyannote AI descreve uma orquestração de diarização com transcrição, oferecendo transcrição por palavra com timestamps e speaker attribution, além de turn-level transcription para falas completas. Ela também informa que identificação do locutor não é compatível com essa modalidade específica, que há dependência de modelos/serviço e que o resultado precisa ser obtido por polling ou webhook.

A implicação para o Furia é separar quatro conceitos: `speaker_turn` é quem parece falar naquele turno; `speaker_identity` é qual pessoa é; `speaker_presence` é quem aparece; e `speaker_mentioned` é quem é citado. O Chub pode fornecer evidência histórica de `renan_speaking`, mas uma integração forte deve medir e combinar essa evidência com diarização, voz, rosto, texto e posição no programa. Quando houver conflito, o candidato deve ir para revisão em vez de atribuição automática.

## Princípios de avaliação derivados

1. Medir recall temporal com IoU e erro de início/fim.
2. Medir precisão editorial com rótulos humanos separados para contexto, payoff, locutor, evidência e headline.
3. Criar pares de janelas quase idênticas para testar se o motor percebe diferenças temporais reais.
4. Avaliar separadamente cada família de fonte: live solo, entrevista, sabatina, discurso, debate, abertura, notícia, reação e tela/documento.
5. Fazer ablação: baseline local; + transcrição melhor; + Chub seeds; + Chub block evidence; + diarização; + visual; + feedback. Assim é possível saber o que realmente ajuda.
6. Manter avaliação temporal fora do ranking final: uma janela pode ter IoU alto e ainda ser ruim para publicação.

## Referências

[1]: https://arxiv.org/html/2410.10818v1 "TemporalBench: Benchmarking Fine-grained Temporal Understanding for Multimodal Video Models"
[2]: https://openaccess.thecvf.com/content/WACV2025/papers/Islam_Unsupervised_Video_Highlight_Detection_by_Learning_from_Audio_and_Visual_WACV_2025_paper.pdf "Unsupervised Video Highlight Detection by Learning from Audio and Visual Recurrence — WACV 2025"
[3]: https://mn.cs.tsinghua.edu.cn/xinwang/PDF/papers/2022_A%20Survey%20on%20Temporal%20Sentence%20Grounding%20in%20Videos.pdf "A Survey on Temporal Sentence Grounding in Videos"
[4]: https://docs.pyannote.ai/tutorials/speech-to-text-diarization "pyannoteAI — Speech-to-text diarization"

## Comparação com ferramentas profissionais

As páginas oficiais do OpusClip descrevem um fluxo com seleção de highlights, prompts em linguagem natural, análise de sinais de áudio/visual/sentimento, reframing com rastreamento, legendas, templates de marca, API e automação de publicação. A página de ajuda do próprio OpusClip separa o score em hook, flow, value e trend, além de relevância ao prompt. A lição para o Furia não é copiar o score de viralidade, mas decompor o resultado em fatores explicáveis e adicionar um score de adequação editorial ao Renan/MBL, sem confundir desempenho histórico com qualidade intrínseca.

A página oficial do Vizard destaca transcrição, identificação de highlights, recorte de locutores, reframing, layouts, captions, títulos, descrições, hashtags, publicação e colaboração. O requisito relevante é o fluxo de uma fonte para vários formatos e saídas, com revisão antes da publicação. O Furia deve fazer isso com presets específicos para 9:16, 1:1 e fake tweet, preservando composição e regras editoriais diferentes para cada formato.

A página oficial do Descript mostra a edição baseada em texto: o usuário edita a transcrição e o vídeo acompanha, com remoção de fillers/silêncios, colaboração, revisão, captions e exportação. Para o Furia, a ideia mais valiosa é um editor de decisão textual: corrigir a transcrição, marcar o começo/fim, excluir uma frase, pedir uma versão mais curta e gerar novamente o render sem perder a proveniência do corte original.

## Referências adicionais

[5]: https://www.opus.pro/ "OpusClip — ClipAnything, ReframeAnything, templates, API e automação"
[6]: https://help.opus.pro/docs/article/virality-score "OpusClip — Virality Score"
[7]: https://vizard.ai/tools/ai-clips-generator "Vizard — AI Clips Generator"
[8]: https://www.descript.com/tools/video-editor "Descript — text-based video editing"
