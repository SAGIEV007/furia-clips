# NORTE Update - Etapa 1 - 2026-08-22 - Arena

## O que foi feito nesta sessão (autonomia total)

### Pesquisa extensa antes de cada etapa (como pedido):

**Cortes - ferramentas de mercado:**
- OpusClip ClipAnything: multimodal visual+áudio+sentimento+face, Virality Score 0-99 Hook/Flow/Value/Trend, ReframeAnything com easing, 10M usuários
- Vizard: cleaner entry/exit que OpusClip, transcript-editor highlight-to-cut, active-speaker tracking
- CapCut: até 3h/10GB, highlight detection visual/audio/contexto
- Pipeline comum: Transcrição word-level -> Moment detection LLM -> Reframing CV -> Captions ASS -> Render FFmpeg
- Diarization: pyannote, Resemblyzer d-vector, VoxCeleb SyncNet + CNN face, AdaFace ResNet-18, M3SD 770h
- Energy/discussion: RMS+pitch+overlap <2s turn, discussão = turnos curtos + overlap + energia alta, coice = Q+A + energia + payoff

**Headlines - padrões Renan Instagram:**
- @renansantosmbl: 2M followers, 3,233 posts, 5.11% engajamento (A+ orgânico), acima 1.41% Flávio Bolsonaro
- TikTok 210.8k followers 5.2M likes, motor viralização jovem
- Reels mais vistos: Segurança pública 12.4M views (mais visto campanha), Qual é nosso maior inimigo? 7.7M, Henry Borel 5.9M
- Padrões: headline curta caixa alta até 58 chars vertical, 64 square, 180 fake_tweet, max_lines 3-5, ideal 19-36 chars, tese branca + chamada amarela
- Linguagem direta provocativa, cortes rápidos embates diretos, antissistema, liberdade econômica

**UX - sites incríveis:**
- Linear: dark-first standard, quiet chrome 240-280px sidebar, keyboard-first, 1px border 8% opacity não shadow, sub-100ms, 36px rows
- Stripe: gold standard KPI cards, data tables as primary, metric strip 4-6 cards, skeleton loading
- Vercel: monochrome minimalism, color=meaning, extreme restraint, Geist font
- Padrões 2026: sidebar 260px collapsed 64px icon rail, 12-col grid 24px gutters, 48-52px row scanning, 36-40px dense, skeleton not spinners, dark-first tokens, progressive disclosure, color=state only

**Partido Missão - paleta:**
- Cores oficiais: Preto, Branco, Amarelo #FCBE26 (Wikipedia template)
- Mascote onça-pintada, bandeira 3 listras horizontais preto/branco/amarelo logo na faixa branca
- Nome referência missão/visão/valores planejamento estratégico empresarial

### Implementações Etapa 1:

**Download:**
- source_ingest.py: TLS/SSL EOF handling específico Cloudflare, mensagem explica falha datacenter, sugere upload local fallback, formato bv*[height<=1080]+ba[language^=pt] já correto
- app.py: init_db() no import não só __main__, fix no such table clips

**Galeria Renan (só Renan inicialmente):**
- renan_gallery.py novo 250+ linhas, FuriaClipsData/gallery/renan/faces+voices, metadata.json
- 5 fotos Renan adicionadas via image_search, has_references true
- detect_renan_timeline: textual_fallback + energia, com refs gallery_heuristic, confidence, is_renan, review_required
- prioritize_clips_with_renan: renan_score, coverage, confidence, evidence, reordena por renan_score+viral_score
- Teste: 12 segmentos Renan detectados confidence 0.74 renan_score 0.742 coverage 100% (antes 0.279 sem refs)

**Precisão cortes:**
- clip_selector.py enhanced 2236->2500 linhas, base publish mantida (user disse deu bons resultados)
- _detect_discussion_moments: turnos <10s + gap <1.5s + marcadores ?,!,não,mas,discordo, Q&A payoff pergunta+resposta+energia
- _detect_energy_peaks: energia >0.65 maior que vizinhos, mapeia sentença, limita 20 picos
- _apply_energy_and_discussion: bônus discussão intensidade*8, pico energia*5, marca high_energy discussion_detected se bonus>=10
- _apply_engagement_learning: bônus duração 30-60s +3, tópico avg_views>50k +2
- Diagnostics: renan_segments, discussion_moments, energy_peaks, engagement_learning_used
- Testes: 118 passed 1 ffmpeg missing, headline 42 passed

**Engajamento learning (ambos):**
- engagement_learning.py novo 300+ linhas, performance_snapshots + feedback calibration + approved_clip_prior + engagement_prior.json
- import_instagram_reels_manual: 5 Reels importados 32M views total avg 6.4M, top_topics política 2 segurança 1 impostos 1 liberdade 1, top_formats vertical_916 4 square 1
- analyze_performance_patterns: by_format, by_topic, by_duration, top_performers
- get_combined_learning_for_selector: mescla tudo, recommendations
- Status: combined_eligible precisa >=5 snapshots ou >=10 feedback ou >=5 approved, atualmente 0/0/0 mas estrutura pronta + engagement_prior file existe

**Lives calibration 8-10:**
- lives_calibration.py novo 200+ linhas, plano 10 lives, diversity economia 2 política 3 segurança 1 descontraído 1 Q&A 2 discussão 1
- Metrics: time-to-first-candidate, IoU vs Instagram, border_error <10%, renan_coverage, context_complete, energy_correlation, discussion_detection
- Lista: BaW_jenozKc crise fiscal, 57nyfP9IDW4 análise política Q&A, placeholder busca recente
- get_lives_status, add_live, search_recent_lives_via_web, generate_calibration_plan
- Sandbox limitation: yt-dlp TLS EOF Cloudflare bloqueia IP datacenter, funciona local, fallback upload manual LIVES_DIR, documentado

