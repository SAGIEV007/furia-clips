# Planejamento Completo - Furia Clips - Autonomia Total - Arena

**Branch:** arena/01a02c77-furia-clips
**Data:** 2026-08-22
**Status:** Etapa 1 em andamento
**Princípio:** Pesquisa extensa antes de cada mudança de etapa, referências reais, registro completo

## Visão Geral do Pedido

Você quer:
1. Download de vídeo configurado corretamente
2. Precisão e qualidade dos cortes de maneira criteriosa, experimentando todas as ferramentas relevantes (legenda, headlines)
3. Headline funcionando apenas com arquivo de legenda enviado
4. Qualidade dos cortes até ficar satisfeito e com resultados incríveis
5. Depois headlines até ficar satisfeito
6. Depois reestruturação visual completa (paleta Missão, UX, design)
7. Autonomia total, sem contrato antigo, pesquisa extensa a cada etapa

Você também pergunta se é possível treinar só com cortes do Instagram e como seria implementar reconhecimento de voz/rosto MBL, energia, discussão, etc.

## Etapa 1 - Download Robusto + Precisão de Cortes (FOCO ATUAL)

### Problema Atual Identificado:

**Download:**
- `modules/source_ingest.py` já é robusto (prefere áudio pt-BR, retries 3x, progress hooks, valida URL contra SSRF, bloqueia localhost/private IPs)
- Mas falha no sandbox por Cloudflare bloqueando yt-dlp: `TLS/SSL connection has been closed (EOF)` - mesmo problema do Chub MCP
- Fora do sandbox funciona. No sandbox precisa fallback para arquivo local (já existe `tests/fixtures/sample_av.mp4`)
- Formato preferido: `bv*[height<=1080]+ba[language^=pt]/bv*+ba/b` - correto para evitar dublagem espanhola

**Cortes:**
- `ClipSelector` já tem: costura por conversa, payoff extension, word timestamp refinement, scene boundary adjustment, deduplicação, fingerprint
- Mas precisa calibração: bordas ainda caem no meio da fala em alguns casos (NORTE 6.3 mediu 5/8 para 1/10 após fix)
- Energia já medida mas não usada para detectar discussão
- Voz cadastrada não decide nada (0 cortes com voz reconhecida)

**Legenda:**
- `subtitle_generator.py` gera ASS/SRT com karaoke word-by-word, escaping seguro
- `transcript_parser.py` já aceita Tactiq, SRT, VTT, timestamps inline

**Headline:**
- Funciona com apenas legenda, mas endpoint falhava por DB não inicializado (`no such table: clips`)
- Após `init_db()`, 42/42 testes passando
- Já tem fixes críticos: `PROTECTED_ENTITY_TOKENS`, `_terms_nearby()` para exigir proximidade local entre Brasil e claim

### Pesquisa Extensa - Como Ferramentas de Mercado Fazem:

**OpusClip ClipAnything:** multimodal visual+áudio+sentimento, Virality Score 0-99 (Hook/Flow/Value/Trend), Active Speaker Detection, ReframeAnything com easing para não jitterar, API job queue

**Vizard:** transcript-based + scene & speaker detection, cortes mais limpos que OpusClip, editor por texto (destaca palavras)

**CapCut long-to-short:** até 3h/10GB, highlight detection por visual/áudio/contexto, auto-reframe, 75+ línguas

**Pipeline comum:** Transcrição word-level → Moment detection LLM → Reframing CV face tracking → Captions ASS → Render FFmpeg

**Speaker diarization:** pyannote/speaker-diarization (HuggingFace, 100+ spaces), Resemblyzer d-vector, x-vector, VoxCeleb pipeline: YouTube → SyncNet active speaker → face recognition CNN para confirmar identidade

**Energy/discussion detection:** pyannote detecta overlap, pitch variability, VAD, energy windows. Discussão = turnos curtos + overlap alto + pitch sobe. "Coice" = pergunta + pausa + resposta com energia alta + payoff.

### O que vou implementar nesta Etapa 1 (com autonomia total):

