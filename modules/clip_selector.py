"""
Clip Selector — Intelligent clip selection using Gemini, Ollama (LLM) or NLP fallback.

Selection priority in automatic mode:
1. Google Gemini Flash, only when a key is already configured
2. Ollama local LLM, when the service and model are available
3. NLP keyword matching, always available and requiring no key
"""

import json
import re
import math
import requests
from difflib import SequenceMatcher
from collections import Counter

from .political_profile import PROFILE_NAME, build_political_prompt_fragment
from .editorial_chapters import annotate_clip_with_chapters
from .interview_turns import (
    detect_interviewer_turns,
    is_interviewer_sentence,
    looks_like_an_interview,
)

PREFERRED_MAX_DURATION = 180.0
TECHNICAL_MAX_DURATION = 600.0

# Portuguese filler words to detect
FILLER_WORDS_PT = {
    "ne", "ne\u0301", "tipo", "ah", "eh", "e\u0301h", "enta\u0303o", "entao",
    "sabe", "basicamente", "na verdade", "ou seja", "entendeu",
    "digamos", "assim", "enfim", "bom", "olha", "veja",
    "quer dizer", "pois e\u0301", "pois e", "ta", "ta\u0301", "cara",
}

CONTINUATION_STARTERS_PT = {
    "e", "mas", "porem", "porém", "porque", "que", "ai", "aí", "entao", "então", "ou", "nem",
}
CONTEXT_REFERENCE_STARTERS_PT = {
    "isso", "isto", "aquilo", "esse", "essa", "esses", "essas", "aquele", "aquela",
    "aqueles", "aquelas", "ele", "ela", "eles", "elas", "nesse", "nessa", "nisso",
    "com isso", "por isso", "foi ali", "foi aí", "foi ai", "foi quando",
}
EVIDENCE_TERMS_PT = {
    "dado", "dados", "numero", "número", "numeros", "números", "pesquisa", "pesquisas",
    "registro", "registros", "email", "emails", "e-mail", "fonte", "prova", "provas",
    "documento", "documentos", "exemplo", "exemplos", "lei", "artigo", "segundo",
}
WEAK_PAYOFF_ENDINGS_PT = {
    "porque", "mas", "porém", "porem", "se", "quando", "que", "como", "embora",
    "então", "entao", "portanto", "logo", "ou seja", "por isso", "dessa forma", "com isso",
}


def _block_field(block, *names):
    """Read a block field written in either naming convention.

    Snapshots reach the selector both snake_cased by the local converter and
    camelCased straight from the Acervo, so reading only one shape silently
    dropped ranks, risks and the speaker verdict.
    """
    for name in names:
        value = block.get(name)
        if value is not None:
            return value
    return None