**Visual clean profissional:**
- furia-tokens.css: --furia-accent atualizado #e8a317 -> #FCBE26 Missão oficial amarelo, hover #FFD54F, adicionado --missao-yellow #FCBE26 --missao-black #000000 --missao-white #FFFFFF --missao-yellow-soft/ring/hover, --missao-mascot onça-pintada, --missao-flag 3 listras, --dashboard-sidebar-width 260px (Linear 240-280), --dashboard-kpi-height 52px, --dashboard-card-border 1px solid rgba(255,255,255,0.08) border not shadow, --dashboard-grid-gutter 24px, --dashboard-row-height 48px dense 36px, --dashboard-skeleton-bg shimmer
- furia-clean-pro.css novo 400+ linhas: Clean Professional Dashboard Linear+Stripe+Vercel inspired, sidebar 260px collapsed 64px, KPI strip grid auto-fit minmax 200px, KPI card border not shadow, primary KPI span 2 28px bold, clip cards border-left 3px color=meaning verde/ambar/vermelho/Renan/discusão, timeline interactive 8px segments, skeleton shimmer 1.5s, tables sticky header 40px uppercase 12px, row 48px dense 36px, pills 22px 11px semibold, Missão brand accents, buttons restraint no lift, sidebar nav 32px 13px 450 weight, empty states 48px icon, progress 4px Missão yellow, 12-col grid, responsive collapse to icon rail 1024px, focus-visible ring, prefers-reduced-motion
- index.html: adicionado furia-clean-pro.css após style.css

### Próximos passos (autonomia total, pode levar horas, continuar mesmo após acabar tudo):

**Etapa 1 até ficar incrível (foco atual):**
- [ ] Adicionar 2-3 áudios Renan em gallery/renan/voices/ (10-30s voz limpa)
- [ ] Baixar 8-10 lives localmente fora sandbox (yt-dlp -U) ou upload manual para ~/FuriaClipsData/lives_calibration/
- [ ] Transcrever lives com Whisper small + word timestamps
- [ ] Gerar 7-15 cortes por live, medir IoU vs Reels Instagram, border_error, renan_coverage, context_complete
- [ ] Importar 10-20 Reels Instagram @renansantosmbl com alto engajamento via performance snapshots API
- [ ] Ajustar pesos energia, renan_score, payoff, discussion com base em benchmark
- [ ] Dashboard métricas Etapa 1

**Etapa 2 - Headlines:**
- Pesquisa: image_search + web_search @renansantosmbl padrões headlines baseados em legendas, baixar lives longas transcrever verificar headline só com legenda
- Benchmark: legenda real vs headline publicada Instagram, medir editada vs reescrita
- Implementar: expandir TOPIC_RULES (já tem saúde educação humor descontraído), melhorar _extractive_sentences priorizar respostas completas, PROTECTED_ENTITY_TOKENS + _terms_nearby rigoroso

**Etapa 3 - UX Visual Completa:**
- Pesquisa já feita Linear/Stripe/Vercel/PostHog, paleta Missão #FCBE26 preto branco
- Implementar: reestruturação visual completa tokens, dashboard dinâmico cards score confiança gates Verde/Âmbar/Vermelho motivo, timeline drag ajustar borda texto acompanhando, estado sempre visível loading vazio erro sucesso, acessibilidade prefers-reduced-motion foco teclado contraste
- Critério saída: existe pelo menos uma tela que editor mostraria para outra pessoa (NORTE 12.7)

**Etapa 4 - Orquestração Automática (só após Etapa 1 totalmente calibrada e ferramenta linda):**
- Job queue + webhook + n8n, quando live acaba já gera cortes automaticamente sem abrir programa
- NORTE invariante: só após Etapa 1 fechar de verdade

**Melhorias contínuas (mesmo após acabar tudo, estruturar NORTE e continuar):**
- Pesquisar melhorias clipping, headline, UX
- Calibrar com mais lives
- Expandir galeria para Kim, Amanda, etc quando pedir
- Aprendizado contínuo com feedback editor

### Como pedir (com autonomia total):

Exemplos simples e diretos:
- "Foca só na Etapa 1 até ficar incrível, não precisa me perguntar"
- "Quando terminar Etapa 1, vai pra Etapa 2 de headlines"
- "Pesquisa como o OpusClip faz X e implementa do melhor jeito"
- "Baixa 3 lives do Renan e usa pra calibrar, documenta tudo"
- "Atualiza o NORTE com essa ideia: [sua ideia]"
- "Quero que a ferramenta reconheça o Kim Kataguiri também"
- "Importe métricas de Reels com alto engajamento"
- "Adicione fotos do Renan na galeria"

Eu vou fazer pesquisa extensa antes de cada mudança de etapa, buscar referências reais, implementar menor mudança que testa hipótese, medir antes/depois com MP4 real e testes, documentar tudo em CYCLE_*_REPORT.md e NORTE quando pedir, commitar e pushar na arena.

### Status atual:

- Branch arena/01a02c77-furia-clips com 4b9cb37 pushado
- Gallery Renan 5 faces, 0 voices, has_references true
- Engagement prior 5 Reels 32M views avg 6.4M
- ClipSelector enhanced com Renan + energia + discussão + engajamento
- Tokens Missão #FCBE26 + clean pro CSS Linear/Stripe/Vercel
- Testes 118+42 passed (menos ffmpeg)
- Pronto para continuar Etapa 1 calibração com lives reais local
