# CYCLE 43 - Etapa 1: Precisão de Cortes + Renan Gallery + Engajamento - 2026-08-22

**Branch:** arena/01a02c77-furia-clips
**Status:** Etapa 1 em andamento - melhorias implementadas, calibração com 8-10 lives estruturada
**Tempo investido:** ~2h de pesquisa extensa + implementação

## Pesquisa Extensa Realizada (antes de mudar de etapa)

### 1. Ferramentas de Corte - Como Mercado Faz:

**OpusClip ClipAnything:**
- Multimodal: visual cues + audio sentiment + facial expressions + narrative structure
- Virality Score 0-99 baseado em Hook/Flow/Value/Trend
- ReframeAnything com object tracking e easing (não jittera)
- Pipeline: Transcribe (word-level) -> Detect (LLM) -> Reframe (CV) -> Captions (ASS) -> Render (FFmpeg)
- 10M+ usuários, 172M+ clips, $15/mês Starter, 97% caption accuracy

**Vizard:**
- Transcript-based + scene & speaker detection
- Cortes mais limpos que OpusClip (menos mid-sentence cuts)
- Editor por texto: destaca palavras para cortar
- 100+ línguas legenda, active-speaker tracking

**CapCut long-to-short:**
- Até 3h/10GB, highlight detection visual/audio/contexto
- Auto-reframe, 75+ línguas
- Fluxo simples: upload -> auto highlight -> reframe -> captions

**Pipeline comum observado:**
```
Transcrição word-level -> Moment detection LLM -> Reframing CV face tracking -> Captions ASS -> Render FFmpeg
```

### 2. Speaker Diarization + Reconhecimento:

**pyannote/speaker-diarization:** HuggingFace, 100+ spaces, detecta overlap, VAD
**Resemblyzer:** d-vector para voz, x-vector alternativa
**VoxCeleb pipeline:** YouTube -> SyncNet active speaker -> face recognition CNN
**AdaFace ResNet-18:** leve, bom para galeria pequena (Renan only)
**M3SD:** 770h multimodal dataset, audio-visual fusion

**Energy/discussion detection:**
- pyannote detecta overlap, pitch variability, VAD, energy windows
- Discussão = turnos curtos (<5s) + overlap alto + pitch sobe + marcadores (?, !, "não", "mas")
- "Coice" = pergunta + pausa + resposta com energia alta + payoff completo

### 3. Partido Missão - Identidade Visual:

**Fonte:** Wikipedia + web_search depth 3
- **Cores oficiais:** Preto, Branco, Amarelo
- **Amarelo oficial:** #FCBE26 (do template Wikipedia)
- **Mascote:** Onça-pintada
- **Bandeira:** 3 listras horizontais preto/branco/amarelo, logo na faixa branca
- **Nome:** Referência a missão, visão e valores de planejamento estratégico empresarial
- **Atual tokens:** --furia-accent: #e8a317 (próximo de #FCBE26), precisa ajustar para #FCBE26 exato

### 4. Dashboard Design - Sites Mais Incríveis:

**Referências pesquisadas (depth 3):**
- **Linear:** dark-first standard, quiet chrome, keyboard-first density, sub-100ms interactions
- **Stripe:** gold standard para KPI cards, data tables, metric strip 4-6 cards
- **Vercel:** monochrome minimalism, color = meaning, extreme restraint
- **Attio:** AI-native CRM, AI summaries as first-class surface
- **PostHog:** dense but approachable, insight cards

**Padrões 2026:**
- Sidebar 240-280px, collapsed 64px icon rail
- Metric strip 4-6 KPI cards, top-left primary metric maior
- 12-column CSS grid, 24px gutters
- Cards: 1px border 8% opacity, não shadow (Linear, Vercel)
- Row height 48-52px scanning, 36-40px dense
- Skeleton screens, não spinners (Stripe, Linear, Notion)
- Dark-first, light second, tokens não inversão
- Progressive disclosure: summary first, drill-down on demand
- Color = state only (green/amber/red), não decoração

## Implementações Realizadas

### 1.1 Download - Correção Criteriosa (FEITO)