#### 1.1 Download - Correção Criteriosa:
- [ ] Adicionar fallback para arquivo local quando yt-dlp falha por TLS (detectar EOF e sugerir upload local)
- [ ] Melhorar mensagem de erro: explicar que no sandbox Cloudflare bloqueia, mas local funciona
- [ ] Garantir `sourceDownloadDir` separado de `outputDir` (já corrigido na publish mas confirmar)
- [ ] Adicionar validação de áudio: rejeitar DASH sem áudio com mensagem clara (já existe)
- [ ] Teste: tentar baixar 1 vídeo real fora do sandbox, documentar resultado

#### 1.2 Precisão de Cortes - Calibração à Exaustão:
- [ ] Restaurar `modules/clip_selector.py` da Claude (mais completo) mantendo fixes da publish
- [ ] Auditar `_refine_clip_boundaries`: garantir que borda cai em costura de conversa, não no meio da fala
- [ ] Implementar detector de discussão: turnos < 5s + overlap + energia alta
- [ ] Implementar detector de "resposta/coice": Q&A completo com payoff, não só frase forte
- [ ] Medir energia por janela e usar no ranking (já existe mas aumentar peso)
- [ ] Teste com `sample_av.mp4` + transcrição manual: gerar 7 clips, validar bordas, medir IoU contra referência manual
- [ ] Experimentar todas as ferramentas em 1 teste: upload → transcrição → seleção → ranking → legenda ASS/SRT → headline → render

#### 1.3 Legenda + Headline apenas com legenda:
- [ ] Garantir `api_analyze_headline_studio` funciona apenas com `transcript` sem `clip_id` (já funciona após init_db)
- [ ] Criar teste manual: enviar apenas SRT e verificar se headline sai conforme
- [ ] Documentar padrões de headline do Renan: usar `data/editorial_priors.json` + tentar acessar Instagram via `image_search` ou pesquisa

#### 1.4 Benchmark:
- [ ] Criar `workspace/benchmark_etapa1/` com 1 vídeo longo real (se conseguir baixar) ou usar fixture
- [ ] Medir: time-to-first-candidate, IoU contra referência, erro de borda, taxa de cortes com locutor identificado
- [ ] Registrar antes/depois no `docs/CYCLE_43_REPORT_2026-08-22.md`

### Critério de Saída Etapa 1 (quando fico satisfeito):
- Download funciona local (fora sandbox) e tem fallback claro no sandbox
- Em 1 vídeo longo real, maioria dos cortes é aproveitável sem retrabalho de borda (critério NORTE)
- Legenda ASS/SRT sai com karaoke word-by-word correto
- Headline sai apenas com legenda enviada, ancorada na legenda, sem inferir Brasil ou primeira pessoa
- 750+ testes passando (menos ffmpeg)

### Etapa 2 - Headlines (após Etapa 1 satisfeita):

**Pesquisa extensa planejada:**
- Acessar perfis @renansantosmbl, @renansantosreserva no Instagram via `image_search` + `web_search` para memorizar padrões de headlines baseados nas legendas
- Baixar lives longas do Renan, transcrever, e verificar se headline gerada apenas com legenda é conforme
- Analisar `docs/headline-studio-editorial-model.md` e `docs/competitive-capabilities-research`

**O que vou fazer:**
- Expandir `TOPIC_RULES` com saúde, educação, humor, descontraído (já tem na publish)
- Melhorar `_extractive_sentences` para priorizar respostas completas sobre perguntas abertas
- Implementar `PROTECTED_ENTITY_TOKENS` e `_terms_nearby` mais rigoroso (já tem)
- Criar benchmark de headlines: para cada legenda real, comparar headline gerada vs headline publicada no Instagram
- Medir: headline editada vs reescrita (critério NORTE Etapa 2)

**Critério de saída:** Editor edita headline em vez de reescrever na maioria dos casos

### Etapa 3 - UX Visual Completa (após Etapa 2 satisfeita):

**Pesquisa extensa planejada:**
- Pesquisar sites mais incríveis e otimizados, dashboards dinâmicos, interativos, nível profissional
- Paleta de cores Partido Missão: buscar `web_search` "Partido Missão paleta cores identidade visual"
- Melhores práticas: Linear, Stripe Dashboard, Vercel, etc
- Referências: OpusClip, Vizard UI, CapCut