class ClipSelector:
    # How far a Campaign Hub seed may fall outside every sentence and still be
    # anchored to the nearest one. Silences, applause and music leave real gaps in
    # a transcript; a mismatch of whole minutes means a timeline mismatch instead.
    MAX_SEED_ANCHOR_GAP_S = 60.0

    # How far a clip's start may move forward to land on a sentence. Beyond this
    # the window was chosen wrong and trimming would hide the real problem.
    MAX_OPENING_TRIM_S = 15.0

    # Words of the answer that must be inside the clip before a question can be
    # considered closed. Fewer than this and the viewer still gets no payoff.
    MIN_ANSWER_WORDS = 12

    # Share of a candidate that may sit on labelled non-content before the
    # candidate is discarded instead of competing for a slot.
    NON_CONTENT_DROP_RATIO = 0.5

    # How far a clip's start may move back to open on the interviewer's question
    # instead of on the tail of the previous answer.
    MAX_TURN_START_SNAP_S = 20.0

    # How far a clip's end may move to land on a seam of the conversation. The
    # selector already had a view on how much material the idea needs; beyond
    # this the boundary is not being repaired, it is being replaced. Growth is
    # additionally bounded by the preferred maximum duration.
    MAX_TURN_END_SHIFT_S = 90.0

    def __init__(
        self,
        target_duration=45,
        max_clips=15,
        min_duration=8,
        max_duration=TECHNICAL_MAX_DURATION,
        preferred_max_duration=PREFERRED_MAX_DURATION,
    ):
        # ``target_duration`` remains for backward compatibility, but is only a
        # soft stopping hint. Context and sentence completion always win.
        self.target_duration = target_duration
        self.max_clips = max_clips
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.preferred_max_duration = preferred_max_duration
        self._candidate_diagnostics = {
            "expected_count": 0,
            "primary_count": 0,
            "fallback_count": 0,
            "final_count": 0,
            "fallback_used": False,
            "fallback_discarded_count": 0,
            "fallback_discarded_overlap": 0,
            "fallback_discarded_similarity": 0,
            "previous_discarded_count": 0,
            "previous_discarded_approved": 0,
            "previous_discarded_rejected": 0,
            "reason": "not_evaluated",
        }

    def select_clips(self, transcription, energy_profile=None, user_context="",
                     settings=None, emit_progress=None, scene_changes=None,
                     video_layout=None):
        settings = settings or {}
        self._selection_source = None
        self._previous_clip_fingerprints = [
            item for item in (settings.get("previous_clip_fingerprints") or [])
            if isinstance(item, dict)
        ]
        ai_backend = settings.get("ai_backend", "auto")
        gemini_key = str(settings.get("gemini_api_key", "") or "").strip()
        sentences = self._build_sentences(transcription["segments"])

        if emit_progress:
            emit_progress(f"Transcricao dividida em {len(sentences)} sentencas")

        if user_context and emit_progress:
            keywords = self._extract_context_keywords(user_context)
            if keywords:
                emit_progress(f"Contexto aplicado: {', '.join(keywords[:8])}...", "info")

        clips = None

        # Gemini só entra no fluxo automático quando a chave já existe.
        if ai_backend in ("auto", "gemini") and gemini_key:
            clips = self._select_with_gemini(
                sentences, energy_profile, user_context, settings, emit_progress
            )
            if clips:
                self._selection_source = "gemini"
                if emit_progress:
                    emit_progress(f"[Gemini] Selecao inteligente concluida! {len(clips)} clips.", "success")

        # Ollama é opcional; falhas de conexão não interrompem o processamento.
        if not clips and ai_backend in ("auto", "gemini", "ollama"):
            if ai_backend == "gemini" and not gemini_key and emit_progress:
                emit_progress("[Gemini] Sem chave configurada; seguindo para o modo local.", "info")
            elif ai_backend == "gemini" and emit_progress:
                emit_progress("[Gemini] Tentando Ollama como fallback...", "warning")
            clips = self._select_with_llm(
                sentences, energy_profile, user_context, settings, emit_progress
            )
            if clips:
                self._selection_source = "llm"
                if emit_progress:
                    emit_progress(f"[Ollama] Selecao inteligente concluida! {len(clips)} clips.", "success")

        # O ranking NLP é o caminho final e não requer API, Ollama ou download extra.
        if not clips:
            self._selection_source = "nlp"
            if emit_progress:
                emit_progress("[NLP] Usando selecao local por contexto e palavras-chave.", "info")
            clips = self._select_with_nlp(
                sentences,
                energy_profile,
                user_context,
                emit_progress,
                editorial_context=settings.get("editorial_context"),
            )

        guided_clips = self._select_with_campaign_hub_guidance(
            sentences,
            settings,
            emit_progress=emit_progress,
        )
        if guided_clips:
            legacy_clips = list(clips or [])
            clips = guided_clips + legacy_clips
            self._selection_source = "campaign_hub_guided"
            if emit_progress:
                emit_progress(
                    f"[Campaign Hub] {len(guided_clips)} proposta(s) guiada(s) adicionada(s) antes do ranking; "
                    "as propostas permanecem sujeitas aos gates e à revisão editorial.",
                    "info",
                )

        expected_count = self._expected_candidate_count(sentences)
        primary_clips = list(clips or [])
        self._candidate_diagnostics = {
            "expected_count": expected_count,
            "primary_count": len(primary_clips),
            "fallback_count": 0,
            "final_count": 0,
            "fallback_used": False,
            "fallback_discarded_count": 0,
            "fallback_discarded_overlap": 0,
            "fallback_discarded_similarity": 0,
            "previous_discarded_count": 0,
            "previous_discarded_approved": 0,
            "previous_discarded_rejected": 0,
            "reason": "short_source" if expected_count == 0 else ("adequate_pool" if len(primary_clips) >= expected_count else "primary_pool_thin"),
        }
        if primary_clips and expected_count and len(primary_clips) < expected_count:
            fallback_clips = self._select_with_nlp(
                sentences,
                energy_profile,
                user_context,
                emit_progress,
                editorial_context=settings.get("editorial_context"),
            ) or []
            if fallback_clips:
                primary_keys = {(round(float(item.get("start", 0)), 3), round(float(item.get("end", 0)), 3)) for item in primary_clips}
                additions = [
                    item for item in fallback_clips
                    if (round(float(item.get("start", 0)), 3), round(float(item.get("end", 0)), 3)) not in primary_keys
                ]
                clips = primary_clips + additions
                self._candidate_diagnostics.update({
                    "fallback_count": len(additions),
                    "fallback_used": bool(additions),
                })
                if additions and emit_progress:
                    emit_progress(
                        f"[Fallback editorial] A fonte principal retornou {len(primary_clips)} candidatos; "
                        f"foram acrescentadas {len(additions)} alternativas locais para revisão, sem relaxar os gates.",
                        "warning",
                    )

        # Drop candidates sitting on stretches the Acervo already labelled as
        # holding no editorial content, before the candidate budget is spent.
        # A window that opens on the tail of a sentence reads as broken even when
        # the material inside it is right, so the boundary is repaired before any
        # other judgement is made about the candidate.
        clips = self._trim_opening_fragment(clips, emit_progress)

        clips = self._close_open_question(clips, sentences, emit_progress)

        # On an interview the seams of the material are the interviewer's turns,
        # and they have the last word on both boundaries: no clip may stop in the
        # middle of an answer or run past the next change of subject.
        clips = self._align_to_interview_turns(clips, sentences, emit_progress)

        clips = self._drop_labelled_non_content(clips, settings, sentences, emit_progress)

        # Every surviving candidate inherits what the Acervo established about the
        # stretch it covers, so the reviewer never sees an anonymous window.
        clips = self._attach_block_evidence(clips, settings)

        # Where the Acervo has nothing to say, Furia reads the subjects itself.
        clips = self._attach_local_topic_context(clips, sentences, emit_progress)

        # Scene changes are camera switches. On material where the picture tells
        # the story that is a good place to cut; in an interview the direction
        # switches cameras mid-answer, and snapping a boundary to it moves the cut
        # off the seam of the conversation by up to two seconds — undoing the
        # alignment above for no editorial gain. On the sabatina the director cut
        # 143 times in 31 minutes, none of them where the subject changed.
        if scene_changes and not self._candidate_diagnostics.get("interview_seams"):
            clips = self._adjust_to_scene_boundaries(clips, scene_changes)
        elif scene_changes and emit_progress:
            emit_progress(
                "[Cenas] Fonte reconhecida como entrevista; as bordas seguem as perguntas, "
                "não as trocas de câmera.",
                "info",
            )

        # Preserve chapter evidence before overlap normalization so every
        # backend (Gemini, Ollama, and NLP) exposes the same review contract.
        editorial_context = settings.get("editorial_context")
        clips = [annotate_clip_with_chapters(clip, editorial_context) for clip in clips]
        transcription_quality = (editorial_context or {}).get("transcription_quality", {}) if isinstance(editorial_context, dict) else {}
        if transcription_quality.get("review_required"):
            coverage_status = str(transcription_quality.get("status", "unknown") or "unknown")
            for clip in clips:
                clip["transcription_review_required"] = True
                clip["transcription_coverage_status"] = coverage_status
                clip["transcription_review_reason"] = (
                    "cobertura parcial da transcrição; confirme o trecho no vídeo"
                    if coverage_status == "partial"
                    else "identidade temporal da transcrição não validada; confirme o trecho no vídeo"
                )
        fallback_used = bool(self._candidate_diagnostics.get("fallback_used"))
        for clip in clips:
            source = str(clip.get("source") or "nlp").lower()
            if source == "campaign_hub_guided":
                origin = "campaign_hub_guided"
                origin_label = "Campaign Hub — proposta guiada"
            elif source == "gemini":
                origin = "gemini_primary"
                origin_label = "Gemini — seleção primária"
            elif source == "llm":
                origin = "ollama_primary"
                origin_label = "Ollama — seleção primária"
            elif fallback_used:
                origin = "local_fallback"
                origin_label = "NLP local — alternativa de cobertura"
            else:
                origin = "local_primary"
                origin_label = "NLP local — seleção primária"
            clip["candidate_origin"] = origin
            clip["candidate_origin_label"] = origin_label
            clip["candidate_origin_note"] = (
                "Alternativa acrescentada porque a fonte primária devolveu um pool curto; "
                "não substitui a avaliação editorial humana."
                if origin == "local_fallback"
                else "Proposta guiada por seed autorizada do Campaign Hub; revisão editorial continua obrigatória."
                if origin == "campaign_hub_guided"
                else "Origem registrada para transparência da revisão."
            )

        # Apply anti-overlap filter after origin labels are available so a
        # primary candidate wins deterministic conflicts with local fallback.
        clips = self._remove_overlaps(clips)

        # Do not recreate intervals already generated in a previous run of the same source.
        clips = self._remove_previous_fingerprints(clips)

        # Limit to the adaptive maximum only after deduplication, so a second run can
        # fill the queue with genuinely new moments instead of truncating repetitions.
        clips = clips[:self.max_clips]
        self._candidate_diagnostics["final_count"] = len(clips)

        if emit_progress:
            source_labels = {
                "gemini": "Gemini Flash",
                "llm": "IA (Ollama)",
                "nlp": "NLP basico",
                "campaign_hub_guided": "Campaign Hub + selecao local",
            }
            source_label = source_labels.get(self._selection_source, "NLP basico")
            emit_progress(f"Selecionados {len(clips)} clips de partes diferentes do video (via {source_label})")

        return clips

    def get_selection_source(self):
        return self._selection_source or "nlp"

    def get_candidate_diagnostics(self):
        """Return explainable candidate-volume diagnostics for the review UI."""
        return dict(self._candidate_diagnostics)

    def _expected_candidate_count(self, sentences):
        """Estimate a review pool size without turning the daily goal into a quota."""
        if not sentences:
            return 0
        try:
            span = max(0.0, float(sentences[-1].get("end", 0)) - float(sentences[0].get("start", 0)))
        except (TypeError, ValueError):
            span = 0.0
        if span < 120 or len(sentences) < 8:
            return 0
        duration_based = int(span // 240) + 6
        structure_based = int(len(sentences) // 18) + 6
        return min(max(3, duration_based, structure_based), max(3, min(self.max_clips, 36)))

    def _extract_context_keywords(self, user_context):
        """Extract meaningful keywords from user context for display."""
        stop_words = {
            "quero", "extrair", "cortes", "onde", "esteja", "neste", "nesta",
            "debate", "principalmente", "quando", "sobre", "para", "como",
            "que", "com", "dos", "das", "nos", "nas", "por", "mais",
            "uma", "uns", "umas", "este", "esta", "esse", "essa",
            "ele", "ela", "eles", "elas", "seu", "sua", "seus", "suas",
            "nos", "pontos", "fala", "fale", "deste", "desta",
        }
        words = user_context.split()
        keywords = []
        for w in words:
            clean = re.sub(r'[^\w]', '', w)
            if clean and len(clean) > 1 and clean.lower() not in stop_words:
                keywords.append(clean)
        return keywords

    def _extract_names_from_context(self, user_context):
        """Extract likely person names from user context for speaker filtering.
        Only extracts words that start with uppercase (proper nouns)."""
        stop_words = {
            "quero", "quando", "como", "onde", "sobre", "para", "este", "esta",
            "esse", "essa", "principalmente", "extrair", "momentos",
            "esteja", "falando", "clips", "cortes", "video", "fazer", "pedir",
            "quais", "melhor", "mais", "menos", "muito", "pouco", "todos",
            "todas", "cada", "outro", "outra", "outros", "outras",
            "pode", "deve", "quer", "tem", "vai", "vem",
            "somente", "apenas", "tambem", "ainda", "agora", "debate",
            "neste", "nesta", "deste", "desta", "pontos", "fala", "fale",
            "proeminentes", "melhores", "piores", "bons", "ruins",
            "sobressaindo", "nesse", "nessa", "aqui", "ali",
            "sobresaia", "estaja", "respondendo", "perguntas", "mitando",
        }
        common_short = {
            "que", "mas", "nem", "dos", "das", "nos", "nas", "uns", "uma",
            "umas", "ele", "ela", "eles", "elas", "sao", "era", "foi",
            "ser", "ter", "ver", "dar", "vir", "por", "pre", "pos", "sub", "pro",
            "se", "no", "na", "ao", "os", "as", "de", "do", "da", "em", "um",
            "ou", "ja", "so", "ha", "la", "ca", "ai", "ir", "oi", "ah", "eh",
        }
        names = []
        for w in user_context.split():
            clean = re.sub(r'[^\w]', '', w)
            if not clean or len(clean) < 3 or len(clean) > 15:
                continue
            if clean.lower() in stop_words:
                continue
            if clean.isdigit():
                continue
            if clean.lower() in common_short:
                continue
            # Only extract as name if starts with uppercase (proper noun)
            if clean[0].isupper():
                if clean.lower() not in [n.lower() for n in names]:
                    names.append(clean)
        return names

    def _build_sentences(self, segments):
        """Group transcript segments while preserving technical metadata.

        Caps sentence length at 30s, but carries speaker labels, overlap flags,
        timing confidence and source segment ids into every editorial block.
        """
        sentences = []
        current_text = ""
        current_start = None
        current_end = None
        current_segments = []
        last_end = 0
        MAX_SENTENCE_DURATION = 30

        def flush():
            nonlocal current_text, current_start, current_end, current_segments
            if not current_text.strip() or current_start is None or current_end is None:
                current_text = ""
                current_start = None
                current_end = None
                current_segments = []
                return
            speakers = [
                str(item.get("speaker") or "").strip()
                for item in current_segments
                if str(item.get("speaker") or "").strip()
            ]
            unique_speakers = list(dict.fromkeys(speakers))
            confidences = []
            for item in current_segments:
                try:
                    confidences.append(float(item.get("speaker_confidence")))
                except (TypeError, ValueError):
                    continue
            timing_confidences = []
            for item in current_segments:
                try:
                    timing_confidences.append(float(item.get("timing_confidence")))
                except (TypeError, ValueError):
                    continue
            sentences.append({
                "text": current_text.strip(),
                "start": current_start,
                "end": current_end,
                "duration": current_end - current_start,
                "speaker": unique_speakers[0] if len(unique_speakers) == 1 else "",
                "speakers": unique_speakers,
                "speaker_change_detected": len(unique_speakers) > 1,
                "speaker_confidence": min(confidences) if confidences else None,
                "overlap_suspected": any(bool(item.get("overlap_suspected")) for item in current_segments),
                "timing_ambiguous": any(
                    float(item.get("timing_confidence", 1.0) or 1.0) < 0.6
                    for item in current_segments
                    if item.get("timing_confidence") is not None
                ) or any(bool(item.get("overlap_suspected")) for item in current_segments),
                "timing_confidence": min(timing_confidences) if timing_confidences else None,
                "segment_ids": [item.get("id") for item in current_segments if item.get("id") is not None],
            })
            current_text = ""
            current_start = None
            current_end = None
            current_segments = []

        for seg in segments:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
            if start < 0 or end <= start:
                continue
            pause_before = start - last_end if last_end > 0 else 0

            if pause_before > 0.8 and current_text:
                flush()

            if current_start is None:
                current_start = start

            current_text += " " + str(seg.get("text", ""))
            current_end = end
            current_segments.append(seg)
            last_end = end

            current_duration = current_end - current_start
            if current_duration >= MAX_SENTENCE_DURATION:
                flush()
                continue

            text_stripped = current_text.strip()
            if text_stripped and text_stripped[-1] in ".!?" and len(text_stripped.split()) >= 5:
                flush()

        flush()
        return sentences

    # ═══════════════════════════════════════════════════
    # GEMINI — Google Gemini Flash API (most capable)
    # ═══════════════════════════════════════════════════

    def _select_with_gemini(self, sentences, energy_profile, user_context, settings, emit_progress):
        """Use Google Gemini Flash API to select clips — sends FULL transcript at once."""
        api_key = settings.get("gemini_api_key", "").strip()
        if not api_key:
            if emit_progress:
                emit_progress("[Gemini] API key nao configurada.", "warning")
            return []

        transcript_blocks = self._build_transcript_blocks(sentences)
        if not transcript_blocks:
            return []

        system_prompt = self._get_gemini_system_prompt(settings.get("editorial_profile", PROFILE_NAME))
        user_prompt = self._build_gemini_prompt(
            transcript_blocks,
            user_context,
            settings.get("editorial_context"),
        )

        if emit_progress:
            emit_progress(f"[Gemini] Enviando {len(transcript_blocks)} blocos para analise...", "info")

        import time as _time

        # Usa o mesmo modelo Gemini configurado para a análise multimodal.
        # O padrão preserva compatibilidade com instalações existentes; a validação
        # impede que uma configuração corrompida altere o caminho da requisição.
        configured_model = str(settings.get("gemini_model", "gemini-2.5-flash") or "").strip()
        model_name = configured_model if re.fullmatch(r"gemini-[a-z0-9.-]+", configured_model) else "gemini-2.5-flash"
        models_to_try = [model_name]
        last_error = ""

        for model_name in models_to_try:
            for attempt in range(3):
                try:
                    if attempt > 0 and emit_progress:
                        emit_progress(f"[Gemini] Tentativa {attempt + 1} com {model_name}...", "info")

                    response = requests.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                        json={
                            "contents": [{"parts": [{"text": user_prompt}]}],
                            "systemInstruction": {"parts": [{"text": system_prompt}]},
                            "generationConfig": {
                                "temperature": 0.3,
                                "maxOutputTokens": 16384,
                            },
                        },
                        timeout=180,
                    )

                    if response.status_code == 503:
                        # Temporary overload — retry after delay
                        if emit_progress:
                            emit_progress(f"[Gemini] {model_name} sobrecarregado (503). Retentando em {5 * (attempt + 1)}s...", "warning")
                        _time.sleep(5 * (attempt + 1))
                        continue

                    if response.status_code == 429:
                        # Quota exceeded — try next model
                        try:
                            error_msg = response.json().get("error", {}).get("message", "")
                        except Exception:
                            error_msg = response.text[:200]
                        if emit_progress:
                            emit_progress(f"[Gemini] {model_name} quota excedida. Tentando proximo modelo...", "warning")
                        last_error = f"429: {error_msg[:150]}"
                        break  # Break retry loop, try next model

                    if response.status_code == 403:
                        if emit_progress:
                            emit_progress("[Gemini] API key invalida ou sem permissao.", "warning")
                        return []

                    if response.status_code != 200:
                        try:
                            error_msg = response.json().get("error", {}).get("message", "")
                        except Exception:
                            error_msg = response.text[:200]
                        if emit_progress:
                            emit_progress(f"[Gemini] Erro {response.status_code}: {error_msg[:200]}", "warning")
                        last_error = f"{response.status_code}: {error_msg[:150]}"
                        break  # Try next model

                    # Success! Parse the response
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        if emit_progress:
                            emit_progress(f"[Gemini] {model_name} sem resposta da API.", "warning")
                        last_error = "no candidates"
                        break  # Try next model

                    # Gemini 2.5 Flash may return "thinking" parts before actual response
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = ""
                    for part in parts:
                        if part.get("thought"):
                            continue  # Skip thinking parts
                        if "text" in part:
                            text = part["text"]
                            break  # Use the first non-thinking text part

                    if not text:
                        # Fallback: try last part regardless
                        if parts:
                            text = parts[-1].get("text", "")

                    if not text:
                        finish_reason = candidates[0].get("finishReason", "unknown")
                        if emit_progress:
                            emit_progress(f"[Gemini] {model_name} resposta vazia (finishReason: {finish_reason}).", "warning")
                        last_error = f"empty response: {finish_reason}"
                        break  # Try next model

                    if emit_progress:
                        emit_progress(f"[Gemini] Resposta recebida de {model_name} ({len(text)} chars). Parseando...", "info")

                    selections = self._parse_llm_response(text, sentences, transcript_blocks, 0, source="gemini")

                    if not selections:
                        if emit_progress:
                            preview = text[:300].replace("\n", " ")
                            emit_progress(f"[Gemini] JSON parseado mas 0 clips validos. Preview: {preview}...", "warning")
                        last_error = "0 clips parsed"
                        break  # Try next model

                    if emit_progress:
                        emit_progress(f"[Gemini] {model_name} encontrou {len(selections)} clips candidatos!", "info")

                    selections.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
                    return selections

                except requests.exceptions.ConnectionError:
                    if emit_progress:
                        emit_progress("[Gemini] Sem conexao com internet.", "warning")
                    return []
                except requests.exceptions.Timeout:
                    if emit_progress:
                        emit_progress(f"[Gemini] Timeout com {model_name} (>180s).", "warning")
                    last_error = "timeout"
                    break  # Try next model
                except Exception as e:
                    if emit_progress:
                        emit_progress(f"[Gemini] Erro com {model_name}: {str(e)[:200]}", "warning")
                    last_error = str(e)[:150]
                    break  # Try next model

        if emit_progress and last_error:
            emit_progress(f"[Gemini] Todos os modelos falharam. Ultimo erro: {last_error}", "warning")
        return []

    def _get_gemini_system_prompt(self, editorial_profile=PROFILE_NAME):
        political_fragment = ""
        if editorial_profile in (PROFILE_NAME, "politics", "political"):
            political_fragment = "\n\n" + build_political_prompt_fragment()
        return """Voce e um editor de video profissional especialista em selecionar os melhores momentos de debates, entrevistas, podcasts e videos longos para clips curtos (YouTube Shorts, TikTok, Reels).

REGRAS CRITICAS:

1. CONTEXTO COMPLETO OBRIGATORIO:
   Cada clip DEVE fazer sentido para quem NAO viu o video inteiro.
   - Se alguem faz uma PERGUNTA e outro RESPONDE, o clip DEVE incluir a pergunta E a resposta.
   - Se alguem diz "esse impacto", "isso tudo", "essa questao", o clip DEVE incluir o que veio antes para contextualizar.
   - O espectador NUNCA deve se perguntar "impacto de que?", "isso o que?", "quem?".
   - Na duvida, inclua blocos a mais para dar contexto.

2. PENSAMENTO 100% COMPLETO:
   NUNCA corte no meio de uma frase ou raciocinio.
   - O falante DEVE terminar COMPLETAMENTE sua ideia antes do clip acabar.
   - Se ele esta no meio de uma explicacao, CONTINUE incluindo blocos ate ele terminar.
   - O clip ideal termina com o falante fazendo uma pausa natural ou passando a palavra.

3. IDENTIFICACAO DE FALANTES:
   Em debates e entrevistas, identifique quem fala em cada trecho:
   - Jornalistas/mediadores geralmente fazem perguntas e introduzem topicos.
   - Debatedores/convidados respondem e argumentam.
   - Mudancas no conteudo, estilo de fala e tom indicam troca de falante.

4. FILTRAGEM POR FALANTE:
   Se o usuario mencionou um NOME ESPECIFICO (ex: "Kim", "Chico", "reporter"):
   - SOMENTE selecione clips onde ESSA PESSOA e o falante principal.
   - PODE incluir a pergunta de um jornalista como setup (1-2 blocos iniciais), mas o foco DEVE ser a resposta da pessoa mencionada.
   - Se nao tiver certeza de quem esta falando em um trecho, NAO inclua.

5. DURACAO E SELECAO:
   - NAO existe uma duracao fixa: encontre o menor trecho que contenha hook, contexto e payoff completos.
   - Quanto mais curto, melhor, desde que o espectador entenda quem, o que e por que sem ter visto o video inteiro.
   - Use 180 segundos como teto preferencial, nao como limite absoluto. Ultrapasse-o somente quando encurtar destruir a pergunta, a resposta, a prova, o argumento ou a conclusao.
   - Nunca corte uma ideia apenas para caber em uma duracao. Um clip excepcionalmente contextualizado pode ser mais longo e deve ser marcado como excecao.
   - Selecione clips de PARTES DIFERENTES do video (diversidade temporal).
   - Prefira momentos com: opiniao forte, dado concreto, confronto, emocao, humor, reacao, historia, bastidor ou conversa descontraida.
   - Nao force tudo como politico. Escolha uma familia editorial: politico, humor, reacao, bastidor, descontraido ou conversa.

6. AVALIACAO HONESTA — use a escala INTEIRA, nao de A para tudo:
   - hook: A = Primeiros segundos prendem atencao imediatamente. B = Inicio razoavel. C = Inicio confuso ou fraco.
   - flow: A = Contexto 100% completo e pensamento totalmente terminado. B = Quase completo, falta algo menor. C = Falta contexto ou cortado no meio.
   - value: A = Conteudo forte, impactante, polemico, engajante. B = Conteudo razoavel. C = Conteudo generico/fraco.
   - energy: A = Tom intenso, animado, emocionante. B = Tom normal. C = Monotono.
   Um clip medio DEVE receber B ou C, NAO A.

FORMATO DE RESPOSTA — retorne APENAS um array JSON valido:
[
  {
    "blocks": [3, 4, 5],
    "title": "Titulo descritivo que resume o conteudo do clip",
    "speaker": "Nome da pessoa principal falando",
    "reason": "Por que este clip e relevante para o pedido do usuario",
    "editorial_family": "politico|humor|reacao|bastidor|descontraido|conversa",
    "hook": "A",
    "flow": "A",
    "value": "B",
    "energy": "A"
  }
]""" + political_fragment

    def _build_gemini_prompt(self, blocks, user_context, editorial_context=None):
        """Build prompt with deterministic interview context plus the transcript."""
        lines = []
        for b in blocks:
            timestamp = f"[{self._format_time(b['start'])} - {self._format_time(b['end'])}]"
            lines.append(f"BLOCO {b['index']}: {timestamp} ({b['duration']}s)\n{b['text']}\n")

        transcript_text = "\n".join(lines)

        context_instruction = ""
        if user_context:
            names = self._extract_names_from_context(user_context)
            if names:
                names_str = ", ".join(names)
                context_instruction = f"""

INSTRUCAO DO USUARIO: "{user_context}"

ATENCAO: O usuario mencionou nomes especificos: {names_str}.
SOMENTE selecione clips onde uma dessas pessoas esta falando como falante principal.
A pergunta de outro pode ser incluida como setup, mas o FOCO deve ser a fala de {names_str}.
Se o nome nao aparece literalmente na transcricao, identifique pela posicao no debate (quem defende qual argumento)."""
            else:
                context_instruction = f"""

INSTRUCAO DO USUARIO: "{user_context}"
Selecione clips que melhor atendam a esse pedido."""

        editorial_instruction = ""
        if editorial_context:
            windows = editorial_context.get("interview_windows", [])[:8]
            qa = editorial_context.get("qa_candidates", [])[:12]
            chapters = editorial_context.get("editorial_chapters", [])[:24]
            editorial_instruction = f"""

PRÉ-ANÁLISE EDITORIAL DETERMINÍSTICA:
{editorial_context.get('description', '')}
Foco padrão: Renan Santos/MBL. Confiança inicial de participante: {editorial_context.get('participant_confidence', 0):.0%}.
Janelas prováveis de entrevista: {windows}.
Candidatos pergunta–resposta detectados: {qa}.
Mapa de capítulos temporais: {chapters}.
Respeite os capítulos como blocos editoriais contíguos. Não combine blocos de capítulos separados sem uma ponte de fala clara. Quando a seleção for uma pergunta–resposta, inclua o capítulo inteiro ou a ponte completa; se houver dúvida sobre locutor ou sobreposição, reduza a confiança ou rejeite.
"""

        num_clips = min(self.max_clips, max(5, len(blocks) // 4))

        return f"""Analise esta transcricao completa e selecione os {num_clips} MELHORES momentos para clips curtos.
{editorial_instruction}
{context_instruction}

TRANSCRICAO COMPLETA ({len(blocks)} blocos, {self._format_time(blocks[-1]['end'])} de video):

{transcript_text}

Combine apenas os blocos consecutivos necessarios para formar o menor clip com CONTEXTO COMPLETO.
Lembre: cada clip deve ter inicio (contexto/pergunta), meio (desenvolvimento) e fim (conclusao do raciocinio); nao encurte nem estenda artificialmente.
Retorne APENAS o array JSON. Nenhum texto antes ou depois."""

    # ═══════════════════════════════════════════════════
    # OLLAMA — Local LLM (offline, free)
    # ═══════════════════════════════════════════════════

    def _select_with_llm(self, sentences, energy_profile, user_context, settings, emit_progress):
        """Use Ollama to intelligently select the best clips."""
        ollama_url = settings.get("ollama_url", "http://localhost:11434")
        ollama_model = settings.get("ollama_model", "llama3.2:3b")

        transcript_blocks = self._build_transcript_blocks(sentences)
        if not transcript_blocks:
            return []

        all_selections = []
        chunk_size = 25

        for chunk_idx in range(0, len(transcript_blocks), chunk_size):
            chunk = transcript_blocks[chunk_idx:chunk_idx + chunk_size]
            prompt = self._build_llm_prompt(
                chunk,
                user_context,
                chunk_idx,
                len(transcript_blocks),
                settings.get("editorial_context"),
            )

            if emit_progress:
                emit_progress(
                    f"Analisando trecho {chunk_idx // chunk_size + 1}/"
                    f"{math.ceil(len(transcript_blocks) / chunk_size)} com IA..."
                )

            try:
                response = requests.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": ollama_model,
                        "prompt": prompt,
                        "system": self._get_system_prompt(settings.get("editorial_profile", PROFILE_NAME)),
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 4096},
                    },
                    timeout=600,
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "")

                selections = self._parse_llm_response(text, sentences, transcript_blocks, chunk_idx, source="llm")
                if not selections and text and emit_progress:
                    # Ollama responded but JSON was unparseable - log for debug
                    preview = text[:150].replace("\n", " ")
                    emit_progress(f"[Ollama] Resposta invalida (nao e JSON): {preview}...", "warning")
                all_selections.extend(selections)

            except requests.exceptions.ConnectionError:
                if emit_progress:
                    emit_progress("Ollama nao disponivel.")
                return []
            except Exception as e:
                if emit_progress:
                    emit_progress(f"Erro na IA: {str(e)[:200]}")
                return []

        all_selections.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
        return all_selections

    def _get_system_prompt(self, editorial_profile=PROFILE_NAME):
        """System prompt for Ollama — simpler and more direct for small models (3B)."""
        political_fragment = ""
        if editorial_profile in (PROFILE_NAME, "politics", "political"):
            political_fragment = "\n\n" + build_political_prompt_fragment()
        return """Voce seleciona os melhores trechos de uma transcricao de video para clips curtos.

REGRAS OBRIGATORIAS:
1. CONTEXTO: Cada clip DEVE ter contexto completo. Se ha uma pergunta, inclua a pergunta E a resposta juntas.
2. COMPLETO: O falante DEVE terminar sua frase e seu raciocinio. NUNCA corte no meio.
3. FALANTE: Se o usuario pediu clips de uma pessoa especifica, SOMENTE inclua momentos dessa pessoa falando.
4. DIVERSIDADE: Selecione clips de partes DIFERENTES do video.
5. DURACAO: Nao ha faixa fixa. Prefira o menor trecho autossuficiente; 180 segundos e apenas um teto preferencial. So ultrapasse esse teto se o contexto e o payoff exigirem.
6. NOTAS: A = excelente (raro), B = bom (normal), C = fraco. NAO de A para tudo, seja critico.

FORMATO — retorne APENAS JSON valido:
[
  {
    "blocks": [3, 4, 5],
    "title": "Titulo descritivo do clip",
    "reason": "Por que este clip e bom",
    "hook": "A",
    "flow": "A",
    "value": "B",
    "energy": "B"
  }
]""" + political_fragment

    def _build_llm_prompt(self, blocks, user_context, chunk_offset, total_blocks, editorial_context=None):
        """Build local prompt with the same interview signals as the online path."""
        lines = []
        for b in blocks:
            timestamp = f"[{self._format_time(b['start'])} - {self._format_time(b['end'])}]"
            lines.append(f"BLOCO {b['index']}: {timestamp} ({b['duration']}s)\n{b['text']}\n")

        transcript_text = "\n".join(lines)

        context_instruction = ""
        if user_context:
            names = self._extract_names_from_context(user_context)
            if names:
                names_str = ", ".join(names)
                context_instruction = f"""

INSTRUCAO DO USUARIO: "{user_context}"
IMPORTANTE: SOMENTE selecione clips onde {names_str} esta falando. Clips de outras pessoas devem ser EXCLUIDOS."""
            else:
                context_instruction = f"""

INSTRUCAO DO USUARIO: "{user_context}"
Selecione clips que atendam a esse pedido."""

        editorial_instruction = ""
        if editorial_context:
            chapters = editorial_context.get("editorial_chapters", [])[:16]
            editorial_instruction = (
                f"\nPRÉ-ANÁLISE: {editorial_context.get('description', '')}\n"
                f"CAPÍTULOS EDITORIAIS: {chapters}\n"
                "Não atravesse capítulos desconectados; preserve perguntas e respostas no mesmo capítulo.\n"
            )

        num_clips = min(self.max_clips, max(3, len(blocks) // 3))
        return f"""Selecione os {num_clips} MELHORES momentos para clips curtos.
{editorial_instruction}
{context_instruction}

TRANSCRICAO (blocos {chunk_offset} a {chunk_offset + len(blocks) - 1} de {total_blocks} total):

{transcript_text}

Combine blocos consecutivos apenas ate o menor trecho com contexto completo e conclusao.
Retorne APENAS o JSON.
"""

    def _build_transcript_blocks(self, sentences):
        """Group sentences into the units the selector will choose between.

        On an interview these are the seams of the conversation. Everywhere else
        they are timed, as they always were.
        """
        seams = self._conversation_seams(sentences)
        if seams:
            return self._blocks_between_seams(sentences, seams)
        return self._timed_transcript_blocks(sentences)

    def _conversation_seams(self, sentences):
        """Where the interviewer takes the floor, when the source is a talk.

        Blocks used to be cut by a stopwatch — every eighteen to thirty seconds,
        wherever that landed. That is why a 31-minute sabatina produced candidates
        of twenty seconds each and why the editor saw clips that "catch the middle
        and the end, never the question": a window that starts on a clock has no
        reason to start where an idea does. The repair afterwards could only move
        an edge a few seconds; it could not turn a tile into an exchange.
        """
        turns = detect_interviewer_turns(sentences)
        span = max((float(item.get("end", 0) or 0) for item in sentences or []), default=0.0)
        if not looks_like_an_interview(turns, span):
            return []
        return [turn["start_s"] for turn in turns if not turn["interjection"]]

    def _blocks_between_seams(self, sentences, seams):
        """One block per exchange, split only when it outgrows a clip.

        A stretch longer than the preferred maximum is still one subject, but no
        single clip can carry it, so it is divided at sentence boundaries rather
        than left for the ranker to truncate arbitrarily.
        """
        ordered = sorted(sentences, key=lambda item: float(item.get("start", 0) or 0))
        marks = sorted({round(seam, 3) for seam in seams})
        groups: list[list] = []
        current: list = []
        for sentence in ordered:
            start = float(sentence.get("start", 0) or 0)
            if current and any(abs(start - mark) < 0.05 or (current[-1]["start"] < mark <= start) for mark in marks):
                groups.append(current)
                current = []
            current.append(sentence)
        if current:
            groups.append(current)

        blocks = []
        for group in groups:
            for piece in self._split_to_clip_length(group):
                if not piece:
                    continue
                text = " ".join(str(item.get("text") or "") for item in piece)
                blocks.append(self._make_editorial_block(
                    len(blocks), piece[0]["start"], piece[-1]["end"], text, piece
                ))
        return blocks

    def _split_to_clip_length(self, group):
        """Cut an over-long exchange into pieces a clip can actually hold."""
        if not group:
            return []
        span = float(group[-1]["end"]) - float(group[0]["start"])
        if span <= self.preferred_max_duration:
            return [group]
        pieces, current = [], []
        for sentence in group:
            current.append(sentence)
            if float(sentence["end"]) - float(current[0]["start"]) >= self.preferred_max_duration:
                pieces.append(current)
                current = []
        if current:
            # A tail too short to stand alone belongs to the piece before it.
            if pieces and float(current[-1]["end"]) - float(current[0]["start"]) < self.min_duration:
                pieces[-1].extend(current)
            else:
                pieces.append(current)
        return pieces

    def _timed_transcript_blocks(self, sentences):
        """Group sentences into compact editorial blocks for analysis."""
        blocks = []
        current_block_sentences = []
        current_start = None
        current_duration = 0

        for sent in sentences:
            if current_start is None:
                current_start = sent["start"]

            current_block_sentences.append(sent)
            current_duration = sent["end"] - current_start

            # Use smaller editorial blocks so a complete idea can remain short.
            # The selector may still join blocks when the context requires it.
            if current_duration >= 30 or (sent["text"].strip()[-1:] in ".!?" and current_duration >= 18):
                block_text = " ".join(s["text"] for s in current_block_sentences)
                blocks.append(self._make_editorial_block(
                    len(blocks), current_start, sent["end"], block_text, current_block_sentences
                ))
                current_block_sentences = []
                current_start = None
                current_duration = 0

        if current_block_sentences:
            block_text = " ".join(s["text"] for s in current_block_sentences)
            blocks.append(self._make_editorial_block(
                len(blocks), current_start, current_block_sentences[-1]["end"],
                block_text, current_block_sentences
            ))

        return blocks

    def _make_editorial_block(self, index, start, end, block_text, sentences):
        speakers = []
        for sentence in sentences:
            for speaker in sentence.get("speakers", []):
                if speaker and speaker not in speakers:
                    speakers.append(speaker)
        return {
            "index": index,
            "start": start,
            "end": end,
            "duration": round(end - start, 1),
            "text": block_text.strip(),
            "sentences": sentences.copy(),
            "speaker": speakers[0] if len(speakers) == 1 else "",
            "speakers": speakers,
            "speaker_change_detected": len(speakers) > 1,
            "overlap_suspected": any(bool(sentence.get("overlap_suspected")) for sentence in sentences),
            "speaker_turn_valid": not any(bool(sentence.get("overlap_suspected")) for sentence in sentences),
            "timing_ambiguous": any(bool(sentence.get("timing_ambiguous")) for sentence in sentences),
            "timing_confidence": min(
                [float(sentence["timing_confidence"]) for sentence in sentences if sentence.get("timing_confidence") is not None]
                or [1.0]
            ),
        }

    def _parse_llm_response(self, response_text, sentences, all_blocks, chunk_offset, source="llm"):
        """Parse LLM/Gemini JSON response into clip data with timestamps."""
        try:
            json_str = response_text.strip()
            # Extract JSON from potential markdown code blocks
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                code_parts = json_str.split("```")
                if len(code_parts) >= 3:
                    json_str = code_parts[1]

            # Try to find JSON array in the response
            start_idx = json_str.find("[")
            end_idx = json_str.rfind("]") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = json_str[start_idx:end_idx]

            # Fix common JSON issues from LLMs
            # Replace smart quotes with regular quotes
            json_str = json_str.replace("\u201c", '"').replace("\u201d", '"')
            json_str = json_str.replace("\u2018", "'").replace("\u2019", "'")
            # Remove trailing commas before ] or }
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

            selections = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            # Try a more aggressive approach: find each {...} object
            try:
                objects = re.findall(r'\{[^{}]+\}', response_text)
                selections = []
                for obj_str in objects:
                    obj_str = obj_str.replace("\u201c", '"').replace("\u201d", '"')
                    obj_str = re.sub(r',\s*([}\]])', r'\1', obj_str)
                    try:
                        obj = json.loads(obj_str)
                        if "blocks" in obj:
                            selections.append(obj)
                    except (json.JSONDecodeError, ValueError):
                        continue
                if not selections:
                    return []
            except Exception:
                return []

        clips = []
        for sel in selections:
            if not isinstance(sel, dict):
                continue

            raw_indices = sel.get("blocks", [])
            if not isinstance(raw_indices, (list, tuple)) or not raw_indices:
                continue
            try:
                block_indices = [int(index) for index in raw_indices]
            except (TypeError, ValueError):
                continue
            if len(set(block_indices)) != len(block_indices):
                continue

            zero_based_valid = all(0 <= index < len(all_blocks) for index in block_indices)
            one_based_valid = all(1 <= index <= len(all_blocks) for index in block_indices)
            # Our prompt exposes zero-based `BLOCO` indices. Only switch to
            # one-based when zero-based mapping is impossible, avoiding the old
            # silent off-by-one error for responses such as [1, 2].
            if not zero_based_valid and one_based_valid:
                block_indices = [index - 1 for index in block_indices]
            elif not zero_based_valid:
                continue

            ordered_indices = sorted(block_indices)
            if ordered_indices != list(range(ordered_indices[0], ordered_indices[-1] + 1)):
                # A model that skips a block skipped context; do not publish it.
                continue
            block_indices = ordered_indices
            valid_blocks = [all_blocks[index] for index in block_indices]
            if not valid_blocks:
                continue

            metadata = {
                "overlap_suspected": any(bool(block.get("overlap_suspected")) for block in valid_blocks),
                "timing_ambiguous": any(bool(block.get("timing_ambiguous")) for block in valid_blocks),
                "speaker_turn_valid": all(block.get("speaker_turn_valid", True) is not False for block in valid_blocks),
                "timing_confidence": min(
                    [float(block.get("timing_confidence")) for block in valid_blocks if block.get("timing_confidence") is not None]
                    or [1.0]
                ),
            }
            preliminary_text = " ".join(block["text"] for block in valid_blocks)
            preliminary_flags = self._editorial_flags(preliminary_text, metadata)
            if preliminary_flags["starts_mid_sentence"] and block_indices[0] > 0:
                previous = all_blocks[block_indices[0] - 1]
                gap = float(valid_blocks[0]["start"]) - float(previous["end"])
                joined_duration = float(valid_blocks[-1]["end"]) - float(previous["start"])
                if gap <= 2.5 and joined_duration <= self.max_duration:
                    valid_blocks.insert(0, previous)
                    block_indices.insert(0, block_indices[0] - 1)
                    metadata["overlap_suspected"] = metadata["overlap_suspected"] or bool(previous.get("overlap_suspected"))
                    metadata["timing_ambiguous"] = metadata["timing_ambiguous"] or bool(previous.get("timing_ambiguous"))

            clip_start = valid_blocks[0]["start"]
            clip_end = valid_blocks[-1]["end"]
            clip_duration = clip_end - clip_start

            # Validate duration. The technical ceiling prevents malformed
            # responses, while the editorial preference remains soft.
            if clip_duration < self.min_duration:
                continue
            if clip_duration > self.max_duration:
                clip_end = clip_start + self.max_duration
                clip_duration = self.max_duration

            clip_text = " ".join(b["text"] for b in valid_blocks)
            technical_flags = self._editorial_flags(clip_text, metadata)
            if technical_flags["overlap_suspected"] or technical_flags["timing_ambiguous"]:
                # Ambiguous timing remains reviewable but should not be treated
                # as a clean candidate by the model response parser.
                sel["technical_review_required"] = True

            # Score scale: A=90, B=55, C=25 (wide spread for real differentiation)
            grade_to_score = {"A": 90, "B": 55, "C": 25}
            hook_score = grade_to_score.get(sel.get("hook", "B"), 55)
            flow_score = grade_to_score.get(sel.get("flow", "B"), 55)
            value_score = grade_to_score.get(sel.get("value", "B"), 55)
            energy_score = grade_to_score.get(sel.get("energy", "B"), 55)

            # Weighted: flow (context completeness) gets highest weight
            viral_score = int(
                hook_score * 0.20 +
                flow_score * 0.35 +
                value_score * 0.25 +
                energy_score * 0.20
            )

            clips.append({
                **technical_flags,
                "start": clip_start,
                "end": clip_end,
                "duration": round(clip_duration, 3),
                "text": clip_text,
                "title": sel.get("title", ""),
                "reason": sel.get("reason", ""),
                "speaker": sel.get("speaker", ""),
                "editorial_family": sel.get("editorial_family", ""),
                "viral_score": viral_score,
                "has_hook": sel.get("hook", "C") in ("A", "B"),
                "breakdown": {
                    "hook": sel.get("hook", "B"),
                    "flow": sel.get("flow", "B"),
                    "value": sel.get("value", "B"),
                    "energy": sel.get("energy", "B"),
                },
                "source": source,
                "duration_preference": self._duration_label(clip_duration, sel),
            })

        return clips

    # ═══════════════════════════════════════════════════
    # NLP — Keyword-based fallback (always available)
    # ═══════════════════════════════════════════════════

    def _select_with_nlp(self, sentences, energy_profile, user_context, emit_progress, editorial_context=None):
        """NLP-based fallback when no AI backend is available."""
        if emit_progress:
            emit_progress("[NLP] Construindo clips com analise por palavras-chave...")

        blocks = self._build_transcript_blocks(sentences)
        if not blocks:
            return []

        context_data = self._prepare_context_matching(user_context) if user_context else None

        scored_blocks = []
        for block in blocks:
            score = self._nlp_score_block(block, user_context, energy_profile, context_data, editorial_context)
            scored_blocks.append((block, score))

        clips = self._build_clips_from_scored_blocks(
            scored_blocks,
            context_data,
            editorial_context=editorial_context,
        )

        # SPEAKER FILTERING: When names are specified, EXCLUDE clips without them
        if context_data and context_data["names"]:
            target_names = context_data["names"]
            filtered = []
            for clip in clips:
                clip_text_lower = clip["text"].lower()
                has_target = any(name in clip_text_lower for name in target_names)
                if has_target:
                    filtered.append(clip)
            # If filtering removes too many, keep at least some clips
            if len(filtered) >= 3:
                clips = filtered
            elif emit_progress:
                emit_progress(f"[NLP] Poucos clips com '{', '.join(target_names)}' na transcricao. Mostrando melhores disponiveis.", "warning")

        clips.sort(key=lambda x: x["viral_score"], reverse=True)

        if emit_progress:
            emit_progress(f"[NLP] Encontrou {len(clips)} clips candidatos")

        return clips

    def _select_with_campaign_hub_guidance(self, sentences, settings, emit_progress=None):
        """Turn an authorized Campaign Hub snapshot into bounded clip proposals."""
        snapshot = settings.get("campaign_hub_snapshot") if isinstance(settings, dict) else None
        if snapshot is None and isinstance(settings, dict) and settings.get("campaign_hub_snapshot_path"):
            try:
                from .campaign_hub import load_snapshot
                snapshot = load_snapshot(settings.get("campaign_hub_snapshot_path"))
            except (ImportError, OSError, ValueError):
                snapshot = None
        if not snapshot or not sentences:
            return []
        try:
            from .campaign_hub_guidance import build_campaign_hub_guided_seeds
            seeds = build_campaign_hub_guided_seeds(
                sentences,
                snapshot,
                account=settings.get("campaign_hub_account") or snapshot.get("default_account"),
                limit=max(1, min(30, self.max_clips * 2)),
                media_duration=self._media_duration(settings),
            )
        except (ImportError, OSError, TypeError, ValueError) as exc:
            if emit_progress:
                emit_progress(f"[Campaign Hub] Seeds guiadas indisponíveis; mantendo seleção local: {str(exc)[:140]}", "warning")
            return []
        proposals = []
        for seed in seeds:
            proposal = self._build_campaign_hub_proposal(sentences, seed)
            if proposal:
                proposals.append(proposal)
        proposals.sort(key=lambda item: (
            bool((item.get("campaign_hub") or {}).get("gates", {}).get("context_complete")),
            float(item.get("viral_score", 0) or 0),
            float(item.get("campaign_hub", {}).get("confidence", 0) or 0),
        ), reverse=True)
        return proposals[:self.max_clips]

    def _trim_opening_fragment(self, clips, emit_progress=None):
        """Start a clip at a sentence instead of in the middle of one.

        The existing repair expands backwards by a whole block, which only helps
        when the missing context sits immediately before and the gap is short. It
        cannot fix the common case: the chosen window opens on the tail of a
        sentence whose beginning belongs to the previous subject. There the
        editor does not want more material, but less — the clip should simply
        start a few seconds later, on the first sentence that stands on its own.

        Start times inside a caption line are interpolated by character position,
        because captions carry one timestamp per line and several sentences can
        share it. Speech rate is close enough to uniform within a line for this
        to land on the right words; the estimate is never allowed to move the
        start by more than ``MAX_OPENING_TRIM_S``.
        """
        for clip in clips or []:
            text = str(clip.get("text") or "")
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            if not text or end - start <= self.min_duration:
                continue
            # A caption that opens in lower case is continuing a sentence that
            # started earlier. Names and acronyms legitimately open a clip, so
            # only the case of the very first character is consulted.
            first = text.lstrip()[:1]
            if not first or not first.islower():
                continue

            offset = self._first_standalone_sentence_offset(text)
            if offset <= 0:
                continue
            shift = (end - start) * (offset / len(text))
            if shift <= 0.4 or shift > self.MAX_OPENING_TRIM_S:
                continue
            if (end - start) - shift < self.min_duration:
                continue

            clip["start"] = round(start + shift, 3)
            clip["duration"] = round(end - clip["start"], 3)
            clip["text"] = text[offset:].strip()
            clip["opening_trimmed_s"] = round(shift, 3)
            if emit_progress:
                emit_progress(
                    f"[Início] Corte {start:.0f}s começava no meio da frase; "
                    f"avançado {shift:.1f}s para abrir em \"{clip['text'][:48]}...\".",
                    "info",
                )
        return clips

    def _close_open_question(self, clips, sentences, emit_progress=None):
        """Never end a clip on the question and leave the answer outside it.

        A window that closes on the interviewer's question is the most frustrating
        shape a clip can have: it sets up an expectation the viewer cannot satisfy.
        The gates already record ``question_answer_complete``, but they only mark
        the candidate — by then the boundary is fixed. Here the boundary itself is
        moved, taking in whatever follows until the answer has actually started.
        """
        if not sentences:
            return clips
        ordered = sorted(sentences, key=lambda item: float(item.get("start", 0) or 0))
        for clip in clips or []:
            text = str(clip.get("text") or "").strip()
            end = float(clip.get("end", 0) or 0)
            start = float(clip.get("start", 0) or 0)
            if not text.endswith("?") or end <= start:
                continue

            answer_words, new_end = 0, end
            for sentence in ordered:
                sentence_start = float(sentence.get("start", 0) or 0)
                sentence_end = float(sentence.get("end", 0) or 0)
                if sentence_end <= end:
                    continue
                if sentence_start > end + 3.0 and answer_words == 0:
                    # Nothing follows closely enough to be the answer to this
                    # question; extending would splice unrelated material.
                    break
                if sentence_end - start > self.max_duration:
                    break
                answer_words += len(str(sentence.get("text") or "").split())
                new_end = sentence_end
                if answer_words >= self.MIN_ANSWER_WORDS:
                    break

            if answer_words >= self.MIN_ANSWER_WORDS and new_end > end:
                clip["end"] = round(new_end, 3)
                clip["duration"] = round(clip["end"] - start, 3)
                clip["answer_extended_s"] = round(new_end - end, 3)
                if emit_progress:
                    emit_progress(
                        f"[Pergunta] Corte terminava na pergunta; estendido {new_end - end:.1f}s "
                        "para incluir o começo da resposta.",
                        "info",
                    )
        return clips

    def _align_to_interview_turns(self, clips, sentences, emit_progress=None):
        """Put every boundary of an interview on a seam of the conversation.

        Measured against the fourteen blocks the Acervo published for a sabatina
        of 31 minutes, not one of the sixteen clips this selector rendered began
        within two seconds of a real seam, and six of them ran across one. That is
        what the editor was reporting: a clip that keeps going after the reporter
        has moved on, and a clip that stops before the answer arrives at its
        point — which on that source turned an argument about extreme poverty
        into its opposite.

        The repair is not to re-select. The selector's window says how much
        material the idea needs and that judgement is kept; only the two edges
        move, onto the nearest moment the interviewer holds the floor. A clip may
        run through a short interruption, because the guest resumes the same
        argument straight after, but it may never cross a turn that changes the
        subject: material from two subjects is not one clip.

        Sources that are not interviews — a live, a speech — produce no turns and
        leave every boundary untouched.
        """
        if not sentences:
            return clips

        turns = detect_interviewer_turns(sentences)
        span = max((float(item.get("end", 0) or 0) for item in sentences), default=0.0)
        if not looks_like_an_interview(turns, span):
            return clips

        # A clip may end where the interviewer speaks — but not on an aside the
        # guest talks straight through, or it stops in the middle of the answer.
        seams = [turn["start_s"] for turn in turns if not turn["interjection"]]
        majors = [turn["start_s"] for turn in turns if turn["major"]]
        if not seams:
            return clips

        self._candidate_diagnostics.update({
            "interview_turns": len(turns),
            "interview_seams": len(seams),
            "interview_major_turns": len(majors),
        })

        kept, dropped = [], 0
        for clip in clips or []:
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            if end <= start:
                kept.append(clip)
                continue
            original_start, original_end = start, end

            # Opening on the tail of the previous answer is the complaint the
            # editor phrased as "it started in the middle of a sentence": the
            # clip carries three words that belong to the subject before it.
            opening = [
                turn for turn in turns
                if not turn["interjection"]
                and turn["start_s"] <= start < turn["end_s"]
                and start - turn["start_s"] <= self.MAX_TURN_START_SNAP_S
            ]
            if opening:
                start = opening[-1]["start_s"]

            # A window that opens a few seconds before the next question is
            # carrying the tail of the previous answer — the "it started in the
            # middle of a sentence" complaint. There is no clip in those seconds,
            # so the clip starts at the question instead.
            ahead = [seam for seam in majors if start < seam < start + self.min_duration]
            if ahead:
                start = ahead[0]

            # A subject change inside the window is not negotiable: the clip ends
            # there even if that costs it the slot.
            # Half of what the selector asked for. Below it the window is no
            # longer the idea that was chosen, it is a leftover.
            viable = max(self.min_duration, (original_end - original_start) * 0.5)

            crossed = [seam for seam in majors if start + 1.0 < seam < end - 1.0]
            if crossed:
                # What is left of a window cut back at a change of subject is a
                # stub: the idea it was chosen for lives on the other side of the
                # seam. Rendering it would fill a slot with nothing, and there is
                # no minimum number of clips to reach.
                end = crossed[0]
                if end - start < viable:
                    dropped += 1
                    continue
            else:
                seam_end = self._nearest_seam_end(start, end, seams)
                # A seam far to the left of the chosen end belongs to some
                # follow-up early in the answer; snapping there would throw away
                # most of the material instead of tidying its edge.
                if seam_end < original_end and seam_end - start < viable:
                    seam_end = original_end
                end = seam_end
                if end - start < self.min_duration:
                    dropped += 1
                    continue

            if abs(end - original_end) > self.MAX_TURN_END_SHIFT_S:
                end = original_end

            self._mark_local_qa_bridge(clip, start, end, turns, sentences)

            if abs(start - original_start) < 0.05 and abs(end - original_end) < 0.05:
                kept.append(clip)
                continue

            clip["start"] = round(start, 3)
            clip["end"] = round(end, 3)
            clip["duration"] = round(end - start, 3)
            clip["turn_aligned"] = {
                "start_shift_s": round(start - original_start, 2),
                "end_shift_s": round(end - original_end, 2),
                "crossed_subject_change": bool(crossed),
            }
            rebuilt = self._text_between(sentences, start, end)
            if rebuilt:
                clip["text"] = rebuilt
            kept.append(clip)

        if emit_progress and (dropped or len(kept) != len(clips or [])):
            emit_progress(
                f"[Entrevista] {len(turns)} turnos do entrevistador reconhecidos; "
                f"bordas ajustadas para não cortar resposta pela metade. "
                f"{dropped} candidato(s) descartado(s) por atravessar mudança de assunto.",
                "info",
            )
        elif emit_progress and turns:
            emit_progress(
                f"[Entrevista] {len(turns)} turnos do entrevistador reconhecidos; "
                "bordas dos cortes alinhadas às perguntas.",
                "info",
            )
        return kept

    def _mark_local_qa_bridge(self, clip, start, end, turns, sentences):
        """Record that the clip carries a question and the answer to it.

        The editorial gate refuses to render a clip where a question is heard and
        the bridge to its answer was never validated — the right rule, and the one
        that made this run unusable. Validation depended on the clip matching a
        question-and-answer window computed in the context stage, within two and a
        half seconds on both edges and covering 72% of it. A window chosen by the
        selector almost never lines up with one of those, so on a 31-minute
        sabatina fourteen of nineteen candidates were held back and the five that
        rendered were the only ones containing no question at all. The editor read
        exactly that back: clips that "catch the middle and the end, never the
        question".

        The bridge does not need a precomputed window to be evident. A clip that
        opens on the interviewer taking the floor and then carries enough of the
        guest answering *is* the bridge, and the turns say so from the transcript
        alone. This is recorded separately from the chapter evidence so the
        context stage stays authoritative whenever it did produce a window.
        """
        inside = [turn for turn in turns if start - 1.0 <= turn["start_s"] < end]
        if not inside:
            return
        answer_words = 0
        after = inside[0]["end_s"]
        for sentence in sentences or []:
            sentence_start = float(sentence.get("start", 0) or 0)
            if not after <= sentence_start < end:
                continue
            text = str(sentence.get("text") or "")
            if is_interviewer_sentence(text):
                continue
            answer_words += len(text.split())
        if answer_words < self.MIN_ANSWER_WORDS:
            return
        clip["qa_bridge_local"] = True
        clip["qa_boundary_basis_local"] = "turnos_do_entrevistador"
        clip["qa_bridge_answer_words"] = answer_words

    def _nearest_seam_end(self, start, end, seams):
        """Where the clip should stop, given where the selector wanted to stop.

        The selector's end is treated as an estimate of how much material the
        idea needs, and the nearest seam to it wins — on either side. Preferring
        the seam *before* the estimate sounds safer and is not: a clip that runs
        through two follow-up questions would be cut back to the first of them
        and lose most of the answer. Moving forward is what completes an argument
        that was stopping one sentence early.
        """
        usable = min(self.preferred_max_duration, self.max_duration)
        reachable = [seam for seam in seams if start + self.min_duration <= seam <= start + usable]
        if not reachable:
            return end
        return min(reachable, key=lambda seam: abs(seam - end))

    @staticmethod
    def _text_between(sentences, start, end):
        """The transcript actually contained in a window, after it was moved."""
        parts = [
            str(item.get("text") or "").strip()
            for item in sorted(sentences or [], key=lambda entry: float(entry.get("start", 0) or 0))
            if float(item.get("start", 0) or 0) >= start - 0.25
            and float(item.get("end", 0) or 0) <= end + 0.25
        ]
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def _first_standalone_sentence_offset(text):
        """Character offset of the first sentence long enough to open a clip.

        Short fragments left over from the previous idea — "Não atua." — are
        skipped as well, because opening on them reads as badly as opening
        mid-sentence.
        """
        offset = 0
        for _ in range(4):
            match = re.search(r"[.!?]\s+", text[offset:])
            if not match:
                return 0
            offset += match.end()
            remainder = text[offset:]
            if len(remainder.split()) < 8:
                return 0
            first_sentence = re.split(r"[.!?]", remainder, maxsplit=1)[0]
            if len(first_sentence.split()) >= 4:
                return offset
        return 0

    def _attach_local_topic_context(self, clips, sentences, emit_progress=None):
        """Give each candidate the subject of the stretch it belongs to.

        The Acervo turns a source into thematic blocks and every downstream
        judgement leans on them, but they only exist for sources it already
        labelled. This reads the same structure out of the transcript, so a
        recording made minutes ago arrives with subjects instead of a flat wall
        of sentences.

        It never overwrites Acervo evidence. A block the Acervo endorsed is a
        QA-gated fact; a unit found here is Furia's own reading, and travels
        under its own key so the two are never confused.
        """
        if not clips or not sentences:
            return clips
        try:
            from .topic_segmenter import segment_transcript
            units = segment_transcript(sentences)
        except (ImportError, TypeError, ValueError):
            return clips
        if not units:
            return clips

        tagged = 0
        for clip in clips:
            if clip.get("campaign_hub_block"):
                continue
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            if end <= start:
                continue
            best, best_overlap = None, 0.0
            for unit in units:
                overlap = max(0.0, min(end, unit["end_s"]) - max(start, unit["start_s"]))
                if overlap > best_overlap:
                    best, best_overlap = unit, overlap
            if not best or best_overlap / (end - start) < 0.5:
                continue
            clip["topic_block"] = {
                "start_s": best["start_s"],
                "end_s": best["end_s"],
                "duration_s": best["duration_s"],
                "topic_terms": best["topic_terms"],
                "carries_subject": best["carries_subject"],
                "non_content_cues": best["non_content_cues"],
                "coverage_of_candidate": round(best_overlap / (end - start), 3),
                "provenance": "furia_topic_segmenter",
                "evidence_only": True,
            }
            tagged += 1
            if not best["carries_subject"]:
                clip["review_required"] = True
                reasons = list(clip.get("review_reasons") or [])
                reasons.append("trecho sem assunto desenvolvido segundo a leitura local")
                clip["review_reasons"] = reasons

        if tagged:
            self._candidate_diagnostics["local_topic_units"] = len(units)
            self._candidate_diagnostics["clips_with_local_topic"] = tagged
            if emit_progress:
                emit_progress(
                    f"[Temas] A fonte foi lida em {len(units)} blocos temáticos pelo próprio Furia, "
                    f"sem depender do Acervo; {tagged} candidato(s) receberam o assunto do trecho.",
                    "info",
                )
        return clips

    def _attach_block_evidence(self, clips, settings):
        """Give every candidate the editorial context of the block it sits in.

        Only candidates born from a Campaign Hub seed carried provenance, so the
        rest reached the reviewer anonymous: no title, no topic, no risk flag and
        — worst of all — no indication of who is speaking. A candidate that lands
        inside a QA-gated block inherits what the Acervo already established about
        that stretch, which is evidence, never approval: nothing here raises a
        score or clears a gate.
        """
        snapshot = settings.get("campaign_hub_snapshot") if isinstance(settings, dict) else None
        records = snapshot.get("records") if isinstance(snapshot, dict) else None
        blocks = [item for item in (records or {}).get("blocks") or [] if isinstance(item, dict)]
        if not blocks or not clips:
            return clips

        for clip in clips:
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            if end <= start:
                continue
            best, best_overlap = None, 0.0
            for block in blocks:
                try:
                    block_start = float(_block_field(block, "start_s", "startS"))
                    block_end = float(_block_field(block, "end_s", "endS"))
                except (TypeError, ValueError):
                    continue
                overlap = max(0.0, min(end, block_end) - max(start, block_start))
                if overlap > best_overlap:
                    best, best_overlap = block, overlap
            if not best or best_overlap / (end - start) < 0.5:
                continue

            renan_speaking = _block_field(best, "renan_speaking", "renanSpeaking")
            # ``false`` from the Acervo means "not confirmed as Renan", which
            # covers both a third party and an unidentified voice. Neither may be
            # published as Renan, so both land on the same review verdict.
            speaker_status = "renan_confirmado" if renan_speaking is True else (
                "nao_confirmado" if renan_speaking is None else "terceiro_ou_indeterminado"
            )
            risk_flags = list(_block_field(best, "risk_flags", "riskFlags") or [])
            gate_warnings = list(_block_field(best, "gate_warnings", "gateWarnings") or [])
            clip["campaign_hub_block"] = {
                "block_id": best.get("id") or best.get("blockId"),
                "title": best.get("title"),
                "summary": best.get("summary"),
                "trigger_question": _block_field(best, "trigger_question", "triggerQuestion"),
                "topics": list(best.get("topics") or [])[:20],
                "category": best.get("category"),
                "density_rank": _block_field(best, "density_rank", "densityRank"),
                "self_contained_rank": _block_field(best, "self_contained_rank", "selfContainedRank"),
                "self_contained_reason": _block_field(best, "self_contained_reason", "selfContainedReason"),
                "renan_speaking": renan_speaking,
                "speaker_status": speaker_status,
                "speakers_note": _block_field(best, "speakers_note", "speakersNote"),
                "risk_flags": risk_flags,
                "gate_warnings": gate_warnings,
                "trust_tier": _block_field(best, "trust_tier", "trustTier"),
                "coverage_of_candidate": round(best_overlap / (end - start), 3),
                "evidence_only": True,
            }
            if speaker_status != "renan_confirmado" or risk_flags:
                clip["review_required"] = True
                reasons = list(clip.get("review_reasons") or [])
                if speaker_status != "renan_confirmado":
                    reasons.append("locutor não confirmado como Renan pelo Acervo")
                if risk_flags:
                    reasons.append(f"riscos sinalizados: {', '.join(risk_flags[:4])}")
                clip["review_reasons"] = reasons
        return clips

    @staticmethod
    def _labelled_non_content_regions(settings):
        """Intervals the authorized snapshot marks as carrying no content.

        Each region arrives with a reason — an unintelligible stretch, an
        isolated fragment — so this is labelled evidence of absence, not missing
        data. Without a snapshot the list is empty and nothing is filtered.
        """
        snapshot = settings.get("campaign_hub_snapshot") if isinstance(settings, dict) else None
        records = snapshot.get("records") if isinstance(snapshot, dict) else None
        regions = []
        for region in (records or {}).get("ignored_regions") or []:
            if not isinstance(region, dict):
                continue
            try:
                start = float(region.get("start_s"))
                end = float(region.get("end_s"))
            except (TypeError, ValueError):
                continue
            if end > start:
                regions.append((start, end, str(region.get("reason") or "")))
        return regions

    def _drop_labelled_non_content(self, clips, settings, sentences=None, emit_progress=None):
        """Remove candidates that mostly cover material that is not editorial.

        A candidate is only dropped when the majority of its window sits inside
        such a region: merely touching one at the edge is normal, because a real
        idea can start right after an unintelligible stretch. Candidates are a
        budget — every slot spent here is a slot a real cut does not get.

        The authorized snapshot is preferred when present, but it only exists for
        sources the Acervo already labelled. Without it the same judgement is made
        locally from the transcript, so a fresh recording is not left defenceless
        against its own sponsor read, opening titles and sign-off.
        """
        regions = self._labelled_non_content_regions(settings)
        source = "acervo"
        if not regions and sentences:
            try:
                from .non_content_detector import detect_non_content_regions
                regions = [
                    (float(item["start_s"]), float(item["end_s"]), str(item.get("reason") or ""))
                    for item in detect_non_content_regions(sentences)
                ]
                source = "local"
            except (ImportError, KeyError, TypeError, ValueError):
                regions = []
        if not regions or not clips:
            return clips
        kept, dropped = [], []
        for clip in clips:
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            span = end - start
            if span <= 0:
                kept.append(clip)
                continue
            covered = sum(
                max(0.0, min(end, region_end) - max(start, region_start))
                for region_start, region_end, _ in regions
            )
            if covered / span >= self.NON_CONTENT_DROP_RATIO:
                dropped.append(clip)
            else:
                kept.append(clip)
        if dropped:
            self._candidate_diagnostics["labelled_non_content_dropped"] = len(dropped)
            self._candidate_diagnostics["non_content_source"] = source
            self._candidate_diagnostics["non_content_regions"] = len(regions)
            if emit_progress:
                origem = (
                    "que o Acervo marcou como sem conteúdo editorial"
                    if source == "acervo"
                    else "reconhecidos localmente como propaganda, abertura, bastidor ou encerramento"
                )
                emit_progress(
                    f"[Descarte] {len(dropped)} candidato(s) removido(s) por cair em trechos {origem}; "
                    "o orçamento foi liberado para fala aproveitável.",
                    "info",
                )
                for clip in dropped[:8]:
                    emit_progress(
                        f"[Descarte] {float(clip.get('start', 0)):.0f}s-{float(clip.get('end', 0)):.0f}s: "
                        f"{str(clip.get('text') or '')[:70]}",
                        "info",
                    )
        return kept

    @staticmethod
    def _media_duration(settings):
        """Length of the file being processed, as measured by the caller.

        The snapshot only knows how long the original source is. When the editor
        works on a block that was downloaded out of a long live, that declared
        length is the wrong ruler, so the job must hand over the duration it
        probed from the local media.
        """
        if not isinstance(settings, dict):
            return None
        for key in ("media_duration", "video_duration", "source_duration"):
            try:
                duration = float(settings.get(key))
            except (TypeError, ValueError):
                continue
            if duration > 0:
                return duration
        return None

    def _build_campaign_hub_proposal(self, sentences, seed):
        """Expand one temporal/semantic seed to the smallest complete local window."""
        if not seed or not sentences:
            return None
        seed_start = float(seed.get("start", 0) or 0)
        seed_end = float(seed.get("end", seed_start) or seed_start)
        overlapping = [
            index for index, sentence in enumerate(sentences)
            if float(sentence.get("end", 0) or 0) > seed_start
            and float(sentence.get("start", 0) or 0) < seed_end
        ]
        if not overlapping:
            nearest = min(
                range(len(sentences)),
                key=lambda index: abs(float(sentences[index].get("start", 0) or 0) - seed_start),
            )
            # A seed landing in a short silence or just past the last sentence is
            # still the same moment, so the nearest sentence is a fair anchor. A
            # seed that misses the transcript by minutes is not: it means the seed
            # and the transcript are on different timelines, and snapping it would
            # publish an unrelated window carrying Campaign Hub provenance. Every
            # such seed would also collapse onto the same edge sentence, turning
            # distinct highlights into duplicate proposals.
            gap = max(
                float(sentences[nearest].get("start", 0) or 0) - seed_end,
                seed_start - float(sentences[nearest].get("end", 0) or 0),
                0.0,
            )
            if gap > self.MAX_SEED_ANCHOR_GAP_S:
                return None
            overlapping = [nearest]
        start_index = min(overlapping)
        end_index = max(overlapping)

        def window_text():
            return " ".join(str(sentences[index].get("text", "") or "").strip() for index in range(start_index, end_index + 1)).strip()

        def window_metadata():
            window = sentences[start_index:end_index + 1]
            return {
                "overlap_suspected": any(bool(item.get("overlap_suspected")) for item in window),
                "timing_ambiguous": any(bool(item.get("timing_ambiguous")) for item in window),
                "speaker_turn_valid": all(item.get("speaker_turn_valid", True) is not False for item in window),
                "timing_confidence": min(
                    [float(item.get("timing_confidence")) for item in window if item.get("timing_confidence") is not None]
                    or [1.0]
                ),
            }

        # Recover the opening question/antecedent when the Chub highlight starts
        # inside a response. The expansion is bounded by the same technical ceiling.
        while start_index > 0:
            current_text = window_text()
            current_flags = self._editorial_flags(current_text, window_metadata())
            previous = sentences[start_index - 1]
            gap = float(sentences[start_index].get("start", 0) or 0) - float(previous.get("end", 0) or 0)
            joined_duration = float(sentences[end_index].get("end", 0) or 0) - float(previous.get("start", 0) or 0)
            needs_opening = (
                current_flags.get("starts_mid_sentence")
                or current_flags.get("starts_with_context_reference")
                or (seed.get("trigger_question") and not current_flags.get("question_detected"))
            )
            if not needs_opening or gap > 2.5 or joined_duration > self.max_duration:
                break
            start_index -= 1

        # Add enough response for the seed to become a complete, reviewable idea.
        while end_index < len(sentences) - 1:
            current_text = window_text()
            current_flags = self._editorial_flags(current_text, window_metadata())
            duration = float(sentences[end_index].get("end", 0) or 0) - float(sentences[start_index].get("start", 0) or 0)
            if duration >= self.min_duration and current_flags.get("context_complete") and current_flags.get("payoff_complete"):
                break
            next_sentence = sentences[end_index + 1]
            joined_duration = float(next_sentence.get("end", 0) or 0) - float(sentences[start_index].get("start", 0) or 0)
            if joined_duration > self.max_duration:
                break
            end_index += 1

        text = window_text()
        if not text:
            return None
        metadata = window_metadata()
        flags = self._editorial_flags(text, metadata)
        start = float(sentences[start_index].get("start", seed_start) or seed_start)
        end = float(sentences[end_index].get("end", seed_end) or seed_end)
        duration = max(0.0, end - start)
        if duration <= 0:
            return None
        chub_confidence = float(seed.get("confidence", 0.0) or 0.0)
        gate_warnings = list(seed.get("gate_warnings") or [])
        if seed.get("renan_speaking") is False:
            gate_warnings.append("Campaign Hub indica outro locutor; confirme o foco editorial")
        speaker_gate = "pass" if seed.get("renan_speaking") is True and metadata.get("speaker_turn_valid") else "review_required"
        trust_tier = str(seed.get("trust_tier") or "unknown").lower()
        gates = {
            "context_complete": bool(flags.get("context_complete")),
            "payoff_complete": bool(flags.get("payoff_complete")),
            "speaker_gate": speaker_gate,
            "timing_gate": "review_required" if metadata.get("timing_ambiguous") else "pass",
            "risk_gate": "review_required" if seed.get("risk_flags") else "pass",
            "technical_gate": "review_required" if metadata.get("overlap_suspected") else "pass",
            "provenance_gate": "pass" if trust_tier == "qa_gated" else "review_required",
            "warning_gate": "review_required" if gate_warnings else "pass",
        }
        review_required = any(value == "review_required" for value in gates.values())
        score = 46.0 + (chub_confidence * 22.0)
        score += 16.0 if flags.get("context_complete") else -12.0
        score += 10.0 if flags.get("payoff_complete") else -10.0
        score += 5.0 if seed.get("source_kind") == "highlight" else 0.0
        density_rank = seed.get("density_rank")
        self_contained_rank = seed.get("self_contained_rank")
        if density_rank is not None:
            score += min(8.0, max(0.0, float(density_rank)) * 0.08)
        if self_contained_rank is not None:
            score += min(8.0, max(0.0, float(self_contained_rank)) * 0.08)
        if trust_tier == "qa_gated":
            score += 3.0
        score -= min(12.0, len(gate_warnings) * 3.0)
        score = max(0.0, min(100.0, score))
        title = str(seed.get("title") or "").strip() or self._generate_simple_title(text)
        reason_parts = [
            f"seed {seed.get('source_kind', 'Campaign Hub')} {seed.get('seed_id')}",
            "janela expandida até contexto e payoff" if flags.get("context_complete") and flags.get("payoff_complete") else "janela requer revisão de completude",
        ]
        return {
            **flags,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(duration, 3),
            "text": text,
            "title": title[:160],
            "reason": "; ".join(reason_parts),
            "viral_score": int(round(score)),
            "has_hook": bool(flags.get("context_complete")),
            "breakdown": {
                "hook": "A" if score >= 75 else ("B" if score >= 55 else "C"),
                "flow": "A" if flags.get("context_complete") else "C",
                "value": "A" if chub_confidence >= 0.8 else "B",
                "energy": "B",
            },
            "source": "campaign_hub_guided",
            "duration_preference": self._duration_label(duration, {"flow": "A" if flags.get("context_complete") else "B"}),
            "review_required": review_required,
            "campaign_hub": {
                "seed_id": seed.get("seed_id"),
                "block_id": seed.get("block_id"),
                "highlight_id": seed.get("highlight_id"),
                "source_kind": seed.get("source_kind"),
                "seed_text": seed.get("seed_text"),
                "summary": seed.get("summary"),
                "trigger_question": seed.get("trigger_question"),
                "topics": seed.get("topics") or [],
                "timeline_mapping": seed.get("timeline_mapping"),
                "absolute_start": seed.get("absolute_start"),
                "absolute_end": seed.get("absolute_end"),
                "confidence": seed.get("confidence"),
                "density_rank": seed.get("density_rank"),
                "self_contained_rank": seed.get("self_contained_rank"),
                "self_contained_reason": seed.get("self_contained_reason"),
                "possible_cuts": seed.get("possible_cuts", 0),
                "content_class": seed.get("content_class"),
                "labeler_version": seed.get("labeler_version"),
                "prompt_version": seed.get("prompt_version"),
                "trust_tier": seed.get("trust_tier"),
                "risk_flags": seed.get("risk_flags") or [],
                "gate_warnings": list(dict.fromkeys(gate_warnings)),
                "gates": gates,
                "review_required": review_required,
                "provenance": seed.get("provenance") or {},
            },
            "technical_gate_status": "review" if review_required else "pass",
            "technical_gate_reasons": list(dict.fromkeys(gate_warnings)),
        }

    def _prepare_context_matching(self, user_context):
        """Pre-process user context for efficient matching."""
        text_lower = user_context.lower()

        all_words = [w.strip('.,;:!?"()') for w in text_lower.split()]
        context_words = [w for w in all_words if len(w) > 2]

        stop_words_pt = {
            "quero", "quando", "como", "onde", "sobre", "para", "este", "esta",
            "esse", "essa", "principalmente", "extrair", "momentos", "onde",
            "esteja", "falando", "clips", "cortes", "video", "fazer", "pedir",
            "quais", "melhor", "mais", "menos", "muito", "pouco", "todos",
            "todas", "cada", "outro", "outra", "outros", "outras", "aqui",
            "ali", "isso", "isto", "aquilo", "dele", "dela", "deles", "delas",
            "nele", "nela", "neles", "nelas", "meu", "minha", "seu", "sua",
            "nosso", "nossa", "vosso", "vossa", "com", "sem", "por", "entre",
            "contra", "desde", "ate", "apos", "antes", "depois", "durante",
            "pode", "deve", "quer", "tem", "vai", "vem", "esta", "estao",
            "foram", "seria", "seria", "fosse", "sendo", "sido", "tendo",
            "tendo", "faz", "fez", "faria", "somente", "apenas", "tambem",
            "ainda", "agora", "logo", "sempre", "nunca", "talvez", "sim",
            "nao", "bem", "mal", "assim", "entao", "pois", "porque", "como",
            "sobresaia", "estaja", "respondendo", "perguntas", "mitando",
            "debate", "neste", "nesta", "deste", "desta",
        }

        names = []
        for w in user_context.split():
            clean = w.strip('.,;:!?"()')
            if not clean or len(clean) < 3 or len(clean) > 12:
                continue
            clean_lower = clean.lower()
            if clean_lower in stop_words_pt:
                continue
            if clean.isdigit():
                continue
            # Only treat as name if starts with uppercase
            if clean[0].isupper():
                common_short = {"que", "mas", "nem", "dos", "das", "nos", "nas",
                                "uns", "uma", "umas", "ele", "ela", "eles", "elas",
                                "sao", "era", "foi", "ser", "ter", "ver", "dar",
                                "vir", "por", "pre", "pos", "sub", "pro",
                                "se", "no", "na", "ao", "os", "as", "de", "do",
                                "da", "em", "um", "ou", "ja", "so", "ha", "la"}
                if clean_lower not in common_short:
                    if clean_lower not in names:
                        names.append(clean_lower)

        phrases = []
        parts = re.split(r'[,;.!?]', text_lower)
        for part in parts:
            part = part.strip()
            words_in_part = part.split()
            if len(words_in_part) >= 3:
                phrases.append(part)
            numeric_phrases = re.findall(r'\d+[\s\w]*\d+[\s\w]*', part)
            for np_match in numeric_phrases:
                if len(np_match.split()) >= 2:
                    phrases.append(np_match.strip())

        return {
            "words": context_words,
            "names": names,
            "phrases": phrases,
            "raw": text_lower,
        }

    def _nlp_score_block(self, block, user_context, energy_profile, context_data=None, editorial_context=None):
        """Score a block using NLP heuristics."""
        text = block["text"].lower()
        score = 40

        # Hook detection
        first_words = " ".join(text.split()[:15])
        hook_patterns = [
            r"voce\s+sabia", r"presta\s+atencao", r"olha\s+isso",
            r"a\s+verdade\s+e", r"ninguem\s+te", r"cuidado",
            r"absurdo", r"vergonha", r"mentira", r"bomba",
            r"urgente", r"inacreditavel", r"chocante",
            r"vou\s+te\s+falar", r"isso\s+e\s+muito",
            r"nao\s+pode", r"tem\s+que",
        ]
        hook_score = 0
        for pattern in hook_patterns:
            if re.search(pattern, first_words):
                hook_score += 12
        hook_score = min(20, hook_score)

        # Emotional intensity
        emotional_words = [
            "absurdo", "vergonha", "mentira", "corrupto", "criminoso",
            "covarde", "traidor", "hipocrita", "lixo", "revolta",
            "liberdade", "patriota", "coragem", "vitoria", "luta",
            "impressionante", "incrivel", "surreal", "chocante",
            "inacreditavel", "povo", "nacao", "brasil",
        ]
        word_list = text.split()
        emotional_count = sum(1 for w in word_list if any(ew in w for ew in emotional_words))
        emotional_density = emotional_count / max(len(word_list), 1)
        emotional_score = min(20, emotional_density * 200)

        # Punctuation energy
        excl_count = block["text"].count("!")
        quest_count = block["text"].count("?")
        punct_score = min(10, excl_count * 4 + quest_count * 2)

        # Filler word penalty
        filler_count = 0
        for fw in FILLER_WORDS_PT:
            if " " in fw:
                filler_count += text.count(fw)
            else:
                filler_count += sum(1 for w in word_list if w == fw)
        filler_density = filler_count / max(len(word_list), 1)
        filler_penalty = min(15, filler_density * 150)

        # User context relevance
        context_score = 0
        if context_data:
            context_score = self._compute_context_score(text, context_data)

        # Duration is a soft preference: shorter complete blocks are rewarded,
        # while long blocks remain eligible when their context is stronger.
        duration = block["duration"]
        duration_score = self._duration_score(duration)
        dossier_score = self._dossier_context_score(block, editorial_context)

        # Sentence completeness
        if block["text"].strip()[-1:] in ".!?":
            completeness_score = 10
        else:
            completeness_score = -15

        total = (score + hook_score + emotional_score + punct_score
                 + context_score + duration_score + completeness_score
                 + dossier_score - filler_penalty)
        return max(0, min(100, total))

    def _dossier_context_score(self, block, editorial_context):
        """Use the local dossier as a bounded tie-breaker for offline selection."""
        if not isinstance(editorial_context, dict):
            return 0.0
        start = float(block.get("start", 0) or 0)
        end = float(block.get("end", start) or start)
        best_hook = 0.0
        for hook in editorial_context.get("hook_candidates", []) or []:
            hook_start = float(hook.get("start", 0) or 0)
            hook_end = float(hook.get("end", hook_start) or hook_start)
            overlap = max(0.0, min(end, hook_end) - max(start, hook_start))
            if overlap > 0:
                best_hook = max(best_hook, min(8.0, float(hook.get("score", 0) or 0) * 0.08))
        qa_bonus = 0.0
        qa_context_gap = 0.0
        for candidate in editorial_context.get("qa_candidates", []) or []:
            qa_start = float(candidate.get("start", 0) or 0)
            qa_end = float(candidate.get("end", qa_start) or qa_start)
            overlap = max(0.0, min(end, qa_end) - max(start, qa_start))
            if overlap <= 0:
                continue
            needs_question = bool(candidate.get("needs_question"))
            preserves_question = start <= qa_start + 2.5
            preserves_response = end >= qa_end - 2.5
            if needs_question and not preserves_question:
                # Do not reward a response-only window as a complete Q&A clip.
                qa_context_gap = max(qa_context_gap, 2.5)
                continue
            if needs_question and not preserves_response:
                qa_context_gap = max(qa_context_gap, 1.5)
                continue
            qa_bonus = 3.0 if candidate.get("speaker_boundary") else 1.5
            break
        return round(max(-4.0, min(10.0, best_hook + qa_bonus - qa_context_gap)), 2)

    def _duration_score(self, duration):
        duration = max(0.0, float(duration or 0.0))
        if duration < self.min_duration:
            return -8
        if duration <= 30:
            return 10
        if duration <= 60:
            return 7
        if duration <= 120:
            return 2
        if duration <= self.preferred_max_duration:
            return -1
        return -5

    def _duration_label(self, duration, selection):
        if duration <= self.preferred_max_duration:
            return "curto_preferencial"
        flow = str(selection.get("flow", "B")).upper()
        if flow == "A":
            return "excecao_contextual"
        return "longo_para_revisao"

    def _compute_context_score(self, text, context_data):
        """Compute context relevance score."""
        score = 0

        for phrase in context_data["phrases"]:
            if phrase in text:
                score += 20

        for name in context_data["names"]:
            if name in text:
                score += 25

        for cw in context_data["words"]:
            if len(cw) > 1 and cw in text:
                score += 5

        name_bonus = sum(25 for n in context_data["names"] if n in text)
        if name_bonus > 0:
            return min(80, score)
        return min(60, score)

    def _editorial_flags(self, text, metadata=None):
        """Return conservative, explainable gates shared by every backend."""
        raw = str(text or "").strip()
        metadata = metadata if isinstance(metadata, dict) else {}
        normalized = raw.lower()
        words = re.findall(r"[\wÀ-ÿ-]+", normalized)
        first_word = words[0] if words else ""
        continuation_starters = {item.lower() for item in CONTINUATION_STARTERS_PT}
        starts_mid_sentence = first_word in continuation_starters
        first_two_words = " ".join(words[:2]) if len(words) >= 2 else first_word
        reference_starters = {item.lower() for item in CONTEXT_REFERENCE_STARTERS_PT}
        starts_with_context_reference = first_word in reference_starters or first_two_words in reference_starters
        has_question = "?" in raw or first_word in {"como", "por", "porque", "qual", "quais", "quem", "quando", "onde"}
        question_index = raw.find("?")
        response_text = raw[question_index + 1:] if question_index >= 0 else ""
        response_words = len(re.findall(r"[\wÀ-ÿ-]+", response_text))
        response_closed = response_text.strip().endswith((".", "!", "?"))
        question_answer_complete = bool(
            has_question and response_words >= 8 and (response_closed or response_words >= 14)
        )
        # An explicit question mark creates a Q&A contract: a candidate must
        # preserve enough response text to be self-contained. Bare
        # interrogative openings remain a soft signal because automatic
        # captions often omit punctuation.
        question_requires_answer = "?" in raw
        normalized_words = set(re.findall(r"[\wÀ-ÿ-]+", normalized))
        has_evidence = bool(normalized_words & {term.lower() for term in EVIDENCE_TERMS_PT})
        ends_closed = raw.endswith((".", "!", "?"))
        tail_words = re.findall(r"[\wÀ-ÿ-]+", normalized)
        tail = tail_words[-2:] if tail_words else []
        weak_payoff_ending = bool(tail and tail[-1] in WEAK_PAYOFF_ENDINGS_PT)
        if len(tail) >= 2 and " ".join(tail[-2:]) in WEAK_PAYOFF_ENDINGS_PT:
            weak_payoff_ending = True
        cliffhanger = any(pattern in normalized[-220:] for pattern in ("em breve", "depois eu", "na proxima", "fique ligado", "vou mostrar"))
        payoff_complete = bool(ends_closed and not cliffhanger and not weak_payoff_ending)
        overlap_suspected = bool(metadata.get("overlap_suspected"))
        timing_ambiguous = bool(metadata.get("timing_ambiguous"))
        speaker_turn_valid = metadata.get("speaker_turn_valid")
        context_complete = bool(
            not starts_mid_sentence
            and not starts_with_context_reference
            and payoff_complete
            and (not question_requires_answer or question_answer_complete)
            and len(words) >= 12
            and not overlap_suspected
            and not timing_ambiguous
            and speaker_turn_valid is not False
        )
        return {
            "starts_mid_sentence": starts_mid_sentence,
            "starts_with_context_reference": starts_with_context_reference,
            "question_detected": has_question,
            "question_requires_answer": question_requires_answer,
            "question_answer_complete": question_answer_complete,
            "evidence_present": has_evidence,
            "payoff_complete": payoff_complete,
            "payoff_weak_ending": weak_payoff_ending,
            "context_complete": context_complete,
            "qa_bridge": bool(
                question_answer_complete
                and not overlap_suspected
                and not timing_ambiguous
                and speaker_turn_valid is not False
            ),
            "speaker_turn_valid": speaker_turn_valid,
            "overlap_suspected": overlap_suspected,
            "timing_ambiguous": timing_ambiguous,
            "timing_confidence": metadata.get("timing_confidence"),
        }

    def _build_clips_from_scored_blocks(self, scored_blocks, context_data=None, editorial_context=None):
        """Build clips by joining only the blocks needed for context and payoff.
        Enforces the technical ceiling on all clips without imposing a fixed length.
        """
        clips = []
        used_indices = set()

        sorted_by_score = sorted(enumerate(scored_blocks), key=lambda x: x[1][1], reverse=True)

        for start_idx, (start_block, start_score) in sorted_by_score:
            if start_idx in used_indices:
                continue

            clip_blocks = [start_block]
            clip_duration = start_block["duration"]
            clip_end_idx = start_idx

            # Recover the smallest contiguous opening window that makes the
            # candidate self-contained. This handles chained references such as
            # “e isso” → “isso” and a response whose question is in the previous
            # block, without pulling unrelated material from the next topic.
            original_start_idx = start_idx
            qa_start = None
            qa_end = None
            if isinstance(editorial_context, dict):
                for candidate in editorial_context.get("qa_candidates", []) or []:
                    candidate_start = float(candidate.get("start", 0) or 0)
                    candidate_end = float(candidate.get("end", candidate_start) or candidate_start)
                    if candidate.get("needs_question") and float(start_block.get("start", 0)) >= candidate_start and float(start_block.get("start", 0)) <= candidate_end:
                        qa_start, qa_end = candidate_start, candidate_end
                        break

            while start_idx > 0 and (start_idx - 1) not in used_indices:
                opening_flags = self._editorial_flags(clip_blocks[0].get("text", ""), clip_blocks[0])
                previous_block = scored_blocks[start_idx - 1][0]
                gap = float(clip_blocks[0].get("start", 0)) - float(previous_block.get("end", 0))
                joined_duration = float(clip_blocks[-1].get("end", 0)) - float(previous_block.get("start", 0))
                needs_previous = (
                    opening_flags.get("starts_mid_sentence")
                    or opening_flags.get("starts_with_context_reference")
                    or (qa_start is not None and float(previous_block.get("start", 0)) <= qa_start + 2.5)
                )
                if not needs_previous or gap > 2.5 or joined_duration > self.max_duration:
                    break
                clip_blocks.insert(0, previous_block)
                clip_duration = joined_duration
                start_idx -= 1

            preferred_stop = min(float(self.target_duration or 45), 30.0)
            clip_text_preview = " ".join(b["text"] for b in clip_blocks)
            preview_flags = self._editorial_flags(
                clip_text_preview,
                {
                    "speaker_turn_valid": all(b.get("speaker_turn_valid", True) is not False for b in clip_blocks),
                },
            )
            start_is_complete = (
                clip_duration >= self.min_duration
                and preview_flags.get("context_complete")
                and preview_flags.get("payoff_complete")
            )
            if not start_is_complete:
                for next_idx in range(start_idx + 1, len(scored_blocks)):
                    if next_idx in used_indices:
                        break
                    next_block = scored_blocks[next_idx][0]
                    new_duration = next_block["end"] - clip_blocks[0]["start"]

                    if new_duration > self.max_duration:
                        break

                    clip_blocks.append(next_block)
                    clip_duration = new_duration

                    # Stop at the first complete, self-contained payoff. A
                    # complete short idea wins over the old soft target duration.
                    natural_end = " ".join(b["text"] for b in clip_blocks)
                    natural_flags = self._editorial_flags(
                        natural_end,
                        {
                            "speaker_turn_valid": all(b.get("speaker_turn_valid", True) is not False for b in clip_blocks),
                        },
                    )
                    if (
                        clip_duration >= self.min_duration
                        and natural_flags.get("context_complete")
                        and natural_flags.get("payoff_complete")
                    ):
                        clip_end_idx = next_idx
                        break

            if clip_duration < self.min_duration:
                continue

            for idx in range(start_idx, clip_end_idx + 1):
                used_indices.add(idx)

            clip_text = " ".join(b["text"] for b in clip_blocks)
            clip_start = clip_blocks[0]["start"]
            clip_end = clip_blocks[-1]["end"]
            clip_flags = self._editorial_flags(
                clip_text,
                {
                    "overlap_suspected": any(bool(block.get("overlap_suspected")) for block in clip_blocks),
                    "timing_ambiguous": any(bool(block.get("timing_ambiguous")) for block in clip_blocks),
                    "speaker_turn_valid": all(block.get("speaker_turn_valid", True) is not False for block in clip_blocks),
                    "timing_confidence": min(
                        [float(block.get("timing_confidence")) for block in clip_blocks if block.get("timing_confidence") is not None]
                        or [1.0]
                    ),
                },
            )

            # ENFORCE max_duration — truncate if clip exceeds limit
            if clip_end - clip_start > self.max_duration:
                clip_end = clip_start + self.max_duration
                clip_duration = self.max_duration
            else:
                clip_duration = clip_end - clip_start

            avg_score = sum(scored_blocks[i][1] for i in range(start_idx, clip_end_idx + 1)) / (clip_end_idx - start_idx + 1)

            hook_grade = "A" if start_score > 75 else ("B" if start_score > 50 else "C")
            flow_grade = "A" if clip_flags["context_complete"] else ("B" if clip_flags["payoff_complete"] else "C")
            value_grade = "A" if avg_score > 70 else ("B" if avg_score > 50 else "C")
            energy_grade = "B"

            viral_score = int(avg_score)
            if not clip_flags["context_complete"]:
                viral_score -= 10
            if clip_flags["starts_mid_sentence"]:
                viral_score -= 12
            if clip_flags["question_detected"] and not clip_flags["qa_bridge"]:
                viral_score -= 10
            if not clip_flags["payoff_complete"]:
                viral_score -= 12
            if clip_flags["overlap_suspected"]:
                viral_score -= 16
            if clip_flags["timing_ambiguous"]:
                viral_score -= 8
            viral_score = max(0, min(100, viral_score))

            title = self._generate_simple_title(clip_text)

            reason = ""
            if context_data and context_data["names"]:
                matched_names = [n for n in context_data["names"] if n in clip_text.lower()]
                if matched_names:
                    reason = f"Contem mencao a: {', '.join(matched_names)}"

            clips.append({
                **clip_flags,
                "start": clip_start,
                "end": clip_end,
                "duration": round(clip_duration, 3),
                "text": clip_text,
                "title": title,
                "reason": reason,
                "viral_score": viral_score,
                "has_hook": hook_grade in ("A", "B"),
                "breakdown": {
                    "hook": hook_grade,
                    "flow": flow_grade,
                    "value": value_grade,
                    "energy": energy_grade,
                },
                "source": "nlp",
                "duration_preference": self._duration_label(clip_duration, {"flow": flow_grade}),
            })

        return clips

    def _generate_simple_title(self, text):
        """Generate a basic title from the clip text."""
        for end_char in ["!", "?", "."]:
            idx = text.find(end_char)
            if 10 < idx < 80:
                title = text[:idx + 1].strip()
                return title
        words = text.split()[:8]
        title = " ".join(words)
        if len(title) > 60:
            title = title[:57] + "..."
        return title

    # ═══════════════════════════════════════════════════
    # Post-processing helpers
    # ═══════════════════════════════════════════════════

    def _adjust_to_scene_boundaries(self, clips, scene_changes):
        """Adjust clip start/end to nearest scene boundary to avoid cutting mid-transition."""
        if not scene_changes or len(scene_changes) < 2:
            return clips

        adjusted = []
        for clip in clips:
            best_start = clip["start"]
            best_end = clip["end"]

            for sc in scene_changes:
                if abs(sc - clip["start"]) < 2.0:
                    best_start = sc
                    break

            for sc in scene_changes:
                if abs(sc - clip["end"]) < 2.0:
                    best_end = sc
                    break

            clip["start"] = best_start
            clip["end"] = best_end
            clip["duration"] = round(best_end - best_start, 3)

            if clip["duration"] >= self.min_duration:
                adjusted.append(clip)

        return adjusted

    def _remove_previous_fingerprints(self, clips):
        """Drop candidates that were already exported for this source video."""
        previous = self._previous_clip_fingerprints
        if not previous or not clips:
            return clips
        selected = []
        for clip in clips:
            repeated = None
            for old in previous:
                try:
                    old_start = float(old.get("start", 0) or 0)
                    old_end = float(old.get("end", 0) or 0)
                    old_duration = float(old.get("duration", old_end - old_start) or (old_end - old_start))
                    new_start = float(clip.get("start", 0) or 0)
                    new_end = float(clip.get("end", 0) or 0)
                except (TypeError, ValueError):
                    continue
                old_clip = {"start": old_start, "end": old_end, "duration": max(old_duration, 0.001)}
                new_clip = {"start": new_start, "end": new_end, "duration": max(new_end - new_start, 0.001)}
                overlap = self._calculate_overlap(new_clip, old_clip)
                text_similarity = self._text_similarity(clip.get("text", ""), old.get("text", ""))
                boundary_match = abs(new_start - old_start) <= 4.0 and abs(new_end - old_end) <= 6.0
                if overlap >= 0.45 or boundary_match or (text_similarity >= 0.86 and abs(new_start - old_start) <= 30.0):
                    repeated = old
                    break
            if repeated is None:
                selected.append(clip)
                continue
            self._candidate_diagnostics["previous_discarded_count"] = int(
                self._candidate_diagnostics.get("previous_discarded_count", 0) or 0
            ) + 1
            status = str(repeated.get("review_status") or "").lower()
            if status == "approved":
                self._candidate_diagnostics["previous_discarded_approved"] += 1
            elif status == "rejected":
                self._candidate_diagnostics["previous_discarded_rejected"] += 1
        return selected

    def _remove_overlaps(self, clips):
        """Remove temporal overlaps and near-duplicate candidates deterministically."""
        if not clips:
            return []

        def origin_priority(clip):
            origin = str(clip.get("candidate_origin") or "")
            return 0 if origin == "local_fallback" else 1

        ordered = sorted(
            clips,
            key=lambda clip: (
                origin_priority(clip),
                float(clip.get("editorial_potential_score", clip.get("viral_score", 0)) or 0),
                float(clip.get("confidence", 0) or 0),
                -float(clip.get("duration", 0) or 0),
            ),
            reverse=True,
        )
        selected = []
        for clip in ordered:
            duplicate = False
            duplicate_reason = ""
            for existing in selected:
                overlap = self._calculate_overlap(clip, existing)
                text_similarity = self._text_similarity(clip.get("text", ""), existing.get("text", ""))
                if overlap > 0.30:
                    duplicate = True
                    duplicate_reason = "overlap"
                    break
                # Repeated wording in adjacent candidate windows is usually a
                # rolling-caption duplicate. Require high lexical and sequence
                # similarity so short common political phrases survive.
                if text_similarity >= 0.90:
                    duplicate = True
                    duplicate_reason = "similarity"
                    break
            if duplicate:
                if str(clip.get("candidate_origin") or "") == "local_fallback":
                    self._candidate_diagnostics["fallback_discarded_count"] = int(
                        self._candidate_diagnostics.get("fallback_discarded_count", 0) or 0
                    ) + 1
                    field = "fallback_discarded_overlap" if duplicate_reason == "overlap" else "fallback_discarded_similarity"
                    self._candidate_diagnostics[field] = int(
                        self._candidate_diagnostics.get(field, 0) or 0
                    ) + 1
                continue
            selected.append(clip)

        return selected

    def _text_similarity(self, first, second):
        def normalize(value):
            return re.sub(r"[^a-z0-9à-ÿ ]+", " ", str(value or "").lower()).strip()

        left = normalize(first)
        right = normalize(second)
        if not left or not right:
            return 0.0
        left_words = set(left.split())
        right_words = set(right.split())
        lexical = len(left_words & right_words) / max(1, len(left_words | right_words))
        sequence = SequenceMatcher(None, left, right).ratio()
        return max(lexical, sequence)

    def _calculate_overlap(self, clip_a, clip_b):
        """Calculate overlap ratio between two clips."""
        overlap_start = max(clip_a["start"], clip_b["start"])
        overlap_end = min(clip_a["end"], clip_b["end"])

        if overlap_start >= overlap_end:
            return 0.0

        overlap_duration = overlap_end - overlap_start
        min_duration = min(clip_a["duration"], clip_b["duration"])

        return overlap_duration / max(min_duration, 1)

    def _format_time(self, seconds):
        """Format seconds as MM:SS."""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"