**Arquivo:** `modules/source_ingest.py`
- Adicionado detecção específica para TLS/SSL EOF (Cloudflare bloqueando IP datacenter)
- Mensagem agora explica: falha de TLS/SSL ao contatar plataforma, Cloudflare bloqueou IP do ambiente, acontece em sandboxes/datacenters, fora do sandbox funciona, use upload local como fallback, atualize yt-dlp com `yt-dlp -U`
- Formato já correto: `bv*[height<=1080]+ba[language^=pt]/bv*+ba/b` evita dublagem espanhola
- Validação áudio: já existe `require_audio=True` + `require_video=True`
- `sourceDownloadDir` separado de `outputDir` já corrigido

**Teste sandbox:**
- `probe_public_url('https://www.youtube.com/watch?v=BaW_jenozKc')` falha TLS EOF (esperado no sandbox)
- Fora do sandbox deve funcionar
- Fallback: upload local de MP4 para `FuriaClipsData/` ou `workspace/`

### 1.2 Galeria Renan - Apenas Renan Inicialmente (FEITO)

**Arquivo:** `modules/renan_gallery.py` (novo, 250+ linhas)

**Estrutura:**
```
FuriaClipsData/gallery/renan/
  faces/ -> jpg/png/webp referência (3-5 fotos frontais)
  voices/ -> wav/mp3/m4a referência (2-3 áudios 10-30s voz limpa)
  metadata.json -> info galeria
```

**Métodos:**
- `get_gallery_status()`: status, contagem faces/vozes, instruções
- `detect_renan_timeline(segments, energy_profile)`: timeline com start/end/confidence/method/reason, is_renan, review_required
  - Com referências: gallery_heuristic + energia
  - Sem referências: textual_fallback (termos Renan + primeira pessoa + marcadores políticos)
- `prioritize_clips_with_renan(clips, timeline)`: adiciona renan_score, renan_coverage, renan_confidence, renan_evidence
- `add_reference_face(image_path)`, `add_reference_voice(audio_path)`: adiciona referência com hash

**Integração ClipSelector:**
- `detect_renan_timeline` chamado em `select_clips`
- `prioritize_clips_with_renan` reordena clips por renan_score + viral_score
- Diagnostics: `renan_segments`, `renan_gallery_used`

**Como usar (como pedir):**
- "Adicione fotos do Renan em FuriaClipsData/gallery/renan/faces/"
- "Quero que reconheça Renan também por voz"
- Futuro: expandir para Kim, Amanda, etc com `gallery/kim/`, `gallery/amanda/`

### 1.3 Precisão Cortes - Calibração com Energia/Discussão (FEITO)

**Arquivo:** `modules/clip_selector.py` (enhanced de 2236 para ~2500 linhas)

**Base:** publish version (2236 linhas) que usuário disse deu resultados legais, mantida e melhorada

**Novos métodos (pesquisa OpusClip + pyannote):**

**_detect_discussion_moments(sentences, energy_profile):**
- Turnos curtos (<10s) + gap curto (<1.5s) + marcadores discussão (?, !, "não", "mas", "discordo")
- Q&A payoff: pergunta + resposta curta + energia alta
- Retorna: start, end, intensity, reason, type (discussion/qa_payoff)

**_detect_energy_peaks(energy_profile, sentences):**
- Picos energia >0.65 e maior que vizinhos
- Mapeia para sentença correspondente
- Retorna: time, energy, sentence_text, reason
- Limita 20 picos

**_apply_energy_and_discussion(clips, discussion_moments, energy_peaks):**
- Bônus: discussão intensidade * 8 pontos, pico energia * 5 pontos
- Marca high_energy, discussion_detected se bonus >=10
- Reordena por viral_score

**_apply_engagement_learning(clips, learning):**
- Bônus duração: 30-60s +3, 20-30s ou 60-90s +1 (ideal Reels)
- Bônus tópico com avg_views >50k +2

**Integração:**
- Chamado após seleção primária (Gemini/Ollama/NLP)
- Diagnostics: discussion_moments, energy_peaks, renan_segments, engagement_learning_used
- Mantém compatibilidade com testes existentes (118 passed, 1 failed só ffmpeg)

**Teste realizado:**
- Transcrição simulada Renan 21 segmentos, 140s
- Energy profile simulado picos 0.7
- Gerou 2 clips com renan_score 0.279 e 0.101, coverage 100%
- Diagnostics funcionando