**O que vou fazer:**
- Reestruturação visual completa: paleta Missão (amarelo, preto, branco?), tokens em `static/css/furia-tokens.css`
- Dashboard dinâmico: cards de clips com score, confiança, gates Verde/Âmbar/Vermelho com motivo
- Timeline interativa com drag para ajustar borda, texto acompanhando
- Estado sempre visível (carregando, vazio, erro, sucesso)
- Acessibilidade: prefers-reduced-motion, foco teclado, contraste

**Critério de saída:** Existe pelo menos uma tela que editor mostraria para outra pessoa (NORTE 12.7)

## Sugestões do que mais pode ser implementado e como pedir:

### Sugestões técnicas (além do seu plano):

1. **Galeria MBL com reconhecimento facial e voz:**
   - Como pedir: "Quero que implemente reconhecimento de rosto e voz dos membros do MBL, cria galeria com fotos e áudios de referência"
   - Implementação: AdaFace + BlazeFace + Resemblyzer, linha do tempo de locutor antes da seleção

2. **Detector de contexto engraçado/descontraído com multimodal:**
   - Como pedir: "Quero que detecte momentos engraçados e descontraídos usando áudio (risada) + visual (sorriso) + texto"
   - Implementação: expandir família descontraído + audio cues + visual emotion

3. **Auto-framing inteligente por confiança:**
   - Como pedir: "Quero que enquadramento automático só use 9:16 quando tiver confiança alta, senão mantém 16:9"
   - Implementação: já está no NORTE como invariante, só calibrar

4. **Aprendizado com feedback do editor (como você quer memorizar padrões):**
   - Como pedir: "Quero que a ferramenta aprenda com meus likes/dislikes e com os Reels que já postei"
   - Implementação: `modules/editorial_learning_store.py` já existe na Claude, salvar decisões em `FuriaClipsData/`, hard-negative benchmark

5. **Download seletivo por blocos do Chub (Garimpo):**
   - Como pedir: "Quero baixar só um trecho específico de uma live longa, como no Garimpo"
   - Implementação: `source_interval.py` + `editorial_block_memory.py` da Claude, mapear timestamps absolutos para timeline local

6. **Medição de energia e discussão ao vivo:**
   - Como pedir: "Quero que detecte quando tem discussão acalorada e marque como highlight"
   - Implementação: energy windows + pitch variability + overlap detection

7. **Orquestração automática (Etapa 4):**
   - Como pedir: "Quero que quando live acaba, já gere cortes automaticamente sem abrir programa"
   - Implementação: job queue + webhook + n8n, mas só após Etapa 1 fechar de verdade (NORTE avisa)

### Como pedir pra mim (com autonomia total e sem pressa):

Você pode pedir de forma simples e direta, tipo:

- "Foca só na Etapa 1 até ficar incrível, não precisa me perguntar"
- "Quando terminar Etapa 1, vai pra Etapa 2 de headlines"
- "Pesquisa como o OpusClip faz X e implementa do melhor jeito"
- "Baixa 3 lives do Renan e usa pra calibrar, documenta tudo"
- "Atualiza o NORTE com essa ideia: [sua ideia]"
- "Quero que a ferramenta reconheça o Kim Kataguiri também"

Eu vou:
- Fazer pesquisa extensa antes de cada mudança de etapa (web_search depth 3 + docs)
- Buscar referências reais (sites, docs, benchmarks)
- Implementar menor mudança que testa hipótese
- Medir antes/depois com MP4 real e testes
- Documentar tudo em `docs/CYCLE_*_REPORT.md` e no NORTE quando pedir
- Commitar e pushar na arena

Cada etapa pode demorar horas, sem pressa, com liberdade criativa total como você disse.

## Status Atual:

- Branch arena criada e com sobriedade da Claude + funcionalidade da publish
- Download auditado: robusto mas bloqueado por Cloudflare no sandbox (funciona local)
- Testes: 750 passed, 7 failed só por ffmpeg
- Headline: 42/42 passando após init_db, funciona apenas com legenda
- Pronto para começar Etapa 1.1

Vou começar agora pela Etapa 1.1 e 1.2 com autonomia total.
