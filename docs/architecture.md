# Arquitetura-alvo do Furia Clips

## Visão de produto

O Furia Clips será um **sistema local de clipping editorial multimodal**, no qual a IA encontra e explica oportunidades de corte, mas o usuário mantém controle rápido sobre a seleção e a renderização. A arquitetura não deve ser organizada em torno de um único provedor de IA. Ela deve funcionar em camadas: quanto mais recursos locais estiverem disponíveis, maior a qualidade; quando um recurso falhar, o sistema continua operando com transparência.

O benchmark público mostra que uma experiência competitiva combina clipping por prompt, análise visual e sonora, score comparável entre clips, edição por texto e timeline, reenquadramento por cena, legendas, branding, projetos, processamento em lote, API e feedback. [1] [2] [3] [4]

## Princípios

A timeline do vídeo original é a fonte canônica. Todos os artefatos derivados, como vídeo sem silêncio, segmentos transcritos, cenas, rostos, candidatos, legendas e exports, devem guardar a versão da timeline que os gerou e uma forma de conversão para o vídeo original.

A execução é orientada a jobs. Cada operação recebe um ID, estado, progresso, logs, artefatos e erros. A interface nunca deve depender apenas de eventos globais que podem ser perdidos quando o navegador reconecta.

A seleção é separada da renderização. O sistema pode gerar candidatos e permitir revisão antes de gastar tempo renderizando legendas, reframe e variantes de plataforma.

A qualidade é mensurável. Cada clip deve passar por gates de timeline, duração, áudio, vídeo, legendas, enquadramento e segurança antes de ser marcado como pronto.

A IA é substituível. Gemini, Ollama, Claude ou um modelo local futuro devem obedecer ao mesmo contrato de entrada e saída; o usuário precisa saber qual motor foi utilizado e por que houve fallback.

## Fluxo lógico

```text
[Ingestão]
   ├─ validação segura de arquivo
   ├─ hash, metadados e duração
   └─ projeto persistido
          ↓
[Análise de mídia]
   ├─ extração de áudio
   ├─ VAD e energia
   ├─ transcrição e timestamps por palavra
   ├─ cenas e frames-chave
   ├─ rostos/objetos quando disponíveis
   └─ timeline_map de qualquer derivado
          ↓
[Compreensão editorial]
   ├─ prompt do usuário estruturado
   ├─ blocos semânticos
   ├─ intenção, entidades, emoção e restrições
   └─ sinais de contexto e locutor
          ↓
[Geração de candidatos]
   ├─ janelas por frase e palavra
   ├─ pergunta/resposta
   ├─ momentos visuais e sonoros
   └─ duração adaptativa
          ↓
[Ranqueamento]
   ├─ hook, flow, value e trend/contexto
   ├─ energia, clareza e completude
   ├─ enquadramento e confiança
   ├─ diversidade temporal/temática
   └─ editorial_potential_score
          ↓
[Revisão]
   ├─ preview
   ├─ início/fim
   ├─ layout
   ├─ legenda e branding
   └─ aprovar/rejeitar
          ↓
[Renderização]
   ├─ reframe por cena
   ├─ captions e safe areas
   ├─ áudio e normalização
   ├─ preset por plataforma
   └─ validação ffprobe
          ↓
[Entrega]
   ├─ exports
   ├─ SEO e thumbnail
   ├─ lote e histórico
   └─ feedback/calibração
```

## Componentes

| Componente | Responsabilidade | Estado recomendado |
| --- | --- | --- |
| `ingestion` | Validar uploads, criar projeto, calcular hash e metadados | Novo módulo isolado |
| `timeline` | Representar intervalos, converter timelines e validar limites | Novo núcleo compartilhado |
| `transcription` | Whisper/faster-whisper, cache versionado e palavras | Adaptar `modules/transcriber.py` |
| `media_analysis` | VAD, energia, cenas, frames, rostos e objetos | Consolidar módulos existentes |
| `prompting` | Converter pedido do usuário em intenção estruturada | Novo módulo |
| `candidate_generation` | Gerar janelas candidatas multimodais | Reestruturar `clip_selector.py` |
| `editorial_ranking` | Calcular score, fatores, confiança e diversidade | Reestruturar `viral_ranker.py` |
| `job_orchestrator` | Fila, estados, progresso, cancelamento e retomada | Novo módulo; substituir estado global |
| `rendering` | Corte, layout, reframe, legendas e presets | Evoluir `video_cutter.py` e `subtitle_generator.py` |
| `quality_gates` | Validar saída, timeline e segurança | Novo módulo |
| `projects` | Persistir projetos, candidatos, versões e feedback | Evoluir `database.py` |
| `api` | Endpoints REST e eventos por job | Adaptar `app.py` |
| `frontend` | Biblioteca, revisão, timeline, jobs e presets | Evoluir `templates/index.html` e `static/js/app.js` |