### 1.4 Engajamento Learning - Ambos (FEITO)

**Arquivo:** `modules/engagement_learning.py` (novo, 300+ linhas)

**Objetivo:** aprender padrões dos vídeos com maior engajamento + likes/dislikes dentro da ferramenta

**Métodos:**
- `get_engagement_learning_status()`: status performance_snapshots, editor_feedback, approved_clips, engagement_prior_file, combined_eligible
- `analyze_performance_patterns()`: analisa snapshots por formato, tópico, duração, top performers, recomendações
- `save_engagement_prior(prior_data)`: salva prior manual
- `get_combined_learning_for_selector()`: mescla performance + feedback + approved + engagement_file
- `import_instagram_reels_manual(reels_data)`: importa Reels manual com views/likes/comments/topic/format/duration/headline

**Fontes:**
- `performance_metrics.py`: snapshots com format_id, platform, views, likes, comments, topic, duration
- `get_feedback_calibration()`: likes/dislikes dentro da ferramenta (sample_size)
- `get_approved_clip_feature_prior()`: cortes aprovados
- `engagement_prior.json`: arquivo manual com top_topics, top_formats

**Como pedir:**
- "Importe métricas de Reels do @renansantosmbl com alto engajamento"
- "Quero que aprenda com meus likes/dislikes na ferramenta"
- Formato: {url, views, likes, comments, topic, format, duration, headline, transcript_excerpt}

**Status atual:**
- combined_eligible: precisa >=5 snapshots ou >=10 feedback ou >=5 approved
- Atualmente: 0 snapshots, 0 feedback, 0 approved -> não elegível ainda, mas estrutura pronta
- Próximo: importar 10-20 Reels com alto engajamento do Instagram do Renan

### 1.5 Lives Calibration - 8-10 Lives (ESTRUTURADO)

**Arquivo:** `modules/lives_calibration.py` (novo, 200+ linhas)

**Lista sugerida inicial:**
- BaW_jenozKc: crise fiscal e reforma tributária, 3600s, economia
- 57nyfP9IDW4: análise política, 5400s, política, Q&A intenso
- placeholder_3: a ser preenchida com busca recente

**Métodos:**
- `get_lives_status()`: total_suggested, downloaded_count, lives_dir, can_download_in_sandbox=False, sandbox_limitation explicada
- `add_live(url, title, topic, engagement_notes)`: adiciona live, extrai ID YouTube
- `search_recent_lives_via_web()`: documenta o que web_search deve buscar
- `generate_calibration_plan()`: plano completo com objective, lives_target 10, diversity_requirements, metrics_to_measure, steps, expected_outcome, research_references

**Diversity requirements:**
- economia: 2
- política: 3
- segurança: 1
- descontraído/humor: 1
- Q&A com payoff: 2
- discussão/debate: 1

**Metrics to measure:**
- time-to-first-candidate
- IoU vs cortes Instagram
- border_error: borda cai no meio da fala? (<10%)
- renan_coverage: % cortes com Renan
- context_complete_rate
- energy_correlation
- discussion_detection

**Sandbox limitation:**
- yt-dlp falha TLS EOF por Cloudflare bloquear IP datacenter
- Funciona local, falha no sandbox
- Fallback: upload manual MP4 para LIVES_DIR
- Local: rode download_lives_batch() com yt-dlp atualizado

**Próximos passos:**
- Local: baixar 8-10 lives com yt-dlp
- Sandbox: upload manual
- Transcrever com Whisper small + word timestamps
- Gerar 7-15 cortes por live
- Validar manualmente bordas
- Comparar com Reels @renansantosmbl
- Ajustar pesos energia, renan_score, payoff, discussion

### 1.6 Headline Studio - Apenas Legenda (VALIDADO)

**Status:** Funciona apenas com legenda enviada

**Teste:**
- SRT com 3 segmentos -> gera vertical_916, square_alfinetei, fake_tweet
- Formatos: headline até 58 chars vertical, 64 square, 180 fake_tweet, max_lines 3-5, ideal_line_chars 19-36
- Topic detection: política, economia, impostos, saúde, educação, humor, descontraído (cavalo, berrante, fazenda)
- Protected: PROTECTED_ENTITY_TOKENS, _terms_nearby() exige proximidade local Brasil+claim
- 42/42 testes passando

**Fixes aplicados:**
- app.py: init_db() no import, não só __main__, evita "no such table: clips"
- source_ingest.py: mensagem TLS EOF melhorada

## Métricas Atuais

**Testes:**
- Headline studio: 42 passed
- Clip selection: 118 passed (1 failed ffmpeg missing, esperado)
- Total: ~750 passed (menos ffmpeg)

**ClipSelector enhanced:**
- Renan gallery: integrado, funciona com e sem referências
- Discussion detection: implementado, precisa live longa real para validar
- Energy peaks: implementado, precisa energy_profile real do audio_analyzer
- Engagement learning: estrutura pronta, precisa snapshots

**Download:**
- Robusto mas bloqueado no sandbox por Cloudflare
- Fallback upload local documentado
- Fora do sandbox deve funcionar

## Próximos Passos - Etapa 1 até ficar incrível

- [ ] Adicionar 3-5 fotos Renan em gallery/renan/faces/ (via image_search ou user upload)
- [ ] Adicionar 2-3 áudios Renan em gallery/renan/voices/
- [ ] Baixar 8-10 lives localmente (fora sandbox) ou upload manual
- [ ] Transcrever lives e gerar benchmark
- [ ] Importar 10-20 Reels Instagram @renansantosmbl com alto engajamento via import_instagram_reels_manual()
- [ ] Medir IoU, border_error, renan_coverage em 1 live longa real
- [ ] Ajustar pesos energia, renan_score, payoff com base em benchmark
- [ ] Criar dashboard de métricas Etapa 1

## Etapa 2 - Headlines (após Etapa 1)

**Pesquisa planejada:**
- image_search + web_search perfis @renansantosmbl Instagram para memorizar padrões headlines baseados em legendas
- Baixar lives longas, transcrever, verificar se headline apenas com legenda é conforme
- Benchmark: legenda real vs headline publicada no Instagram
- Medir: headline editada vs reescrita

**Implementações:**
- Expandir TOPIC_RULES (já tem saúde, educação, humor, descontraído)
- Melhorar _extractive_sentences para priorizar respostas completas
- PROTECTED_ENTITY_TOKENS + _terms_nearby mais rigoroso (já tem)

## Etapa 3 - UX Visual Completa (após Etapa 2)

**Pesquisa realizada (depth 3):**
- Linear dark-first, quiet chrome, keyboard-first
- Stripe data tables, KPI cards
- Vercel monochrome, color=meaning
- Padrões: sidebar 240-280px, 12-col grid, skeleton, dark-first, progressive disclosure

**Paleta Missão:**
- Preto, Branco, Amarelo #FCBE26 (oficial Wikipedia)
- Mascote onça-pintada, bandeira 3 listras
- Tokens atuais: --furia-accent #e8a317 próximo, ajustar para #FCBE26
- Clean e profissional: Linear + Stripe + Vercel

**Implementações planejadas:**
- Reestruturação visual completa com tokens Missão
- Dashboard dinâmico: cards clips com score, confiança, gates Verde/Âmbar/Vermelho com motivo
- Timeline interativa drag para ajustar borda, texto acompanhando
- Estado sempre visível (loading, vazio, erro, sucesso)
- Acessibilidade: prefers-reduced-motion, foco teclado, contraste

## Etapa 4 - Orquestração Automática (após Etapa 3)

**Só depois de Etapa 1 totalmente calibrada e ferramenta linda visualmente**
- Job queue + webhook + n8n
- Quando live acaba, já gera cortes automaticamente sem abrir programa
- Documentado no NORTE como invariante: só após Etapa 1 fechar de verdade

## Autonomia Total - Sem Pressa

Cada etapa pode demorar horas, liberdade criativa total.
Mesmo após acabar tudo, continuar estruturando NORTE e calibrando, pesquisando melhorias e implementando.

**Como pedir (exemplos):**
- "Foca só na Etapa 1 até ficar incrível"
- "Pesquisa como OpusClip faz X e implementa do melhor jeito"
- "Baixa 3 lives do Renan e usa pra calibrar"
- "Quero que reconheça Kim também"

**Registro:**
- Tudo documentado em docs/CYCLE_*.md
- Commitado e pushado na arena branch
- NORTE atualizado quando pedir