## Modelo de dados-alvo

As tabelas atuais devem evoluir sem destruir dados antigos. O modelo mínimo recomendado é:

| Entidade | Campos essenciais |
| --- | --- |
| `projects` | id, nome, source_path, source_hash, status, created_at, updated_at |
| `media_assets` | id, project_id, path, kind, mime, size, duration, width, height, checksum |
| `timelines` | id, project_id, source_asset_id, derived_asset_id, segments_json, version |
| `transcriptions` | id, project_id, timeline_id, model, language, segments_json, full_text, version |
| `analysis_runs` | id, project_id, job_id, detector, version, signals_json, status |
| `candidates` | id, project_id, start, end, source, prompt_match, factors_json, score, confidence |
| `clip_edits` | id, candidate_id, start, end, layout_json, caption_json, status |
| `render_jobs` | id, clip_edit_id, preset, output_path, validation_json, status |
| `feedback` | id, candidate_id, action, adjustments_json, created_at |
| `jobs` | id, project_id, type, state, stage, progress, message, error, timestamps |
| `settings` | chave/valor, com segredos fora da resposta da API |

## Contrato de job

Cada job deve retornar uma estrutura equivalente a:

```json
{
  "job_id": "uuid",
  "project_id": 1,
  "type": "analyze_and_select",
  "state": "running",
  "stage": "candidate_generation",
  "progress": 48,
  "message": "Gerando candidatos por limites de palavra",
  "artifacts": [],
  "error": null,
  "created_at": "2026-08-12T00:00:00Z",
  "updated_at": "2026-08-12T00:01:00Z"
}
```

## Estratégia de timeline

A remoção de silêncio não deve substituir o vídeo original como fonte de corte. O sistema deve analisar o original e manter os silêncios como sinais para pontuar ou propor edições. Caso crie um derivado compactado, deverá persistir uma função por segmentos:

```text
original [o_start, o_end] ↔ derivado [d_start, d_end]
```

Qualquer intervalo derivado deve ser convertido para o original antes do corte final. Legendas e frames também precisam ser recalculados ou convertidos no mesmo mapa.

## Estratégia de multimodalidade

A execução começa com sinais baratos e confiáveis: duração, audio stream, VAD, energia, transcrição, palavras e pausas. Em seguida, adiciona cenas e frames-chave. A detecção de rostos e objetos é aplicada por amostragem e refinada apenas nos candidatos, para reduzir custo. Modelos de linguagem avaliam intenção, contexto, completude e valor, mas não devem inventar timestamps fora das janelas fornecidas.

O prompt do usuário deve virar uma intenção estruturada com sujeito, ação, tema, emoção, restrições, gênero, duração e quantidade. Isso torna “momentos em que o convidado critica o governo” diferente de “momentos emocionais” de forma testável.

## Integração com GitHub

O desenvolvimento deve ocorrer em branch de trabalho. Cada unidade lógica produz testes e um commit. A branch principal só recebe mudanças por Pull Request aprovado pelo usuário. A integração GitHub é opcional durante a implementação local; a ausência de autenticação não pode impedir testes nem causar alegações falsas de publicação.

## Referências

[1]: https://help.opus.pro/docs/article/introduction-to-opusclip "Introdução ao OpusClip"

[2]: https://help.opus.pro/docs/article/9947095-clip-anything "ClipAnything multimodal"

[3]: https://help.opus.pro/docs/article/clip-anything-prompt-manual "Manual de prompts"

[4]: https://www.opus.pro/api "API pública do OpusClip"
