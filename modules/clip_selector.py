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
import unicodedata
import requests
import time
from difflib import SequenceMatcher
from collections import Counter

from .political_profile import PROFILE_NAME, build_political_prompt_fragment
from .cancellation import OperationCancelled
from .job_manager import JobCancelled
from .editorial_chapters import annotate_clip_with_chapters
from .interview_turns import (
    classify_broadcast_boundary,
    detect_interviewer_turns,
    first_address_to_guest,
    is_a_whole_question,
    is_interviewer_sentence,
    looks_like_an_interview,
)

# Teto preferencial, não limite absoluto: `max_duration` continua sendo o limite
# duro, e um trecho excepcionalmente contextualizado ainda pode passar daqui.
#
# Eram 180s, e 180s vinha de intuição. Medido contra as fronteiras que um humano
# marcou no Acervo (`scripts/medir_cortes.py`), 180 fazia a sabatina da Band sair
# em pedaços de 175s — 2,8 vezes o tamanho que o próprio rotulador implica
# (território ÷ possibleCuts = 63s) — e 75% deles atravessavam uma fronteira de
# assunto. Em 60s a sabatina cai para 0,91 do alvo humano e 11% de
# atravessamento, com a cobertura dos dez territórios intacta.
#
# Não escolhi pelo atravessamento, que é degenerado: quanto mais curto o corte,
# menos fronteira ele cruza, e a curva nunca vira. Escolhi pela razão de duração
# chegar a 1,0. E há confirmação de fora da régua: o corte de João Pessoa que o
# editor chamou de "o melhor dos 3" tinha 61 segundos.
PREFERRED_MAX_DURATION = 60.0
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

# ─────────────────────────────────────────────────────────────────────────────
# ABERTURAS QUE A GRAMÁTICA JÁ DENUNCIA COMO CONTINUAÇÃO
#
# Medido na corrida real do editor (PENÉLOPE, 11 cortes entregues): o predicado
# de reparo aprovava as ONZE aberturas, inclusive as que ele reprovou a olho.
# Como ele nunca dizia "isto não começa nada", o recuo nunca andava, e cortes
# que abrem no meio do raciocínio ficavam como estavam.
#
#     #6  "Agora eu não sei o que que vocês estão avaliando…"
#     #9  "Somando tudo a três pontos na redondado,"
#     #7  "Quatro debates organizados aí."
#     #10 "O Renan também criticou Flávio Bolsonaro…"
#     #3  "Está certo? O Lula tem que estar nos debates…"
#
# As cinco falham por motivos gramaticais, não por assunto — e por isso dá para
# detectá-las sem inventar limiar. Cada conjunto abaixo é uma categoria, não uma
# lista de palavras colhida de uma amostra.
#
# ESTES CONJUNTOS SERVEM AO REPARO, NUNCA AO PORTÃO. `_editorial_flags` continua
# com as listas antigas de propósito: alargar o portão faria MAIS candidatos
# serem adiados, e o editor foi explícito que nada pode reduzir a quantidade de
# cortes. Alargar o reparo faz o corte COMEÇAR MAIS CEDO, que é a direção que
# ele prefere — "em casos de respostas longas eu gostaria de ter o contexto
# inteiro porque aí eu mesmo edito" — e o recuo já tem orçamento
# (`MAX_OPENING_REWIND_S`), então ninguém desaparece por causa disto.
# ─────────────────────────────────────────────────────────────────────────────

# "Também/inclusive/aliás X" afirma "além de algo", e esse algo ficou para trás.
ADDITIVE_ADVERBS_PT = {"também", "tambem", "inclusive", "aliás", "alias", "tampouco"}

# "Agora" na primeira palavra é o "agora" do discurso — contraste com o que veio
# antes —, não o do relógio. Só vale na posição 1: "agora são três horas" no meio
# de uma frase é hora de verdade.
CONTRAST_OPENERS_PT = {"agora"}

# Advérbio de lugar usado como ponteiro: "organizados aí", "foi lá". Aponta para
# algo que o corte não mostra. Só conta no fim da primeira oração, que é o uso
# dêitico; "lá em Brasília" traz o próprio referente e fica de fora.
POINTING_ADVERBS_PT = {"aí", "ai", "ali", "lá", "la"}

# Quantas palavras contam como "primeira oração" para procurar o aditivo.
FIRST_CLAUSE_WORDS = 8


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

    # A distant Chub seed may be recovered by its highlight text, but only when
    # enough non-trivial words agree. Text alignment is recall-only evidence and
    # always remains reviewable; it never proves the speaker or approves a clip.
    MIN_SEED_TEXT_ANCHOR_COVERAGE = 0.55
    MIN_SEED_TEXT_ANCHOR_SCORE = 0.62
    MAX_SEED_TEXT_ANCHOR_SENTENCES = 3

    # How far a clip's start may move forward to land on a sentence. Beyond this
    # the window was chosen wrong and trimming would hide the real problem.
    MAX_OPENING_TRIM_S = 15.0

    # Words of the answer that must be inside the clip before a question can be
    # considered closed. Fewer than this and the viewer still gets no payoff.
    MIN_ANSWER_WORDS = 12

    # A question-only candidate may show the first syllables of an answer and
    # still not be an editorially self-contained clip. This larger threshold is
    # diagnostic/defer-only; it does not replace the local QA bridge threshold.
    MIN_SUBSTANTIAL_ANSWER_WORDS = 20

    # A hard broadcast boundary is never crossed, even when the candidate's
    # original window was long enough to absorb both sides of a break.
    BROADCAST_BOUNDARY_PAD_S = 0.35

    # A response that follows a noisy interviewer handover may need to open on
    # its first stable, self-directed explanation rather than on the aside. This
    # is a minimum shift guard, not a timestamp rule.
    MIN_STABILIZED_OPENING_SHIFT_S = 20.0

    # Teto do alongamento que fecha uma pergunta. Ele não tinha teto próprio: o
    # único limite era a duração técnica de dez minutos, e numa coletiva real
    # isso esticou um corte em 157 segundos. Mostrar que a resposta começou é o
    # bastante — a resposta inteira é outro corte.
    MAX_ANSWER_EXTENSION_S = 30.0

    # Share of a candidate that may sit on labelled non-content before the
    # candidate is discarded instead of competing for a slot.
    NON_CONTENT_DROP_RATIO = 0.5

    # How far a clip's start may move back to open on the interviewer's question
    # instead of on the tail of the previous answer.
    MAX_TURN_START_SNAP_S = 20.0

    # How far a clip's start may rewind to reach the sentence where the thought
    # actually begins. Twenty-five seconds covers "the answer started three or
    # four sentences ago"; past it the window was chosen in the wrong place and
    # rewinding would build a different clip instead of repairing this one.
    MAX_OPENING_REWIND_S = 25.0

    # A pause this long before a sentence is a natural opening: the speaker
    # stopped, and whatever comes next stands on its own.
    OPENING_PAUSE_S = 1.2

    # Quanto de pergunta cabe na frente de uma resposta. Uma pergunta de coletiva
    # leva cinco a quinze segundos; passando de trinta o que está atrás não é o
    # setup deste corte, é o fim da resposta anterior mais a pergunta, e recuar
    # até lá abriria o corte no assunto errado.
    MAX_QUESTION_SETUP_S = 30.0

    # How far a clip's end may move to land on a seam of the conversation. The
    # selector already had a view on how much material the idea needs; beyond
    # this the boundary is not being repaired, it is being replaced. Growth is
    # additionally bounded by the preferred maximum duration.
    MAX_TURN_END_SHIFT_S = 90.0

    # Word timestamps can sharpen a seam, but they must never replace a badly
    # localized candidate. Refinement is bounded and diagnostic-only when the
    # transcript does not cover enough of the candidate text.
    MAX_WORD_BOUNDARY_SHIFT_S = 3.0
    MIN_WORD_BOUNDARY_COVERAGE = 0.55
    MIN_WORDS_FOR_BOUNDARY_REFINEMENT = 3

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
        # O teto preferencial não pode passar do limite duro. Nada reconciliava
        # os dois, e enquanto os limiares de bloco eram absolutos isso não
        # aparecia; quando eles passaram a sair do teto, um seletor pedido com
        # `max_duration=30` e o teto padrão de 60 começou a montar blocos de 48s
        # — maiores que o limite que ele mesmo declarou.
        self.preferred_max_duration = min(preferred_max_duration, max_duration)
        # In the Renan-first pipeline, a clean turn boundary is not enough to
        # claim who is speaking. The selection path carries this requirement
        # from editorial_context into every backend and gate.
        self._speaker_identity_required = False
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
            "campaign_hub_guided_filtered_by_speaker": 0,
            "campaign_hub_discovery_count": 0,
            "campaign_hub_discovery_candidates": [],
            "campaign_hub_publishable_guided_count": 0,
            "campaign_hub_publishable_candidates": [],
            "final_candidates": [],
            "stage_counts": {},
            "word_boundary_segments_available": False,
            "word_boundary_refined_count": 0,
            "word_boundary_review_count": 0,
            # Quem morreu na peneira de sobreposição, com nome e endereço. O
            # contador dizia "12 descartados" e mais nada: não dava para saber
            # se eram fragmentos redundantes ou cortes perdidos. Sem esta lista
            # a pergunta do editor — "estou perdendo cortes?" — só tinha
            # resposta por adivinhação.
            "descartados_por_sobreposicao": [],
            "hard_negatives": [],
            "hard_negative_count": 0,
            "candidate_relationships": [],
            "broadcast_break_count": 0,
            "reason": "not_evaluated",
        }

    def select_clips(self, transcription, energy_profile=None, user_context="",
                     settings=None, emit_progress=None, scene_changes=None,
                     video_layout=None, cancel_check=None):
        settings = settings or {}
        self._campaign_hub_guided_filtered_by_speaker = 0
        self._campaign_hub_discovery_candidates = []
        editorial_context = settings.get("editorial_context") if isinstance(settings.get("editorial_context"), dict) else {}
        focus = str(
            editorial_context.get("focus")
            or settings.get("editorial_focus")
            or ""
        ).strip().lower()
        profile = str(settings.get("editorial_profile") or "").strip().lower()
        channel_context = str(settings.get("channel_context") or "").strip().lower()
        renan_profile = profile in {"renan", "renan_santos", "renan_santos_politics"}
        renan_channel = "renan" in channel_context and "mbl" in channel_context
        self._speaker_identity_required = bool(
            focus in {"renan", "renan_santos", "renan_santos_politics"}
            or focus in {"", "auto", "generic_political"} and (renan_profile or renan_channel)
        )
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
                sentences, energy_profile, user_context, settings, emit_progress,
                cancel_check=cancel_check,
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
        guided_selection_enabled = bool(settings.get("campaign_hub_guided_selection", False))
        discovered_guided_clips = list(guided_clips or [])
        publishable_guided_clips = list(discovered_guided_clips)
        self._campaign_hub_discovery_candidates = [
            self._campaign_hub_discovery_record(clip, "eligible")
            for clip in discovered_guided_clips
        ]
        if discovered_guided_clips and self._speaker_identity_required:
            original_guided_count = len(discovered_guided_clips)
            publishable_guided_clips = [
                clip for clip in discovered_guided_clips
                if (clip.get("campaign_hub") or {}).get("renan_speaking") is True
            ]
            self._campaign_hub_guided_filtered_by_speaker = original_guided_count - len(publishable_guided_clips)
            publishable_ids = {
                str((clip.get("campaign_hub") or {}).get("seed_id") or "")
                for clip in publishable_guided_clips
            }
            for record in self._campaign_hub_discovery_candidates:
                if str(record.get("seed_id") or "") not in publishable_ids:
                    record["publication_status"] = "speaker_gate_review"
                    record["exclusion_reason"] = "sem evidência positiva de fala do Renan"
            if self._campaign_hub_guided_filtered_by_speaker and emit_progress:
                emit_progress(
                    f"[Campaign Hub] {self._campaign_hub_guided_filtered_by_speaker} proposta(s) guiada(s) "
                    "ficaram fora do pool Renan-first por não terem evidência positiva de fala do Renan.",
                    "info",
                )
        self._campaign_hub_publishable_candidates = [
            self._campaign_hub_discovery_record(clip, "publishable_pool")
            for clip in publishable_guided_clips
        ] if guided_selection_enabled else []
        if publishable_guided_clips and guided_selection_enabled:
            legacy_clips = list(clips or [])
            clips = publishable_guided_clips + legacy_clips
            self._selection_source = "campaign_hub_guided"
            if emit_progress:
                emit_progress(
                    f"[Campaign Hub] {len(publishable_guided_clips)} proposta(s) guiada(s) adicionada(s) antes do ranking; "
                    "as propostas permanecem sujeitas aos gates e à revisão editorial.",
                    "info",
                )
        elif discovered_guided_clips and emit_progress:
            emit_progress(
                f"[Campaign Hub] {len(discovered_guided_clips)} referência(s) históricas disponíveis apenas para explicação; "
                "a seleção e o score continuam exclusivamente no Furia 1 local.",
                "info",
            )

        expected_count = self._expected_candidate_count(sentences)
        primary_clips = list(clips or [])
        self._candidate_diagnostics = {
            "expected_count": expected_count,
            "stage_counts": {},
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
            "campaign_hub_guided_filtered_by_speaker": int(getattr(self, "_campaign_hub_guided_filtered_by_speaker", 0) or 0),
            "campaign_hub_discovery_count": len(getattr(self, "_campaign_hub_discovery_candidates", []) or []),
            "campaign_hub_discovery_candidates": list(getattr(self, "_campaign_hub_discovery_candidates", []) or []),
            "campaign_hub_publishable_guided_count": len(getattr(self, "_campaign_hub_publishable_candidates", []) or []),
            "campaign_hub_guided_selection_enabled": bool(settings.get("campaign_hub_guided_selection", False)),
            "campaign_hub_publishable_candidates": list(getattr(self, "_campaign_hub_publishable_candidates", []) or []),
            "final_candidates": [],
            "word_boundary_segments_available": False,
            "word_boundary_refined_count": 0,
            "word_boundary_review_count": 0,
            # Quem morreu na peneira de sobreposição, com nome e endereço. O
            # contador dizia "12 descartados" e mais nada: não dava para saber
            # se eram fragmentos redundantes ou cortes perdidos. Sem esta lista
            # a pergunta do editor — "estou perdendo cortes?" — só tinha
            # resposta por adivinhação.
            "descartados_por_sobreposicao": [],
            "hard_negatives": [],
            "hard_negative_count": 0,
            "reason": "short_source" if expected_count == 0 else ("adequate_pool" if len(primary_clips) >= expected_count else "primary_pool_thin"),
        }
        self._record_candidate_stage("primary_pool", primary_clips)
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
        self._record_candidate_stage("post_fallback", clips)

        # Drop candidates sitting on stretches the Acervo already labelled as
        # holding no editorial content, before the candidate budget is spent.
        # A window that opens on the tail of a sentence reads as broken even when
        # the material inside it is right, so the boundary is repaired before any
        # other judgement is made about the candidate.
        clips = self._trim_opening_fragment(clips, emit_progress, sentences)

        clips = self._close_open_question(clips, sentences, emit_progress)

        # On an interview the seams of the material are the interviewer's turns,
        # and they have the last word on both boundaries: no clip may stop in the
        # middle of an answer or run past the next change of subject.
        clips = self._align_to_interview_turns(clips, sentences, emit_progress)

        # The alignment above only repairs a start that already sits near a
        # question. A window that opens deep inside an answer is untouched by it
        # and is the defect the editor reported on four of five clips: the clip
        # begins mid-sentence, with the subject of the sentence left outside.
        clips = self._open_where_the_thought_begins(clips, sentences, emit_progress)

        # A mesma reparação do outro lado da borda. A abertura acima só cuida do
        # começo; o fim continuava caindo onde o bloco caía, e onde a conversa
        # não tem costura o bloco cai pelo relógio. É por isso que o podcast do
        # Acervo entregava um terço do tamanho que o rotulador implica.
        clips = self._close_where_the_thought_ends(clips, sentences, emit_progress)

        # O avanço acima só sabe ESTENDER. Quando o rabo de assunto novo já veio
        # dentro do bloco, ninguém o tirava — e é a queixa do editor sobre o
        # corte que termina em "segundo ponto:", com o raciocínio pela metade.
        clips = self._trim_trailing_announcement(clips, sentences, emit_progress)

        # Record the remaining editorial risks after all deterministic boundary
        # repairs. Question-only windows are deferred by the render gate; an
        # interrupted answer remains available for human review.
        clips = self._evaluate_interview_boundaries(clips, sentences, emit_progress)

        # If the canonical transcript has word timestamps, sharpen the repaired
        # seams without changing candidate discovery or ranking. Missing word
        # timestamps are a normal no-op and remain visible in diagnostics.
        clips = self._refine_boundaries_with_words(
            clips,
            transcription.get("segments") or [],
            emit_progress,
        )

        # Two candidates that merely touch are one answer served twice.
        # Cutting a long block into pieces makes neighbours by construction, and the
        # ranker scored each on its own merits without ever seeing that the clip
        # before it ended where this one begins.
        clips = self._drop_touching_siblings(clips, emit_progress, sentences)

        clips = self._drop_labelled_non_content(clips, settings, sentences, emit_progress)
        self._record_candidate_stage("after_non_content_filter", clips)

        # Every surviving candidate inherits what the Acervo established about the
        # stretch it covers, so the reviewer never sees an anonymous window.
        clips = self._attach_block_evidence(clips, settings)

        # Where the Acervo has nothing to say, Furia reads the subjects itself.
        clips = self._attach_local_topic_context(clips, sentences, emit_progress)
        self._record_candidate_stage("after_context_enrichment", clips)

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
        self._record_candidate_stage("pre_origin_label", clips)
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

        self._record_candidate_stage("pre_overlap", clips)
        # Apply anti-overlap filter after origin labels are available so a
        # primary candidate wins deterministic conflicts with local fallback.
        clips = self._remove_overlaps(clips)
        self._record_candidate_stage("post_overlap", clips)

        # Do not recreate intervals already generated in a previous run of the same source.
        clips = self._remove_previous_fingerprints(clips)
        self._record_candidate_stage("post_previous_fingerprints", clips)

        # Limit to the adaptive maximum only after deduplication, so a second run can
        # fill the queue with genuinely new moments instead of truncating repetitions.
        # Let the ranker and the final render stage apply the budget so we don't
        # discard valid candidates prematurely.
        pass
        self._candidate_diagnostics["final_count"] = len(clips)
        self._candidate_diagnostics["campaign_hub_publishable_candidate_count"] = len(clips)
        self._candidate_diagnostics["final_candidates"] = [
            {
                "start": round(float(clip.get("start", 0) or 0), 3),
                "end": round(float(clip.get("end", 0) or 0), 3),
                "candidate_origin": clip.get("candidate_origin"),
                "review_required": bool(clip.get("review_required")),
            }
            for clip in clips
        ]
        self._record_candidate_stage("final", clips)

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

    def _record_candidate_relationship(self, candidate, related, relation, reason=""):
        """Keep a bounded, diagnostic-only relation between candidate windows."""
        if not isinstance(candidate, dict) or not isinstance(related, dict):
            return
        relationships = self._candidate_diagnostics.setdefault("candidate_relationships", [])
        if len(relationships) >= 80:
            return
        relationships.append({
            "relation": str(relation or "related")[:40],
            "reason": str(reason or "")[:80],
            "candidate": {
                "start": round(float(candidate.get("start", 0) or 0), 3),
                "end": round(float(candidate.get("end", 0) or 0), 3),
            },
            "related": {
                "start": round(float(related.get("start", 0) or 0), 3),
                "end": round(float(related.get("end", 0) or 0), 3),
            },
        })

    def _record_hard_negative(self, clip, reason, *, winner=None, details=None):
        """Keep bounded near-misses for later human calibration.

        This is diagnostic-only. It never changes which candidate survives. The
        ledger deliberately stores a short transcript preview and interval
        metadata, never media, secrets or a complete transcription.
        """
        if not isinstance(clip, dict):
            return
        ledger = self._candidate_diagnostics.setdefault("hard_negatives", [])
        if len(ledger) >= 80:
            self._candidate_diagnostics["hard_negative_count"] = int(
                self._candidate_diagnostics.get("hard_negative_count", 0) or 0
            ) + 1
            return
        try:
            start = round(float(clip.get("start", 0) or 0), 3)
            end = round(float(clip.get("end", start) or start), 3)
        except (TypeError, ValueError):
            start, end = 0.0, 0.0
        item = {
            "start": start,
            "end": end,
            "duration": round(max(0.0, end - start), 3),
            "reason": str(reason or "unspecified")[:80],
            "candidate_origin": str(clip.get("candidate_origin") or "")[:48],
            "source": str(clip.get("source") or "")[:48],
            "score": clip.get("editorial_potential_score", clip.get("viral_score")),
            "confidence": clip.get("confidence"),
            "text_preview": " ".join(str(clip.get("text") or "").split())[:280],
        }
        if isinstance(winner, dict):
            try:
                winner_start = round(float(winner.get("start", 0) or 0), 3)
                winner_end = round(float(winner.get("end", winner_start) or winner_start), 3)
            except (TypeError, ValueError):
                winner_start, winner_end = 0.0, 0.0
            item["winner"] = {
                "start": winner_start,
                "end": winner_end,
                "score": winner.get("editorial_potential_score", winner.get("viral_score")),
                "text_preview": " ".join(str(winner.get("text") or "").split())[:180],
            }
        if isinstance(details, dict):
            item["details"] = {
                str(key)[:40]: value
                for key, value in list(details.items())[:8]
                if isinstance(value, (str, int, float, bool)) or value is None
            }
        ledger.append(item)
        self._candidate_diagnostics["hard_negative_count"] = int(
            self._candidate_diagnostics.get("hard_negative_count", 0) or 0
        ) + 1

    @staticmethod
    def _campaign_hub_discovery_record(clip, publication_status):
        """Return bounded Chub provenance for discovery and audit surfaces."""
        campaign_hub = clip.get("campaign_hub") if isinstance(clip, dict) else {}
        campaign_hub = campaign_hub if isinstance(campaign_hub, dict) else {}
        gates = campaign_hub.get("gates") if isinstance(campaign_hub.get("gates"), dict) else {}
        evidence = campaign_hub.get("alignment_evidence")
        if isinstance(evidence, dict):
            evidence = {
                "coverage": evidence.get("coverage"),
                "sequence": evidence.get("sequence"),
                "score": evidence.get("score"),
                "matched_words": list(evidence.get("matched_words") or [])[:20],
            }
        else:
            evidence = None
        return {
            "seed_id": campaign_hub.get("seed_id"),
            "block_id": campaign_hub.get("block_id"),
            "highlight_id": campaign_hub.get("highlight_id"),
            "start": round(float(clip.get("start", 0) or 0), 3),
            "end": round(float(clip.get("end", 0) or 0), 3),
            "duration": round(float(clip.get("duration", 0) or 0), 3),
            "source_kind": campaign_hub.get("source_kind"),
            "alignment_method": clip.get("alignment_method") or campaign_hub.get("alignment_method"),
            "alignment_evidence": evidence,
            "seed_text": str(campaign_hub.get("seed_text") or "")[:320],
            "summary": str(campaign_hub.get("summary") or "")[:500],
            "trigger_question": str(campaign_hub.get("trigger_question") or "")[:320],
            "topics": list(campaign_hub.get("topics") or [])[:20],
            "renan_speaking": campaign_hub.get("renan_speaking"),
            "speaker_gate": campaign_hub.get("speaker_gate"),
            "confidence": campaign_hub.get("confidence"),
            "density_rank": campaign_hub.get("density_rank"),
            "self_contained_rank": campaign_hub.get("self_contained_rank"),
            "trust_tier": campaign_hub.get("trust_tier"),
            "risk_flags": list(campaign_hub.get("risk_flags") or [])[:20],
            "gate_warnings": list(campaign_hub.get("gate_warnings") or [])[:20],
            "gates": gates,
            "review_required": bool(clip.get("review_required")),
            "publication_status": publication_status,
        }

    def _record_candidate_stage(self, stage, clips):
        """Store bounded, explainable counts for each selection stage.

        This is diagnostic-only: it never changes ordering or gate decisions. The
        benchmark uses it to distinguish Chub seeds, local candidates that merely
        inherited block evidence, and candidates lost to a later filter.
        """
        items = [item for item in (clips or []) if isinstance(item, dict)]
        source_counts = {}
        origin_counts = {}
        for item in items:
            source = str(item.get("source") or "nlp").lower()
            source_counts[source] = source_counts.get(source, 0) + 1
            origin = str(item.get("candidate_origin") or "unlabelled")
            origin_counts[origin] = origin_counts.get(origin, 0) + 1
        guided = [item for item in items if str(item.get("source") or "").lower() == "campaign_hub_guided"]
        block_evidence = [item for item in items if isinstance(item.get("campaign_hub_block"), dict)]
        stage_summary = {
            "count": len(items),
            "source_counts": dict(sorted(source_counts.items())),
            "origin_counts": dict(sorted(origin_counts.items())),
            "campaign_hub_guided": len(guided),
            "campaign_hub_block_evidence": len(block_evidence),
            "campaign_hub_renan_true": sum(
                1 for item in guided
                if (item.get("campaign_hub") or {}).get("renan_speaking") is True
            ),
            "identity_available": sum(1 for item in items if item.get("speaker_identity_available") is True),
            "context_complete": sum(1 for item in items if item.get("context_complete") is True),
            "payoff_complete": sum(1 for item in items if item.get("payoff_complete") is True),
            "review_required": sum(1 for item in items if item.get("review_required") is True),
        }
        stages = self._candidate_diagnostics.setdefault("stage_counts", {})
        stages[str(stage)] = stage_summary
        return stage_summary

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
            "pontos", "fala", "fale", "deste", "desta",
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

    @staticmethod
    def _split_long_segments(segments):
        """Break oversized segments back into the sentences they contain.

        The builder below only ever joins; it has no way to take a segment apart.
        That is fine for Whisper, which emits a few seconds at a time, and wrong
        for an imported caption: a 31-minute sabatina arrived as 62 segments, so a
        single "sentence" ran forty seconds and held the reporter's question and
        the answer to it in one lump. Everything downstream reads sentences — the
        turn detector, the seams, the name pass — and none of it can see a seam
        that sits inside one unit. On that run the interviewer's turns were never
        detected at all.

        Only segments that really carry several sentences are divided, and the
        times are shared out by how much text each piece holds. Speech rate is
        close enough to uniform inside one caption line for that to land on the
        right words, and nothing is invented: the text is the same, only cut.

        Duration is not what qualifies a segment for splitting, and requiring
        twelve seconds of it was the single most expensive line in this file.
        A YouTube caption line runs two or three seconds and breaks wherever the
        line filled up, so a full stop lands mid-line constantly:

            {"t": 1595.84, "texto": "premiando por boas práticas. você cria"}

        The builder below can only close a sentence when the accumulated text
        *ends* on a stop, so that full stop was invisible and the sentence it
        closes ran on into the next one. Measured on the Metrópoles interview,
        five of the eight rendered clips opened on the leftover — "premiando por
        boas práticas", "a gente tem que pensar no interesse nacional",
        "cometimento de crime dentro daquela comunidade" — which is exactly what
        the editor reported as "começa no meio da fala". Worse, the interviewer's
        question inherited the tail of the answer before it, so the turn detector
        placed every seam a few seconds early and the alignment pass then opened
        clips on those seams, on purpose.
        """
        detailed = []
        for segment in segments or []:
            text = str(segment.get("text") or "")
            try:
                start = float(segment.get("start", 0.0))
                end = float(segment.get("end", start))
            except (TypeError, ValueError):
                continue
            span = end - start
            pieces = [piece for piece in re.split(r"(?<=[.!?])\s+", text.strip()) if piece.strip()]
            if span <= 0 or len(pieces) < 2:
                detailed.append(segment)
                continue
            total = sum(len(piece) for piece in pieces) or 1
            cursor = start
            for piece in pieces:
                share = span * (len(piece) / total)
                detailed.append({
                    **segment,
                    "text": piece,
                    "start": round(cursor, 3),
                    "end": round(min(end, cursor + share), 3),
                    "split_from_segment": segment.get("id"),
                })
                cursor += share
        return detailed

    def _build_sentences(self, segments):
        """Group transcript segments while preserving technical metadata.

        Caps sentence length at 30s, but carries speaker labels, overlap flags,
        timing confidence and source segment ids into every editorial block.
        """
        segments = self._split_long_segments(segments)
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
                # Os instantes em que o arquivo marcou troca de locutor (">>").
                # É o instante que importa e não só o sinal: uma frase montada
                # pode conter a marca no meio dela — "Agora o peraló tem os
                # outros candidato." carrega três, e a que interessa é a última.
                "speaker_change_at": [
                    round(float(item.get("start", 0) or 0), 3)
                    for item in current_segments
                    if item.get("speaker_change")
                ],
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

            # A marca ">>" do arquivo diz que quem fala mudou aqui. Juntar a fala
            # de duas pessoas numa mesma "frase" está errado de saída, e tinha uma
            # consequência concreta: na coletiva de João Pessoa, "Agora o peraló
            # tem os outros" (repórter) e "candidato. Eh, quais os compromissos..."
            # (outro repórter) viravam uma frase só. A fronteira do bloco só cai em
            # fronteira de frase, então o corte abria em "Eh, quais os
            # compromissos" — o editor pediu que abrisse em "candidato", que é
            # exatamente onde a marca está.
            if current_text and seg.get("speaker_change"):
                flush()
                current_start = None

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

    # How many blocks travel in one request. The whole transcript used to go at
    # once — the old docstring said so out loud — and on a 73-minute press
    # conference that meant 28 blocks in a single prompt, which timed out at 180
    # seconds. Every candidate for that source then came from the keyword
    # fallback, and that fallback is where the four clips of exactly 180.0
    # seconds came from. Several small requests cost more time and buy back the
    # only path that reads the argument.
    GEMINI_BLOCKS_PER_REQUEST = 8
    # A lot this size answers in well under a minute; the old ceiling was sized
    # for a prompt that no longer exists, and a slow answer is still an answer.
    GEMINI_TIMEOUT_S = 60
    # Total budget for all Gemini lots in one analysis. When it expires, the
    # local NLP path receives the partial result instead of waiting on retries.
    GEMINI_TOTAL_TIMEOUT_S = 180

    def _select_with_gemini(self, sentences, energy_profile, user_context, settings, emit_progress, cancel_check=None):
        """Select clips with Gemini, a few blocks at a time.

        Partial success is kept. A lot that fails no longer discards the lots
        that answered: losing a quarter of a source to the fallback is bad,
        losing all of it is what actually happened.
        """
        api_key = settings.get("gemini_api_key", "").strip()
        if not api_key:
            if emit_progress:
                emit_progress("[Gemini] API key nao configurada.", "warning")
            return []

        transcript_blocks = self._build_transcript_blocks(sentences)
        if not transcript_blocks:
            return []

        # The audio was already measured and then thrown away on this path. The
        # profile was computed for every source — 4.418 windows on a 73-minute
        # one — passed into this function, and read by nobody: only the keyword
        # fallback ever looked at it. Where the voice rises is exactly the signal
        # the editor keeps asking for, so the blocks carry it into the prompt.
        self._mark_energy(transcript_blocks, energy_profile)

        system_prompt = self._get_gemini_system_prompt(settings.get("editorial_profile", PROFILE_NAME))
        size = max(1, int(self.GEMINI_BLOCKS_PER_REQUEST))
        lots = [transcript_blocks[at:at + size] for at in range(0, len(transcript_blocks), size)]
        if emit_progress:
            emit_progress(
                f"[Gemini] {len(transcript_blocks)} blocos em {len(lots)} lote(s) de até {size}.", "info"
            )

        selections, failed = [], 0
        deadline = time.monotonic() + max(1.0, float(self.GEMINI_TOTAL_TIMEOUT_S))
        for position, lot in enumerate(lots, start=1):
            if cancel_check:
                cancel_check()
            if time.monotonic() >= deadline:
                failed += len(lots) - position + 1
                if emit_progress:
                    emit_progress(
                        f"[Gemini] Limite total de {self.GEMINI_TOTAL_TIMEOUT_S:.0f}s atingido; "
                        "seguindo pelo caminho local com os resultados parciais.",
                        "warning",
                    )
                break
            if emit_progress:
                emit_progress(f"[Gemini] Lote {position}/{len(lots)}...", "info")
            found = self._gemini_lot(
                lot, sentences, transcript_blocks, system_prompt,
                user_context, settings, api_key, emit_progress,
                cancel_check=cancel_check, deadline=deadline,
            )
            if found is self.TEMPO_ESGOTADO:
                failed += len(lots) - position + 1
                if emit_progress:
                    emit_progress(
                        f"[Gemini] Limite total de {self.GEMINI_TOTAL_TIMEOUT_S:.0f}s atingido; "
                        "seguindo pelo caminho local com os resultados parciais.",
                        "warning",
                    )
                break
            if found is self.QUOTA_ESGOTADA:
                # Pedir os outros lotes é pedir de novo o que já foi negado. Numa
                # fonte de 1h21 são dezenas de requisições condenadas antes de a
                # corrida cair calada no NLP básico.
                restantes = len(lots) - position
                if emit_progress:
                    emit_progress(
                        "[Gemini] A quota da sua conta acabou. "
                        + (f"Os {restantes} lote(s) restantes foram interrompidos, "
                           if restantes else "A corrida foi interrompida, ")
                        + "porque o limite é da conta e não deste trecho. "
                        "O corte segue pelo caminho local, que é mais fraco.",
                        "warning",
                    )
                failed += restantes + 1
                break
            if found is None:
                failed += 1
                continue
            selections.extend(found)

        if emit_progress:
            if failed and selections:
                emit_progress(
                    f"[Gemini] {failed} lote(s) sem resposta; os outros renderam "
                    f"{len(selections)} candidato(s).", "warning",
                )
            elif selections:
                emit_progress(f"[Gemini] {len(selections)} candidato(s) encontrados.", "info")
        selections.sort(key=lambda item: item.get("viral_score", 0), reverse=True)
        return selections

    # A block sitting this far above the source's own median counts as raised
    # voice. Relative, because a studio and a street have different floors and an
    # absolute level would mean nothing on the next source.
    ENERGY_RAISED = 1.35
    ENERGY_CALM = 0.7

    @staticmethod
    def _mark_energy(blocks, energy_profile):
        """Tell each block whether the voice rises inside it.

        Left as a plain word rather than a number on purpose: the model reads it
        as a hint about intensity, and a number would invite it to rank by
        loudness. Shouting is not the same as saying something, and the editorial
        rule stands — energy may not compensate a structural failure.
        """
        # O analisador devolve uma janela por segundo como dicionário —
        # {"time", "energy_rms", "energy_db", "energy_normalized"} — e não um
        # número solto. Ler isso como número quebrou o corte inteiro por dois
        # dias: `float()` sobre um dicionário levanta TypeError, o job morria em
        # "Erro no corte" logo depois de dividir a transcrição, e nenhum teste
        # pegou porque a fixture que escrevi usava uma lista de floats que a
        # produção nunca produziu.
        janelas = []
        for item in energy_profile or []:
            if isinstance(item, dict):
                valor = item.get("energy_normalized", item.get("energy_rms"))
                instante = item.get("time")
            else:
                valor, instante = item, None
            try:
                if valor is None:
                    continue
                janelas.append((float(instante) if instante is not None else float(len(janelas)), float(valor)))
            except (TypeError, ValueError):
                continue
        if not janelas or not blocks:
            return blocks
        ordered = sorted(valor for _, valor in janelas)
        median = ordered[len(ordered) // 2] or 0.0
        if median <= 0:
            return blocks
        for block in blocks:
            start = max(0.0, float(block.get("start", 0) or 0))
            end = max(start + 1.0, float(block.get("end", 0) or 0))
            window = [valor for instante, valor in janelas if start <= instante < end]
            if not window:
                continue
            peak = max(window) / median
            if peak >= ClipSelector.ENERGY_RAISED:
                block["energy_mark"] = "voz elevada"
            elif peak <= ClipSelector.ENERGY_CALM:
                block["energy_mark"] = "voz baixa"
        return blocks

    def _gemini_lot(self, blocks, sentences, all_blocks, system_prompt,
                    user_context, settings, api_key, emit_progress, cancel_check=None, deadline=None):
        """One request. ``None`` says this lot failed and the others still count."""
        user_prompt = self._build_gemini_prompt(
            blocks,
            user_context,
            settings.get("editorial_context"),
        )

        import time as _time

        # Usa o mesmo modelo Gemini configurado para a análise multimodal.
        # O padrão preserva compatibilidade com instalações existentes; a validação
        # impede que uma configuração corrompida altere o caminho da requisição.
        configured_model = str(settings.get("gemini_model", "gemini-2.5-flash") or "").strip()
        model_name = configured_model if re.fullmatch(r"gemini-[a-z0-9.-]+", configured_model) else "gemini-2.5-flash"
        # A mensagem de quota dizia "Tentando proximo modelo..." e a lista tinha um
        # modelo só: não havia próximo, e a corrida caía para o NLP com
        # alternativas de pé. Medido na conta do editor, no mesmo instante:
        # gemini-2.5-flash devolvia 429 e gemini-flash-latest devolvia 200. A
        # quota é por modelo.
        models_to_try = [model_name] + [
            alternativa for alternativa in self.GEMINI_FALLBACK_MODELS
            if alternativa != model_name
        ]
        last_error = ""

        for model_name in models_to_try:
            for attempt in range(3):
                if cancel_check:
                    cancel_check()
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return self.TEMPO_ESGOTADO
                    request_timeout = max(1.0, min(float(self.GEMINI_TIMEOUT_S), remaining))
                else:
                    request_timeout = float(self.GEMINI_TIMEOUT_S)
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
                        timeout=request_timeout,
                    )

                    if response.status_code == 503:
                        # Temporary overload — retry after delay
                        if emit_progress:
                            emit_progress(f"[Gemini] {model_name} sobrecarregado (503). Retentando em {5 * (attempt + 1)}s...", "warning")
                        delay = float(5 * (attempt + 1))
                        if deadline is not None:
                            delay = min(delay, max(0.0, deadline - time.monotonic()))
                        if delay:
                            if cancel_check:
                                cancel_check()
                            _time.sleep(delay)
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
                        return None

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

                    selections = self._parse_llm_response(
                        text, sentences, all_blocks, 0, source="gemini", emit_progress=emit_progress
                    )

                    if not selections:
                        if emit_progress:
                            preview = text[:300].replace("\n", " ")
                            emit_progress(f"[Gemini] JSON parseado mas 0 clips validos. Preview: {preview}...", "warning")
                        last_error = "0 clips parsed"
                        break  # Try next model

                    if emit_progress:
                        emit_progress(f"[Gemini] {model_name} encontrou {len(selections)} clips candidatos!", "info")

                    return selections

                except requests.exceptions.ConnectionError:
                    if emit_progress:
                        emit_progress("[Gemini] Sem conexao com internet.", "warning")
                    return None
                except requests.exceptions.Timeout:
                    if emit_progress:
                        emit_progress(
                            f"[Gemini] Timeout com {model_name} (>{request_timeout:.0f}s) "
                            f"na tentativa {attempt + 1}/3.",
                            "warning",
                        )
                    last_error = "timeout"
                    if deadline is not None and time.monotonic() >= deadline:
                        return self.TEMPO_ESGOTADO
                    if attempt < 2:
                        delay = float(2 * (attempt + 1))
                        if deadline is not None:
                            delay = min(delay, max(0.0, deadline - time.monotonic()))
                        if delay:
                            if cancel_check:
                                cancel_check()
                            _time.sleep(delay)
                        continue
                    break
                except (OperationCancelled, JobCancelled):
                    raise
                except Exception as e:
                    if emit_progress:
                        emit_progress(f"[Gemini] Erro com {model_name}: {str(e)[:200]}", "warning")
                    last_error = str(e)[:150]
                    break  # Try next model

        if emit_progress and last_error:
            emit_progress(f"[Gemini] Lote sem resposta. Ultimo erro: {last_error}", "warning")
        # Quota esgotada não é um problema deste lote: é da conta, e os lotes
        # seguintes vão bater na mesma porta. Quem chama precisa saber a
        # diferença para parar em vez de insistir.
        if str(last_error).startswith("429"):
            return self.QUOTA_ESGOTADA
        return None

    # A reserva quando o modelo configurado nega. Feita de apelidos e não de
    # versões: `gemini-2.0-flash` já devolve 404 na conta do editor — some da API
    # sem aviso —, enquanto `-latest` é a promessa do próprio fornecedor de
    # apontar para o modelo corrente. Uma lista de versões fixas apodrece, e foi
    # apodrecendo em silêncio que ela chegou até aqui.
    GEMINI_FALLBACK_MODELS = ("gemini-flash-latest", "gemini-flash-lite-latest")

    # Sentinela devolvida por `_gemini_lot` quando a conta — e não o lote —
    # acabou. Um objeto próprio em vez de `None` porque as duas falhas pedem
    # respostas opostas: uma segue para o lote seguinte, a outra para a corrida.
    QUOTA_ESGOTADA = object()
    # Sentinel for a per-analysis time budget; the caller falls back locally.
    TEMPO_ESGOTADO = object()

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
   - Use 60 segundos como teto preferencial, nao como limite absoluto. Ultrapasse-o somente quando encurtar destruir a pergunta, a resposta, a prova, o argumento ou a conclusao.
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

    def _render_editorial_context(self, editorial_context):
        """A pré-análise em texto, com o mesmo relógio da transcrição.

        Ela ia para o prompt como `repr` de dicionário do Python e ocupava mais
        espaço que a própria transcrição num vídeo curto — com escrituração
        interna que o modelo não tem como usar (`boundary_basis`,
        `needs_speaker_review`, `qa_candidate_ids`, índices de segmento).

        Pior: eram listas de `{'start': ..., 'end': ...}` logo acima do pedido de
        `"blocks": [3, 4, 5]`, e na coletiva de João Pessoa o modelo respondeu
        exatamente naquela forma. Aqui não há mais chave nenhuma para copiar, e
        os tempos saem em MM:SS, como os blocos da transcrição.
        """
        if not editorial_context:
            return ""

        def intervalo(item):
            return f"{self._format_time(float(item.get('start', 0) or 0))}–{self._format_time(float(item.get('end', 0) or 0))}"

        linhas = ["", "PRÉ-ANÁLISE (determinística, feita antes de você):"]
        description = str(editorial_context.get("description", "") or "").strip()
        if description:
            linhas.append(description)
        linhas.append(
            "Foco padrão: Renan Santos/MBL. Confiança inicial de participante: "
            f"{editorial_context.get('participant_confidence', 0):.0%}."
        )

        windows = editorial_context.get("interview_windows", []) or []
        if windows:
            linhas.append(
                "Trechos prováveis de entrevista: "
                + ", ".join(intervalo(item) for item in windows[:8])
                + "."
            )

        qa = editorial_context.get("qa_candidates", []) or []
        if qa:
            linhas.append(
                "Pares pergunta–resposta detectados (a pergunta começa no primeiro tempo): "
                + ", ".join(intervalo(item) for item in qa[:12])
                + "."
            )

        chapters = editorial_context.get("editorial_chapters", []) or []
        if chapters:
            linhas.append("Capítulos temporais:")
            for chapter in chapters[:24]:
                rotulo = str(chapter.get("label", "") or "bloco editorial")
                linhas.append(f"  {intervalo(chapter)}  {rotulo}")

        contract = editorial_context.get("context_contract") or {}
        reasons = [str(item) for item in (contract.get("review_reasons") or []) if str(item).strip()]
        if reasons:
            # O contrato já nomeia em português o que falta para o trecho se
            # sustentar sozinho; ele entra como exigência, não como dicionário.
            linhas.append("Antes de fechar um clip, garanta que ele já: " + "; ".join(reasons) + ".")

        linhas.append(
            "Respeite os capítulos como blocos editoriais contíguos. Não combine blocos de "
            "capítulos separados sem uma ponte de fala clara. Quando a seleção for uma "
            "pergunta–resposta, inclua a ponte completa: a pergunta inteira e a resposta "
            "inteira. Se a fala abrir com uma referência ('isso', 'essa questão'), recupere a "
            "menor frase anterior que a torne compreensível. Não termine antes da consequência. "
            "Se houver dúvida sobre quem fala, rejeite o trecho."
        )
        return "\n".join(linhas) + "\n"

    def _build_gemini_prompt(self, blocks, user_context, editorial_context=None):
        """Build prompt with deterministic interview context plus the transcript."""
        lines = []
        for b in blocks:
            timestamp = f"[{self._format_time(b['start'])} - {self._format_time(b['end'])}]"
            energy = f" [{b['energy_mark']}]" if b.get("energy_mark") else ""
            lines.append(f"BLOCO {b['index']}: {timestamp} ({b['duration']}s){energy}\n{b['text']}\n")

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

        editorial_instruction = self._render_editorial_context(editorial_context)

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
        self._mark_energy(transcript_blocks, energy_profile)

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

                selections = self._parse_llm_response(
                    text, sentences, transcript_blocks, chunk_idx,
                    source="llm", emit_progress=emit_progress,
                )
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
5. DURACAO: Nao ha faixa fixa. Prefira o menor trecho autossuficiente; 60 segundos e apenas um teto preferencial. So ultrapasse esse teto se o contexto e o payoff exigirem.
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
            energy = f" [{b['energy_mark']}]" if b.get("energy_mark") else ""
            lines.append(f"BLOCO {b['index']}: {timestamp} ({b['duration']}s){energy}\n{b['text']}\n")

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

        editorial_instruction = self._render_editorial_context(editorial_context)

        num_clips = min(self.max_clips, max(3, len(blocks) // 3))
        return f"""Selecione os {num_clips} MELHORES momentos para clips curtos.
{editorial_instruction}
{context_instruction}

TRANSCRICAO (blocos {chunk_offset} a {chunk_offset + len(blocks) - 1} de {total_blocks} total):

{transcript_text}

Combine blocos consecutivos apenas ate o menor trecho com contexto completo e conclusao.
Retorne APENAS o JSON.
"""

    def _build_transcript_blocks(self, sentences, granularity="fine"):
        """Group sentences into the units the selector will choose between.

        On an interview these are the seams of the conversation. Everywhere else
        they are timed, as they always were.

        ``granularity`` diz quem vai consumir o bloco. Um modelo combina blocos e
        precisa deles finos; o caminho local não combina nada e usa o bloco como
        corte. Onde há costura de conversa a fronteira é a troca de palavra e não
        depende de quem consome, então a distinção só vale para o relógio.
        """
        seams = self._conversation_seams(sentences)
        if seams:
            return self._blocks_between_seams(sentences, seams)
        return self._timed_transcript_blocks(sentences, granularity=granularity)

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

        # A whole question is evidence by itself, and it is local. The density
        # gate below asks whether the *whole video* is an interview before
        # honouring any seam, and its own reasoning undoes it: if a monologue
        # produces almost no turns, then using turns as seams on a monologue
        # changes almost nothing. What the gate did block is the shape the editor
        # actually works on — a speech followed by a press conference — where the
        # questions are real but too sparse across the whole runtime to clear
        # one-turn-per-five-minutes. There the blocks fell back to the stopwatch,
        # and the question ended up glued to the tail of the previous answer.
        seams = {turn["start_s"] for turn in turns if turn.get("asks_a_whole_question")}
        # A chamada/retorno é uma costura em ambas as extremidades: o bloco da
        # vinheta não deve juntar-se nem à resposta anterior nem à pergunta após
        # o retorno.
        for turn in turns:
            if turn.get("hard_boundary"):
                seams.add(float(turn["start_s"]))
                seams.add(float(turn["end_s"]))

        # E, antes de qualquer adivinhação: a marca que o arquivo já traz. O
        # YouTube e o tactiq escrevem ">>" onde o locutor troca, e a transcrição
        # de 1h21 que o editor mandou tem 153 delas. O parser as apagava na
        # entrada, então a costura era reconstruída por vocabulário — "candidato,",
        # "o senhor" — tendo a resposta escrita no próprio arquivo. Uma pergunta
        # que não use nenhuma dessas formas passava batida, e foi assim que quatro
        # dos oito cortes da coletiva abriram no meio de uma frase.
        #
        # Marca não é diarização: ela diz que trocou, não quem passou a falar.
        # Para decidir onde o corte abre é o suficiente, e é evidência do arquivo
        # em vez de palpite meu.
        for item in sentences or []:
            for instante in item.get("speaker_change_at") or []:
                seams.add(float(instante))
            if item.get("speaker_change"):
                seams.add(float(item.get("start", 0) or 0))

        # The looser signals — a vocative, a short aside, an address with no
        # question in it — are only trustworthy when the source really is an
        # interview, so they stay behind the gate.
        if looks_like_an_interview(turns, span):
            seams.update(turn["start_s"] for turn in turns if not turn["interjection"])
        return sorted(seams)

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
        """Cut an over-long exchange into pieces a clip can actually hold.

        Where the cut falls is the whole question. Closing each piece the moment
        the stopwatch reached the preferred ceiling put back, one level up, the
        defect the seam detection had just removed: on a 73-minute press
        conference it produced four candidates of exactly 180.0 seconds, three of
        them consecutive tiles of the same answer, each opening mid-argument and
        stopping mid-argument. The editor read them as random.

        So the ceiling decides how much may be taken and the material decides
        where to stop. Inside the window the piece is allowed to end, the best
        boundary wins: the interviewer taking the floor first, since that is a
        real change of speaker; otherwise the longest silence, which is where the
        speaker themselves finished a thought.
        """
        if not group:
            return []
        span = float(group[-1]["end"]) - float(group[0]["start"])
        if span <= self.preferred_max_duration:
            return [group]

        pieces: list[list[dict]] = []
        remaining = list(group)
        while remaining:
            opening = float(remaining[0]["start"])
            if float(remaining[-1]["end"]) - opening <= self.preferred_max_duration:
                pieces.append(remaining)
                break
            cut = self._best_cut_index(remaining, opening)
            pieces.append(remaining[:cut])
            remaining = remaining[cut:]

        if len(pieces) > 1:
            tail_span = float(pieces[-1][-1]["end"]) - float(pieces[-1][0]["start"])
            if tail_span < self.min_duration:
                pieces[-2].extend(pieces.pop())
        return pieces

    # Below this a gap between two candidates is not a gap: they are the same
    # stretch of talk handed over in two files.
    TOUCHING_GAP_S = 3.0

    def _drop_touching_siblings(self, clips, emit_progress=None, sentences=None):
        """Keep one of two candidates that sit end to end.

        Measured on a 73-minute press conference: three of the seven rendered
        clips were consecutive pieces of one answer — 1137→1158, 1158→1227,
        1227→1407 — and the editor recognised the second as "just the beginning
        of" the third. Each had been judged alone and none knew of the others.

        The longer one is kept when the scores are close, because the complaint
        about the short neighbours was that they end before the idea does.

        **Encostar não basta.** A regra nasceu de blocos esparsos, onde dois
        candidatos colados eram mesmo a mesma resposta servida duas vezes. No
        caminho local os blocos particionam a fonte inteira, então encostar é o
        estado normal e não um defeito: numa sabatina real este passe apagava
        nove de dezoito candidatos, cada um respondendo a uma pergunta
        diferente. O que separa os dois casos é quem fala no meio — se o
        entrevistador toma a palavra na junta, são respostas a perguntas
        distintas e as duas vivem.
        """
        # A mesma costura que separa os blocos separa os cortes. Isto era
        # derivado de novo aqui, com as duas travas que já custaram caro lá em
        # cima — o portão de densidade e o filtro de interjeição — e uma
        # coletiva com perguntas curtas caía nas duas. Julgar a mesma coisa em
        # dois lugares é como o defeito volta; agora há uma fonte só.
        juntas_de_pergunta: list[float] = []
        if sentences:
            try:
                juntas_de_pergunta = self._conversation_seams(sentences)
            except (TypeError, ValueError, KeyError):
                juntas_de_pergunta = []

        def pergunta_entre(fim_anterior, inicio_atual):
            baixo, alto = min(fim_anterior, inicio_atual) - 2.0, max(fim_anterior, inicio_atual) + 2.0
            return any(baixo <= marca <= alto for marca in juntas_de_pergunta)

        ordered = sorted(clips or [], key=lambda clip: float(clip.get("start", 0) or 0))
        kept: list[dict] = []
        dropped = 0
        for clip in ordered:
            start = float(clip.get("start", 0) or 0)
            previous = kept[-1] if kept else None
            gap = start - float(previous.get("end", 0) or 0) if previous is not None else None
            # Overlap is a different problem with its own handling and its own
            # diagnostics; swallowing it here hid which candidate had lost to
            # which. This pass only owns the case where one clip ends and the
            # next begins.
            if (
                gap is not None
                and 0.0 <= gap <= self.TOUCHING_GAP_S
                and not pergunta_entre(float(previous.get("end", 0) or 0), start)
            ):
                current_score = float(clip.get("viral_score", 0) or 0)
                previous_score = float(previous.get("viral_score", 0) or 0)
                current_span = float(clip.get("end", 0) or 0) - start
                previous_span = float(previous.get("end", 0) or 0) - float(previous.get("start", 0) or 0)
                # A clearly better score wins; a tie goes to the longer stretch.
                better = (current_score > previous_score + 5) or (
                    abs(current_score - previous_score) <= 5 and current_span > previous_span
                )
                dropped += 1
                if better:
                    self._record_candidate_relationship(
                        previous, clip, "continuation_of", "touching_sibling"
                    )
                    self._record_hard_negative(
                        previous,
                        "touching_sibling_lost_to_better_candidate",
                        winner=clip,
                        details={"score_gap": round(current_score - previous_score, 2), "relation": "continuation_of"},
                    )
                    kept[-1] = clip
                else:
                    self._record_candidate_relationship(
                        clip, previous, "continuation_of", "touching_sibling"
                    )
                    self._record_hard_negative(
                        clip,
                        "touching_sibling_lost_to_existing_candidate",
                        winner=previous,
                        details={"score_gap": round(previous_score - current_score, 2), "relation": "continuation_of"},
                    )
                continue
            kept.append(clip)
        if dropped and emit_progress:
            emit_progress(
                f"[Vizinhos] {dropped} candidato(s) descartado(s) por serem a continuação imediata de outro corte.",
                "info",
            )
        return kept

    def _best_cut_index(self, sentences, opening):
        """How many sentences the next piece takes, cutting where the talk breaks.

        Only positions that leave a piece long enough to stand alone and short
        enough to keep are considered; among those, a change of speaker beats a
        pause and a pause beats the arbitrary ceiling.
        """
        allowed = []
        for index in range(1, len(sentences)):
            duration = float(sentences[index - 1]["end"]) - opening
            if duration < self.min_duration:
                continue
            if duration > self.preferred_max_duration:
                break
            gap = float(sentences[index]["start"]) - float(sentences[index - 1]["end"])
            allowed.append((index, gap, is_interviewer_sentence(str(sentences[index].get("text") or ""))))
        if not allowed:
            # Nothing inside the window: fall back to the ceiling rather than
            # emit a piece too short to be a clip.
            for index in range(1, len(sentences)):
                if float(sentences[index - 1]["end"]) - opening >= self.preferred_max_duration:
                    return index
            return len(sentences)
        handover = [item for item in allowed if item[2]]
        pool = handover or allowed
        return max(pool, key=lambda item: (item[1], item[0]))[0]

    # Onde não há costura de conversa, o bloco fecha pelo relógio. Os limiares
    # eram 18s e 30s, absolutos, escolhidos quando o teto era 180s — nessa conta
    # o bloco valia um décimo do corte e servia só como peça para o modelo juntar.
    # Com o teto medido em 60s eles ficaram desproporcionais: no podcast do
    # Acervo, que é a única das três fontes sem costura, saíam 78 fatias de 21s e
    # o corte virava uma delas.
    #
    # Agora saem do teto, para os dois caminhos não discordarem quando a régua o
    # mover. Medido em `scripts/medir_cortes.py`: o podcast vai de 0,29 para 0,41
    # do alvo humano e o atravessamento de assunto cai de 9% para 4%; a live e a
    # sabatina não se movem, porque as duas têm costura e nem passam por aqui.
    #
    # Não chega a 1,0 e o motivo está entendido: aqui o corte é um bloco, e o
    # alvo do podcast é 94s. Fechar essa distância pede juntar blocos — o que o
    # comentário antigo prometia e nunca aconteceu no caminho local — e isso é
    # mudança maior, para um ciclo com a régua já montada.
    # O tamanho certo do bloco depende de quem vai consumi-lo, e essa distinção
    # faltava. Para Gemini e Ollama o bloco é matéria-prima: o prompt manda
    # "combine apenas os blocos consecutivos necessários", então ele precisa ser
    # fino o bastante para haver o que combinar. No caminho local ninguém combina
    # — o bloco *vira* o corte —, e ali um bloco fino é um corte curto.
    #
    # Medido em `scripts/medir_cortes.py`, com o passe de fecho já no lugar: no
    # podcast, que é a única das três fontes sem costura de conversa e por isso a
    # única que depende destes limiares, a razão de duração sobe de 0,41 para
    # 0,73 quando o bloco local vai a 0,90 do teto. A curva vira em 1,00 (0,68),
    # então 0,90 é ótimo medido e não borda de varredura. Custa atravessamento de
    # assunto: 4% para 15% — ainda abaixo dos 24% da sabatina, e é a troca certa,
    # porque "não conclui o tema" é a queixa do editor e "atravessa" não é.
    #
    # Os limiares finos ficam onde estavam. Mexer neles otimizaria o caminho que
    # eu meço e poderia estragar o que não meço — o Gemini roda na máquina do
    # editor, não aqui.
    BLOCK_SENTENCE_CLOSE_RATIO = 0.40
    BLOCK_HARD_CLOSE_RATIO = 0.80
    LOCAL_BLOCK_SENTENCE_CLOSE_RATIO = 0.90
    LOCAL_BLOCK_HARD_CLOSE_RATIO = 1.00

    def _timed_transcript_blocks(self, sentences, granularity="fine"):
        """Group sentences into compact editorial blocks for analysis.

        ``granularity="clip"`` monta blocos do tamanho de um corte, para o
        caminho local, onde o bloco não é combinado por ninguém.
        """
        if granularity == "clip":
            sentence_ratio = self.LOCAL_BLOCK_SENTENCE_CLOSE_RATIO
            hard_ratio = self.LOCAL_BLOCK_HARD_CLOSE_RATIO
        else:
            sentence_ratio = self.BLOCK_SENTENCE_CLOSE_RATIO
            hard_ratio = self.BLOCK_HARD_CLOSE_RATIO
        sentence_close = self.preferred_max_duration * sentence_ratio
        hard_close = self.preferred_max_duration * hard_ratio
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
            closes_a_sentence = sent["text"].strip()[-1:] in ".!?"
            if current_duration >= hard_close or (closes_a_sentence and current_duration >= sentence_close):
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
            "speaker_identity_required": bool(self._speaker_identity_required),
            "speaker_identity_available": bool(speakers),
            "speaker_change_detected": len(speakers) > 1,
            "overlap_suspected": any(bool(sentence.get("overlap_suspected")) for sentence in sentences),
            "speaker_turn_valid": not any(bool(sentence.get("overlap_suspected")) for sentence in sentences),
            "timing_ambiguous": any(bool(sentence.get("timing_ambiguous")) for sentence in sentences),
            "timing_confidence": min(
                [float(sentence["timing_confidence"]) for sentence in sentences if sentence.get("timing_confidence") is not None]
                or [1.0]
            ),
        }

    # Sobreposição mínima para dizer que um intervalo de tempo cobre um bloco.
    # Abaixo disso é arredondamento na borda, não intenção de incluir o bloco.
    SPAN_MATCH_S = 0.25

    @staticmethod
    def _instant(value):
        """Um instante do vídeo em segundos, aceito em número ou em relógio.

        A transcrição vai para o modelo com cada bloco rotulado `[MM:SS - MM:SS]`,
        e desde a 6.12 a pré-análise também. Então ele responde no relógio que nós
        ensinamos — `{"start": "00:55"}` foi o que a sabatina devolveu na conta
        real — e `float("00:55")` levanta `ValueError` dentro do mesmo `except`
        que já custou a coletiva de João Pessoa. Ensinar um formato e recusar a
        resposta nele é o mesmo defeito uma camada acima.
        """
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        texto = str(value or "").strip()
        if not texto:
            return None
        if ":" in texto:
            partes = texto.split(":")
            if len(partes) > 3:
                return None
            total = 0.0
            for parte in partes:
                try:
                    total = total * 60.0 + float(parte)
                except ValueError:
                    return None
            return total
        try:
            return float(texto)
        except ValueError:
            return None

    @classmethod
    def _span_from(cls, obj):
        """O intervalo de tempo declarado num objeto, ou None se não houver.

        `start`/`end` dentro de um endereço de bloco são o momento do vídeo. É o
        que o modelo quer dizer quando devolve `{"start": 219.0, "end": 223.0,
        "text": "..."}`: aquele instante, não o bloco de índice 219.
        """
        if not isinstance(obj, dict):
            return None
        if "start" not in obj or "end" not in obj:
            return None
        start = cls._instant(obj["start"])
        end = cls._instant(obj["end"])
        if start is None or end is None or end <= start:
            return None
        return start, end

    def _blocks_for_span(self, all_blocks, start, end):
        """Os blocos editoriais que um intervalo de tempo cobre."""
        span = end - start
        hits = []
        for block in all_blocks:
            try:
                block_start = float(block["start"])
                block_end = float(block["end"])
            except (KeyError, TypeError, ValueError):
                continue
            overlap = min(block_end, end) - max(block_start, start)
            if overlap > self.SPAN_MATCH_S or (overlap > 0 and overlap >= 0.5 * span):
                hits.append(int(block["index"]))
        if hits:
            return hits
        # Um intervalo inteiramente dentro de um bloco pode não cruzar a borda de
        # nenhum outro; o bloco que contém o meio dele é a resposta.
        middle = (start + end) / 2
        for block in all_blocks:
            if float(block["start"]) <= middle < float(block["end"]):
                return [int(block["index"])]
        return []

    def _addressed_blocks(self, sel, all_blocks):
        """Os blocos que uma seleção do modelo aponta, em índice ou em tempo.

        O prompt pede índice (`"blocks": [3, 4, 5]`) e o modelo às vezes responde
        em tempo, que é o endereço mais direto que existe: o índice depende de como
        nós agrupamos as frases, o segundo não depende de nada. Recusar a resposta
        por causa da forma custou uma coletiva inteira — vinte e dois mil
        caracteres de análise descartados por um `dict` onde havia um `int`.

        Devolve `(índices, endereçado_por_tempo, motivo_da_recusa)`.
        """
        raw = sel.get("blocks", [])
        if not isinstance(raw, (list, tuple)):
            return None, False, "campo 'blocks' não é uma lista"

        if not raw:
            # Sem `blocks`, mas talvez com o intervalo no próprio objeto do clip.
            span = self._span_from(sel)
            if span is None:
                return None, False, "resposta sem blocos e sem intervalo de tempo"
            hits = self._blocks_for_span(all_blocks, *span)
            if not hits:
                return None, True, f"nenhum bloco no intervalo {span[0]:.1f}-{span[1]:.1f}s"
            return sorted(set(hits)), True, None

        indices = []
        by_time = False
        for item in raw:
            if isinstance(item, dict):
                span = self._span_from(item)
                if span is None:
                    return None, True, "endereço em forma de objeto sem start/end válidos"
                hits = self._blocks_for_span(all_blocks, *span)
                if not hits:
                    return None, True, f"nenhum bloco no intervalo {span[0]:.1f}-{span[1]:.1f}s"
                by_time = True
                indices.extend(hits)
            else:
                try:
                    indices.append(int(item))
                except (TypeError, ValueError):
                    return None, False, "índice de bloco não é um número"

        if by_time:
            # Intervalos vizinhos encostam no mesmo bloco o tempo todo; aqui a
            # repetição é geometria, não o modelo repetindo o índice.
            return sorted(set(indices)), True, None
        return indices, False, None

    def _parse_llm_response(self, response_text, sentences, all_blocks, chunk_offset,
                            source="llm", emit_progress=None):
        """Parse LLM/Gemini JSON response into clip data with timestamps."""
        rejections = []
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

            block_indices, addressed_by_time, rejection = self._addressed_blocks(sel, all_blocks)
            if block_indices is None:
                rejections.append(rejection or "endereço de bloco ilegível")
                continue
            if not addressed_by_time and len(set(block_indices)) != len(block_indices):
                rejections.append("o mesmo bloco foi listado duas vezes")
                continue

            if not addressed_by_time:
                zero_based_valid = all(0 <= index < len(all_blocks) for index in block_indices)
                one_based_valid = all(1 <= index <= len(all_blocks) for index in block_indices)
                # Our prompt exposes zero-based `BLOCO` indices. Only switch to
                # one-based when zero-based mapping is impossible, avoiding the old
                # silent off-by-one error for responses such as [1, 2].
                if not zero_based_valid and one_based_valid:
                    block_indices = [index - 1 for index in block_indices]
                elif not zero_based_valid:
                    rejections.append("índice de bloco fora da transcrição enviada")
                    continue

            ordered_indices = sorted(block_indices)
            if ordered_indices != list(range(ordered_indices[0], ordered_indices[-1] + 1)):
                # A model that skips a block skipped context; do not publish it.
                rejections.append("a seleção pula um bloco, e pular bloco é pular contexto")
                continue
            block_indices = ordered_indices
            valid_blocks = [all_blocks[index] for index in block_indices]
            if not valid_blocks:
                continue

            metadata = {
                "overlap_suspected": any(bool(block.get("overlap_suspected")) for block in valid_blocks),
                "timing_ambiguous": any(bool(block.get("timing_ambiguous")) for block in valid_blocks),
                "speaker_turn_valid": all(block.get("speaker_turn_valid", True) is not False for block in valid_blocks),
                "speaker_identity_required": bool(self._speaker_identity_required),
                "speaker_identity_available": all(bool(block.get("speaker_identity_available")) for block in valid_blocks),
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
                rejections.append(
                    f"trecho de {clip_duration:.0f}s, abaixo do mínimo de {self.min_duration:.0f}s"
                )
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
            if technical_flags.get("speaker_identity_review_required"):
                sel["review_required"] = True
                sel["review_reasons"] = list(sel.get("review_reasons") or [])
                sel["review_reasons"].append("identidade do locutor não confirmada para o foco Renan-first")

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

        if not clips and rejections and emit_progress:
            # "0 clips parsed" não dizia por quê, e a corrida caía para o NLP sem
            # que ninguém soubesse o que o modelo tinha respondido de errado.
            motivos = []
            for motivo in rejections:
                if motivo not in motivos:
                    motivos.append(motivo)
            emit_progress(
                f"[{source}] Resposta lida, {len(rejections)} seleção(oes) recusada(s): "
                + "; ".join(motivos[:3]),
                "warning",
            )

        return clips

    # ═══════════════════════════════════════════════════
    # NLP — Keyword-based fallback (always available)
    # ═══════════════════════════════════════════════════

    def _select_with_nlp(self, sentences, energy_profile, user_context, emit_progress, editorial_context=None):
        """NLP-based fallback when no AI backend is available."""
        if emit_progress:
            emit_progress("[NLP] Construindo clips com analise por palavras-chave...")

        # Aqui ninguém combina bloco: o bloco vira o corte, então ele é montado
        # do tamanho de um corte.
        blocks = self._build_transcript_blocks(sentences, granularity="clip")
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
        # O nome citado no contexto é preferência, nunca portão. Quem fala é
        # decidido pelo áudio e pelos turnos da entrevista; citar um nome no
        # texto significa que ALGUÉM FALOU DAQUELA PESSOA, que é quase o oposto.
        # Numa sabatina o entrevistado não diz o próprio nome nem o do canal, e
        # o descarte por citação apagava 12 dos 19 candidatos de uma fonte real.
        # _compute_context_score já dá +25 por nome e teto maior a quem cita.
        if context_data and context_data["names"] and emit_progress:
            citam = sum(
                1 for clip in clips
                if any(name in clip["text"].lower() for name in context_data["names"])
            )
            emit_progress(
                f"[NLP] {citam} de {len(clips)} candidatos citam o contexto; "
                f"eles sobem no ranqueamento, os outros continuam disponíveis."
            )

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

    def _trim_opening_fragment(self, clips, emit_progress=None, sentences=None):
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
        cased = self._casing_is_meaningful(sentences)
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
            # Landing on a sentence is not the same as landing on a beginning.
            # Measured on the Metrópoles interview, this pass moved four of the
            # eight rendered clips onto "Ela só tá iludida...", "E aí o deputado
            # então...", "você cria uma...", "Então este reconhecimento..." — a
            # whole sentence every time, and every time a sentence leaning on the
            # one before it. The editor read all four back as "começa no meio da
            # fala e não dá contexto". Where the remainder does not open a
            # thought, the boundary is left alone for the rewind below, which can
            # go back to where the thought started instead of forward past it.
            if not self._opens_a_thought(text[offset:], cased):
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
                # A continuidade tem de valer em cada passo, não só no primeiro.
                # Exigi-la apenas enquanto nada tinha sido tomado deixava o laço
                # atravessar buracos de qualquer tamanho depois da primeira frase,
                # emendando material que não é a resposta daquela pergunta.
                if sentence_start > new_end + 3.0:
                    break
                if classify_broadcast_boundary(str(sentence.get("text") or "")) is not None:
                    break
                # E o alongamento precisa de teto próprio. O único limite era a
                # duração máxima técnica, de dez minutos: numa coletiva real isso
                # esticou um corte em 157 segundos. Mostrar que a resposta começou
                # é o suficiente; a resposta inteira é outro corte.
                if sentence_end - end > self.MAX_ANSWER_EXTENSION_S:
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

    @staticmethod
    def _add_review_reason(clip, code, message=None):
        """Attach a stable review code without erasing existing explanations."""
        if not isinstance(clip, dict):
            return
        codes = clip.get("review_reason_codes")
        if not isinstance(codes, list):
            codes = []
        if code not in codes:
            codes.append(str(code)[:80])
        clip["review_reason_codes"] = codes[:12]
        clip["review_required"] = True
        if message:
            reasons = clip.get("review_reasons")
            if not isinstance(reasons, list):
                reasons = []
            if message not in reasons:
                reasons.append(message)
            clip["review_reasons"] = reasons[:12]

    @staticmethod
    def _broadcast_turns(sentences):
        """Return hard transmission boundaries detected in the transcript."""
        return [
            turn for turn in detect_interviewer_turns(sentences or [])
            if turn.get("hard_boundary")
        ]

    @classmethod
    def _broadcast_boundary_between(cls, start, end, boundaries):
        """Return a hard break overlapping ``start``–``end``, if one exists."""
        for turn in boundaries or []:
            boundary_start = float(turn.get("start_s", 0) or 0)
            boundary_end = float(turn.get("end_s", boundary_start) or boundary_start)
            if end > boundary_start + cls.BROADCAST_BOUNDARY_PAD_S and start < boundary_end - cls.BROADCAST_BOUNDARY_PAD_S:
                return turn
        return None

    @staticmethod
    def _first_sentence_after_boundary(sentences, boundary_end):
        """Find the first transcript sentence after a return announcement."""
        ordered = sorted(sentences or [], key=lambda item: float(item.get("start", 0) or 0))
        for item in ordered:
            start = float(item.get("start", 0) or 0)
            if start + 0.25 < boundary_end:
                continue
            if classify_broadcast_boundary(str(item.get("text") or "")) is not None:
                continue
            return start
        return None

    @staticmethod
    def _is_stabilized_response_opener(text):
        """Recognize a generic verbal cue that the guest starts answering."""
        normalized = " ".join(str(text or "").lower().split())
        return bool(re.search(
            r"\b(?:vou|vamos|a gente vai|eu vou)\b[^.!?]{0,44}"
            r"\b(?:dar um exemplo|responder|explicar|mostrar|por partes|um a um|de um a um)\b"
            r"|\b(?:primeiro|segundo|terceiro)\s+(?:ponto|exemplo|caso)\b",
            normalized,
        ))

    @classmethod
    def _stabilized_response_start(cls, sentences, after_s, before_s, minimum_start_s=None):
        """Find a semantic response opener after repeated interviewer noise."""
        ordered = sorted(sentences or [], key=lambda item: float(item.get("start", 0) or 0))
        for item in ordered:
            start = float(item.get("start", 0) or 0)
            if start < after_s - 0.25 or start >= before_s:
                continue
            text = str(item.get("text") or "")
            if classify_broadcast_boundary(text) is not None or is_interviewer_sentence(text):
                continue
            if cls._is_stabilized_response_opener(text):
                normalized = " ".join(text.lower().split())
                marker_positions = [
                    normalized.find(marker)
                    for marker in (
                        "dar um exemplo", "responder", "explicar", "mostrar",
                        "por partes", "um a um", "de um a um",
                    )
                    if normalized.find(marker) >= 0
                ]
                # "Por exemplo? ... eu vou dar um exemplo" is still the
                # interrupted handover, not a stable opening. A cue with no
                # question before it is the first self-directed explanation.
                if marker_positions and "?" in normalized[:min(marker_positions)]:
                    continue
                if minimum_start_s is not None and start - minimum_start_s < cls.MIN_STABILIZED_OPENING_SHIFT_S:
                    continue
                return start
        return None

    def _evaluate_interview_boundaries(self, clips, sentences, emit_progress=None):
        """Annotate question-only openings and unfinished/interrupted endings.

        This is deliberately a review/defer pass, not a new ranking model. It
        distinguishes a question at the start from a response that follows it,
        and distinguishes an answer cut just before a new question from one cut
        inside an interruption. A teaser mode is not enabled by default, so a
        question-only candidate is deferred rather than rendered as a clip.
        """
        if not clips or not sentences:
            return clips
        turns = detect_interviewer_turns(sentences)
        if not turns:
            return clips

        changed = 0
        for clip in clips:
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", start) or start)
            if end <= start:
                continue
            boundaries = [turn for turn in turns if turn.get("hard_boundary")]
            crossed = self._broadcast_boundary_between(start, end, boundaries)
            if crossed:
                clip["contains_broadcast_break"] = True
                self._add_review_reason(
                    clip,
                    "broadcast_break",
                    "a janela ainda toca uma chamada ou retorno de intervalo",
                )
                changed += 1

            visible_turns = [
                turn for turn in turns
                if not turn.get("hard_boundary")
                and turn["start_s"] < end + 0.35
                and turn["end_s"] > start - 0.35
            ]
            first_turn = visible_turns[0] if visible_turns else None
            opening_sentence = next(
                (
                    sentence for sentence in sorted(
                        sentences, key=lambda item: float(item.get("start", 0) or 0)
                    )
                    if abs(float(sentence.get("start", 0) or 0) - start) <= 0.75
                ),
                None,
            )
            opening_is_interviewer = bool(
                opening_sentence
                and is_interviewer_sentence(str(opening_sentence.get("text") or ""))
            )
            starts_with_question = bool(
                first_turn
                and first_turn["start_s"] <= start + 0.75
                and (
                    first_turn.get("asks_a_whole_question")
                    or opening_is_interviewer
                )
            )
            if starts_with_question:
                last_question = first_turn
                answer_words = 0
                answer_start = None
                question_end = float(last_question.get("question_end_s", last_question.get("end_s", 0)) or 0)
                for sentence in sorted(sentences, key=lambda item: float(item.get("start", 0) or 0)):
                    sentence_start = float(sentence.get("start", 0) or 0)
                    sentence_end = float(sentence.get("end", sentence_start) or sentence_start)
                    if sentence_end <= question_end or sentence_start >= end:
                        continue
                    if classify_broadcast_boundary(str(sentence.get("text") or "")) is not None:
                        continue
                    if is_interviewer_sentence(str(sentence.get("text") or "")):
                        continue
                    if answer_start is None:
                        answer_start = sentence_start
                    answer_words += len(str(sentence.get("text") or "").split())
                clip["starts_with_interviewer_question"] = True
                clip["answer_words_after_last_question"] = answer_words
                clip["question_answer_substantial"] = answer_words >= self.MIN_SUBSTANTIAL_ANSWER_WORDS
                clip["question_answer_complete"] = bool(
                    clip.get("question_answer_complete") and answer_words >= self.MIN_ANSWER_WORDS
                )
                if answer_start is not None:
                    clip["answer_start_after_question_s"] = round(answer_start, 3)
                if answer_words < self.MIN_SUBSTANTIAL_ANSWER_WORDS:
                    clip["starts_with_question_only"] = True
                    clip["context_complete"] = False
                    self._add_review_reason(
                        clip,
                        "starts_with_question_only",
                        "a pergunta abre a janela, mas a resposta ainda não tem extensão substancial",
                    )
                    changed += 1

            ending_turn = next(
                (
                    turn for turn in reversed(visible_turns)
                    if turn["start_s"] < end - 0.35 < turn["end_s"] + 0.35
                ),
                None,
            )
            if ending_turn:
                clip["ends_at_interviewer_turn"] = True
                new_turn_inside_window = ending_turn["start_s"] > start + 0.75
                interrupted = bool(ending_turn.get("interjection") or new_turn_inside_window)
                code = "ending_interruption" if interrupted else "ends_at_interviewer_turn"
                if interrupted:
                    clip["ending_interruption"] = True
                    clip["payoff_complete"] = False
                    self._add_review_reason(
                        clip,
                        code,
                        "o corte termina dentro de uma intervenção/pergunta nova antes do desfecho",
                    )
                else:
                    self._add_review_reason(
                        clip,
                        code,
                        "o corte termina dentro da retomada do entrevistador; confirme o fechamento no vídeo",
                    )
                changed += 1

        if changed and emit_progress:
            emit_progress(
                f"[Fronteiras] {changed} candidato(s) receberam sinal de pergunta, intervalo ou interrupção para revisão.",
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
        starts = [float(item.get("start", 0) or 0) for item in sentences if item.get("start") is not None]
        ends = [float(item.get("end", 0) or 0) for item in sentences if item.get("end") is not None]
        span = max(0.0, max(ends, default=0.0) - min(starts, default=0.0))
        if not looks_like_an_interview(turns, span) and not any(
            turn.get("hard_boundary") for turn in turns
        ):
            return clips

        # A clip may end where the interviewer speaks — but not on an aside the
        # guest talks straight through, or it stops in the middle of the answer.
        seams = [turn["start_s"] for turn in turns if not turn["interjection"]]
        majors = [turn["start_s"] for turn in turns if turn["major"]]
        broadcast_boundaries = [turn for turn in turns if turn.get("hard_boundary")]
        if not seams:
            return clips

        self._candidate_diagnostics.update({
            "interview_turns": len(turns),
            "interview_seams": len(seams),
            "interview_major_turns": len(majors),
            "broadcast_break_count": len(broadcast_boundaries),
        })

        # Before the interviewer first addresses the guest, the broadcast is
        # presenting itself: the anchor reads the running order and names who is
        # coming. It is speech, it transcribes cleanly, and it is not a clip —
        # the guest has not said a word yet. One run rendered exactly that as its
        # fifth clip, fifty-two seconds of the studio introducing the programme.
        #
        # This only holds when the transcript really begins at the top of the
        # source. Given an excerpt that opens in the middle of an answer, the
        # first turn found is just the next question, and everything before it is
        # the guest talking — dropping that would throw away the material.
        opens_the_source = min(
            (float(item.get("start", 0) or 0) for item in sentences), default=0.0
        ) <= 30.0
        handover = first_address_to_guest(sentences)
        content_start = handover if (opens_the_source and handover is not None) else 0.0

        kept, dropped = [], 0
        for clip in clips or []:
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            if end <= start:
                kept.append(clip)
                continue
            original_start, original_end = start, end
            viable = max(self.min_duration, (original_end - original_start) * 0.5)
            crossed_broadcast = None
            candidate_dropped = False

            # A break is not an ordinary major question. It is a region with no
            # editorial answer, and a candidate must remain entirely on one side
            # of it. If the original window starts in the call/vinheta, prefer the
            # first real question after the return; if it starts before the call,
            # keep the pre-break answer and trim its tail at the hard boundary.
            for boundary in broadcast_boundaries:
                boundary_start = float(boundary.get("start_s", 0) or 0)
                boundary_end = float(boundary.get("end_s", boundary_start) or boundary_start)
                if end <= boundary_start + self.BROADCAST_BOUNDARY_PAD_S:
                    continue
                if start >= boundary_end - self.BROADCAST_BOUNDARY_PAD_S:
                    continue
                crossed_broadcast = boundary
                after_return = self._first_sentence_after_boundary(sentences, boundary_end)
                if start < boundary_start - self.BROADCAST_BOUNDARY_PAD_S:
                    end = min(end, boundary_start)
                    side = "before_break"
                else:
                    if after_return is None:
                        self._record_hard_negative(
                            clip,
                            "broadcast_break",
                            details={"boundary_start": round(boundary_start, 3), "boundary_end": round(boundary_end, 3)},
                        )
                        dropped += 1
                        candidate_dropped = True
                        break
                    start = max(start, after_return)
                    side = "after_return"
                if end - start < viable or end - start < self.min_duration:
                    self._record_hard_negative(
                        clip,
                        "broadcast_break",
                        details={
                            "boundary_start": round(boundary_start, 3),
                            "boundary_end": round(boundary_end, 3),
                            "side": side,
                            "remaining_duration": round(max(0.0, end - start), 3),
                        },
                    )
                    dropped += 1
                    candidate_dropped = True
                    crossed_broadcast = None
                    break
            if candidate_dropped:
                continue
            if crossed_broadcast is not None:
                self._candidate_diagnostics["broadcast_break_candidates_adjusted"] = int(
                    self._candidate_diagnostics.get("broadcast_break_candidates_adjusted", 0) or 0
                ) + 1
            if start < content_start - 0.5:
                if end - content_start < max(self.min_duration, (end - start) * 0.5):
                    dropped += 1
                    continue
                start = content_start

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
                # Never back past the handover. A turn can begin before the
                # programme has handed over — the anchor is still presenting —
                # and snapping onto it undoes the guard applied just above,
                # which is how a clip came to open on the studio reading the
                # running order.
                start = max(opening[-1]["start_s"], content_start)

            # A window that opens a few seconds before the next question is
            # carrying the tail of the previous answer — the "it started in the
            # middle of a sentence" complaint. There is no clip in those seconds,
            # so the clip starts at the question instead.
            # If the window opens exactly on a short interviewer aside, do not
            # publish the noisy handover as the hook. Advance to the first stable
            # response cue only when it is materially later and leaves a viable
            # answer. This is intentionally language-pattern based, never a
            # timestamp for the Renan source.
            entry_interjection = next(
                (
                    turn for turn in turns
                    if turn.get("interjection")
                    and turn["start_s"] - 0.75 <= start < turn["end_s"] + 0.25
                ),
                None,
            )
            stabilized_opening = False
            if entry_interjection:
                stable = self._stabilized_response_start(
                    sentences,
                    float(entry_interjection.get("end_s", start) or start),
                    end,
                    minimum_start_s=start,
                )
                if stable is not None and stable - start >= self.MIN_STABILIZED_OPENING_SHIFT_S:
                    if end - stable >= self.min_duration:
                        start = stable
                        clip["opening_stabilized_after_interruption_s"] = round(
                            stable - original_start, 3
                        )
                        clip["opening_source"] = "resposta estabilizada após intervenção"
                        stabilized_opening = True
                        self._candidate_diagnostics["stabilized_openings"] = int(
                            self._candidate_diagnostics.get("stabilized_openings", 0) or 0
                        ) + 1

            ahead = [seam for seam in majors if start < seam < start + self.min_duration]
            if ahead:
                start = ahead[0]

            # Once a noisy aside has been replaced by a stable answer opener,
            # the next identified whole question is a clean end for this answer.
            # This trims the tail without claiming that the preceding answer was
            # complete or deleting the next question's reusable inventory.
            if stabilized_opening:
                next_follow_up = next(
                    (
                        turn["start_s"] for turn in turns
                        if not turn.get("hard_boundary")
                        and turn.get("asks_a_whole_question")
                        and turn["start_s"] >= start + self.min_duration
                        and turn["start_s"] < end - 1.0
                    ),
                    None,
                )
                if next_follow_up is not None and next_follow_up - start >= self.min_duration:
                    end = next_follow_up
                    clip["ending_follow_up_boundary_s"] = round(next_follow_up, 3)

            # A subject change inside the window is not negotiable: the clip ends
            # there even if that costs it the slot. A hard broadcast region was
            # handled above and must not be reconsidered as an ordinary question.
            crossed = [
                seam for seam in majors
                if start + 1.0 < seam < end - 1.0
                and not any(abs(seam - float(boundary.get("start_s", 0) or 0)) < 0.05 for boundary in broadcast_boundaries)
            ]
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
                "crossed_broadcast_break": bool(crossed_broadcast),
            }
            if crossed_broadcast:
                self._add_review_reason(
                    clip,
                    "broadcast_break",
                    "a borda foi ajustada para não atravessar uma chamada/retorno de intervalo",
                )
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

    @staticmethod
    def _casing_is_meaningful(sentences):
        """Whether an initial capital in this transcript means anything.

        Whisper and imported captions punctuate and capitalise, so a sentence
        opening in lower case is continuing the one before it. Other tools emit
        everything in lower case, and there the same test would condemn every
        sentence in the source and rewind every clip to the first second. The
        share of capitalised openings separates the two cases without anybody
        having to declare which transcriber was used.
        """
        firsts = [
            str(item.get("text") or "").strip()[:1]
            for item in sentences or []
            if str(item.get("text") or "").strip()
        ]
        firsts = [char for char in firsts if char.isalpha()]
        if len(firsts) < 8:
            return False
        return sum(1 for char in firsts if char.isupper()) / len(firsts) >= 0.6

    @staticmethod
    def _opens_a_thought(text, cased=False):
        """Whether a sentence can be the first thing the viewer hears.

        Three things disqualify it. Two are already named at the top of this
        module, because the gates use them to *flag* the defect: a conjunction
        continuing the previous sentence ("e", "mas", "então"), and a pronoun
        pointing at something said before it ("isso", "ela", "por isso").

        The third is the one that let four bad clips through on the Metrópoles
        interview. "premiando por boas práticas" is neither a conjunction nor a
        pronoun, so both lists cleared it — and it is the tail end of a sentence
        that began fifteen words earlier. What gives it away is the lower-case
        first letter, and that test is only trustworthy on a transcript that
        capitalises at all, which ``_casing_is_meaningful`` decides.

        Discourse openers the guest uses to turn to the camera — "Veja,",
        "Olha," — are not continuations: they introduce their own subject, and a
        clip that begins on one of them reads as a beginning.
        """
        raw = str(text or "").strip()
        if not raw:
            return False
        if cased and raw[:1].isalpha() and raw[:1].islower():
            return False
        words = re.findall(r"[\wÀ-ÿ-]+", raw.lower())
        if not words:
            return False
        first = words[0]
        pair = " ".join(words[:2]) if len(words) >= 2 else first
        if first in {item.lower() for item in CONTINUATION_STARTERS_PT}:
            return False
        references = {item.lower() for item in CONTEXT_REFERENCE_STARTERS_PT}
        if first in references or pair in references:
            return False

        # As cinco categorias medidas na corrida da PENÉLOPE, onde as onze
        # aberturas passavam por aqui. Ver o bloco de constantes lá em cima para
        # por que cada uma é gramática e não assunto.

        # "Agora eu não sei o que que vocês estão avaliando" — contraste com o
        # que veio antes.
        if first in CONTRAST_OPENERS_PT:
            return False

        # "Somando tudo a três pontos" — oração gerundiva é subordinada por
        # construção: ela modifica uma principal que ficou de fora.
        if len(first) > 4 and first.endswith("ndo"):
            return False

        primeira_oracao = words[:FIRST_CLAUSE_WORDS]

        # "O Renan também criticou Flávio Bolsonaro" — o "além de" ficou atrás.
        if any(palavra in ADDITIVE_ADVERBS_PT for palavra in primeira_oracao):
            return False

        # "Quatro debates organizados aí." — o dêitico só aponta se estiver no
        # fim da oração; "lá em Brasília" carrega o próprio referente.
        fim_da_oracao = re.split(r"[.!?,;:]", raw, maxsplit=1)[0]
        palavras_da_oracao = re.findall(r"[\wÀ-ÿ-]+", fim_da_oracao.lower())
        if len(palavras_da_oracao) >= 2 and palavras_da_oracao[-1] in POINTING_ADVERBS_PT:
            return False

        # "Está certo?" — fragmento curto que responde a algo que ficou atrás.
        # Uma pergunta longa é hook e continua valendo como abertura.
        if raw.rstrip().endswith("?") and len(words) <= 3:
            return False

        return True

    def _close_where_the_thought_ends(self, clips, sentences, emit_progress=None):
        """Espelho do recuo de abertura, do outro lado da borda.

        O corte fechava onde o *bloco* fechava. Medido contra as fronteiras
        humanas do Acervo, o podcast — a única das três fontes onde a conversa
        não tem costura detectável — entregava 39s onde o rotulador implica 94s:
        ali o corte é um bloco, e o bloco fecha pelo relógio. É a queixa mais
        teimosa do editor, "ele parece não concluir o tema", e o comentário do
        módulo promete o contrário desde sempre sem nunca cumprir.

        A regra é gramática, não tópico. A abertura recua enquanto o texto não
        *começa* um pensamento; o fecho avança enquanto o texto seguinte não
        *consegue começar* um. Um trecho que abre com "e", "mas", "então", "aí"
        ou "porque" é por construção a continuação do anterior: deixá-lo de fora
        para um corte no meio do raciocínio, e deixá-lo virar corte próprio abre
        um no meio dele — as duas queixas, a mesma fronteira.

        Antes de escrever isto eu medi a alternativa. Coesão léxica entre blocos
        vizinhos (TextTiling, o método clássico) acerta a direção mas separa
        fraco demais — +0,04 a +0,09 de diferença, com três travessias de
        amostra —, e um limiar ali seria ajuste a ruído. A muleta de conversa, no
        podcast, aparece em 59% dos pares dentro do mesmo território e em
        nenhuma das travessias.

        O avanço para na primeira frase que se sustenta sozinha, na palavra do
        entrevistador (quem responde terminou quando quem pergunta retoma) e no
        limite duro de duração. O orçamento do avanço é um teto preferencial de
        material a mais — a mesma grandeza que a régua mediu, em vez de mais um
        número inventado.
        """
        if not sentences or not clips:
            return clips
        ordered = sorted(sentences, key=lambda item: float(item.get("start", 0) or 0))
        cased = self._casing_is_meaningful(ordered)
        extended = 0

        for clip in clips:
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            if end <= start:
                continue

            # O orçamento do avanço é um teto preferencial de material — a mesma
            # grandeza que a régua mediu, em vez de mais um número inventado. Um
            # corte que fecha onde o bloco fechava pode assim chegar ao dobro do
            # teto quando o raciocínio de fato corre longo, e o limite duro
            # continua sendo a palavra final.
            ceiling = min(
                start + self.max_duration,
                end + self.preferred_max_duration,
            )
            target = end
            for item in ordered:
                item_start = float(item.get("start", 0) or 0)
                item_end = float(item.get("end", 0) or 0)
                if item_start < target - 0.25:
                    continue
                text = str(item.get("text") or "")
                # A palavra do entrevistador fecha o raciocínio de quem responde.
                if is_interviewer_sentence(text):
                    break
                # Uma frase que se sustenta sozinha é o próximo assunto, não a
                # continuação deste.
                if self._opens_a_thought(text, cased):
                    break
                if item_end > ceiling:
                    break
                target = item_end

            if target > end + 0.05:
                clip["end"] = round(target, 3)
                clip["duration"] = round(target - start, 3)
                moved = self._text_between(ordered, start, target)
                if moved:
                    clip["text"] = moved
                clip["closing_extended_s"] = round(target - end, 3)
                extended += 1

        if extended and emit_progress:
            emit_progress(
                f"[Fecho] {extended} corte(s) estendido(s) até o raciocínio fechar, "
                "em vez de pararem onde o bloco parava.",
                "info",
            )
        return clips

    @staticmethod
    def _turn_starts_here(sentence):
        """O arquivo marcou troca de locutor no começo desta frase.

        A marca vale para o começo, não para qualquer lugar dela: uma frase
        montada pode carregar marca no meio — quando o repórter corta e devolve
        a palavra dentro da mesma linha de legenda — e isso não faz dela o
        início de um turno.
        """
        start = float(sentence.get("start", 0) or 0)
        if sentence.get("speaker_change"):
            return True
        return any(
            abs(float(instante) - start) < 0.35
            for instante in sentence.get("speaker_change_at") or []
        )

    def _question_marked_just_before(self, ordered, index, floor):
        """A pergunta que este corte responde, quando o arquivo a marcou.

        O recuo de abertura procura onde o *raciocínio* começa, e por isso não
        toca numa resposta que se sustenta sozinha: "Falando a verdade, eu não
        vou abrir concessão" é uma frase inteira, nada nela indica que falta
        algo. E falta — a pergunta, seis segundos atrás.

        O que indica isso não está no texto da resposta, está na marca: o
        arquivo diz que quem fala mudou ali, e que o turno anterior é uma
        pergunta inteira. Nesse caso o corte abre na pergunta, que é o setup
        dele. Um turno, nunca dois: duas trocas atrás já é outra conversa.
        """
        if index <= 0:
            return None
        opening = ordered[index]
        if not self._turn_starts_here(opening):
            return None

        # O turno anterior inteiro, e não a frase anterior. Uma pergunta de
        # coletiva quase nunca cabe numa frase só — "como vai desenvolver sua
        # campanha frente a candidatos que já têm experiência nas urnas, né? /
        # Como chegar mais no país." são duas, e recuar só até a segunda abriria
        # o corte na metade da pergunta, que é pior do que abrir na resposta.
        fim = index
        while fim > 0:
            position = fim - 1
            while position > 0 and not self._turn_starts_here(ordered[position]):
                position -= 1
            if not self._turn_starts_here(ordered[position]):
                return None

            # Pergunta inteira, ou alguém se dirigindo ao entrevistado. A
            # segunda forma existe porque metade das perguntas de coletiva não é
            # uma frase interrogativa: "A pergunta é, o senhor foi com a parada
            # de segurança para" não tem ponto de interrogação nem abre com
            # pronome interrogativo, e é exatamente a pergunta que o corte de
            # 12:39 estava deixando de fora. O que a identifica é o tratamento —
            # "o senhor" —, e isso já está medido em `is_interviewer_sentence`.
            textos = [str(item.get("text") or "") for item in ordered[position:fim]]
            if any(is_a_whole_question(t) or is_interviewer_sentence(t) for t in textos):
                start = float(ordered[position].get("start", 0) or 0)
                if start < floor:
                    return None
                if float(opening.get("start", 0) or 0) - start > self.MAX_QUESTION_SETUP_S:
                    return None
                return start

            # Um "Sim, sim." entre a pergunta e a resposta é aceite de palavra,
            # não é a conversa mudando de assunto — e na coletiva ele fica entre
            # a pergunta do repórter e a resposta que este corte carrega. Passar
            # por cima dele não é atravessar dois turnos; é ignorar um turno que
            # não diz nada. Qualquer coisa maior que isso é outra conversa e o
            # recuo para ali.
            if not self._is_acknowledgement(textos):
                return None
            fim = position
        return None

    # Aceite de palavra: curto, sem pergunta e sem conteúdo próprio.
    ACKNOWLEDGEMENT_MAX_WORDS = 5

    @classmethod
    def _is_acknowledgement(cls, textos):
        juntas = " ".join(texto.strip() for texto in textos).strip()
        if not juntas or "?" in juntas:
            return False
        return len(re.findall(r"[^\W\d_]+", juntas, flags=re.UNICODE)) <= cls.ACKNOWLEDGEMENT_MAX_WORDS

    @staticmethod
    def _announces_a_new_subject(text):
        """A última frase ABRE um assunto em vez de fechar este?

        É o pior fim possível, e o mais difícil de ver: gramaticalmente ela está
        perfeita — sujeito, verbo, ponto final —, então `payoff_complete` diz que
        está tudo certo. O problema não é a forma, é a função. Ela promete um
        desenvolvimento que o corte não entrega.

        Medido nos cortes reais do editor:

            #9 termina em "Eu tive essa experiência uma vez no Arontalcus."
            e ele relatou outro terminando em "segundo ponto:"

        Nos dois casos o espectador fica esperando o que vem depois. O editor:
        "ele parece não concluir o tema".

        O detector é deliberadamente ESTREITO. Um fim bom também é uma frase que
        se sustenta sozinha, então "se sustenta sozinha" não separa nada — foi
        por isso que o avanço, que usa esse critério, nunca pegou o caso. O que
        separa é a marca de anúncio: uma enumeração pendurada, ou um caso novo
        sendo apresentado com referente indefinido.

        Preferi deixar passar um fim ruim a cortar um fim bom. "Eu vou falar do
        que quiser." (#8) é um fecho ótimo e cai bem perto destas regras; ele
        continua de fora porque não anuncia nada.
        """
        raw = str(text or "").strip()
        if not raw:
            return False
        normalizado = raw.lower()

        # Enumeração pendurada: "segundo ponto:", "primeiro:", "outra coisa:".
        if raw.rstrip().endswith(":"):
            return True
        if re.match(
            r"^(primeiro|segundo|terceiro|quarto|quinto|outro|outra|mais um|mais uma)\b"
            r".{0,24}\b(ponto|coisa|questao|questão|exemplo|caso)\b",
            normalizado,
        ):
            return True

        # Caso novo sendo apresentado. "uma vez" é a marca clássica de abertura
        # de causo, e "teve um/uma" apresenta referente indefinido — as duas
        # anunciam o que viria a seguir.
        if re.search(r"\buma vez\b", normalizado):
            return True
        if re.match(r"^(teve|tinha|houve)\s+(um|uma)\b", normalizado):
            return True

        return False

    def _trim_trailing_announcement(self, clips, sentences, emit_progress=None):
        """Tira do fim a frase que anuncia um assunto novo.

        O avanço (`_close_where_the_thought_ends`) só sabe somar material. Quando
        o rabo já nasceu dentro do bloco, nenhum passo o removia.

        Corta no máximo UMA frase, e só se o que sobra continua sendo um corte
        de verdade. Isto nunca faz um corte desaparecer: um corte encurtado
        continua existindo, e a guarda de duração mínima impede que ele encolha
        até cair no chão da renderização.
        """
        if not sentences or not clips:
            return clips
        ordered = sorted(sentences, key=lambda item: float(item.get("start", 0) or 0))
        aparados = 0

        for clip in clips:
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            if end <= start:
                continue
            dentro = [
                item for item in ordered
                if float(item.get("start", 0) or 0) >= start - 0.25
                and float(item.get("end", 0) or 0) <= end + 0.25
            ]
            # Com menos de duas frases não há rabo para tirar: o que sobraria
            # seria o corte inteiro.
            if len(dentro) < 2:
                continue
            ultima = dentro[-1]
            if not self._announces_a_new_subject(ultima.get("text")):
                continue
            novo_fim = float(dentro[-2].get("end", 0) or 0)
            if novo_fim <= start or (novo_fim - start) < self.min_duration:
                continue

            clip["end"] = round(novo_fim, 3)
            clip["duration"] = round(novo_fim - start, 3)
            refeito = self._text_between(ordered, start, novo_fim)
            if refeito:
                clip["text"] = refeito
            clip["closing_trimmed_s"] = round(end - novo_fim, 3)
            clip["closing_trim_reason"] = "a última frase abria um assunto novo"
            aparados += 1

        if aparados and emit_progress:
            emit_progress(
                f"[Fecho] {aparados} corte(s) perderam a última frase por ela abrir "
                "um assunto novo em vez de fechar este.",
                "info",
            )
        return clips

    def _open_where_the_thought_begins(self, clips, sentences, emit_progress=None):
        """Make every clip start where somebody starts saying something.

        The turn alignment above puts a boundary on a question when the window
        already lands near one. It has nothing to say about the far more common
        shape the editor reported on five consecutive clips: the window opens
        deep inside an answer, tens of seconds from any turn, so nothing moves
        it and the clip begins mid-sentence — "começa no meio da fala", "sem
        contexto suficiente".

        The repair is the smallest one that fixes it. The end is never touched,
        because on the same five clips the endings were right. Only the start
        moves, and only backwards to where the sentence — or the thought that
        sentence continues — began. Rewinding is bounded twice: by
        ``MAX_OPENING_REWIND_S`` and by the preferred duration ceiling, so a clip
        never grows into a different clip while looking for its beginning.

        A rewind stops as soon as it reaches solid ground: the interviewer's
        turn (the answer begins the instant the question ends), a real pause, or
        a sentence that already stands on its own. When rewinding is not
        affordable the start goes *forward* instead, onto the next sentence
        boundary, so the clip still opens on a whole sentence — shorter, but
        never broken.
        """
        if not sentences:
            return clips
        ordered = sorted(sentences, key=lambda item: float(item.get("start", 0) or 0))
        starts = [float(item.get("start", 0) or 0) for item in ordered]
        cased = self._casing_is_meaningful(ordered)
        repaired = 0

        for clip in clips or []:
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", 0) or 0)
            if end - start <= self.min_duration:
                continue

            # The sentence the start falls in, or the first one after it.
            index = None
            for position, item in enumerate(ordered):
                if float(item.get("start", 0) or 0) - 0.25 <= start < float(item.get("end", 0) or 0):
                    index = position
                    break
            forward_only = index is None
            if forward_only:
                index = next((position for position, value in enumerate(starts) if value >= start - 0.25), None)
                if index is None:
                    continue

            mid_sentence = starts[index] < start - 0.35

            # O recuo mede contra o limite duro, não contra o teto preferencial.
            # O teto é suave exatamente para este caso: o NORTE autoriza passar
            # dele "quando encurtar destruir a pergunta, a resposta, a prova, o
            # argumento ou a conclusão", e abrir num "E" pendurado é destruir o
            # setup. Quando o teto caiu de 180s para 60s — medido, não achado —,
            # amarrar o recuo ao preferencial teria comprado corte curto ao preço
            # de corte que abre no meio da frase, que é a queixa mais antiga do
            # editor. O `MAX_OPENING_REWIND_S` continua limitando quanto se
            # recua; o que muda é só quem paga a conta.
            floor = max(start - self.MAX_OPENING_REWIND_S, end - self.max_duration)

            if not mid_sentence:
                # Antes de dar o corte por bem aberto: o arquivo pode dizer que
                # a pergunta está logo atrás. Isso vale mesmo quando a frase de
                # abertura se sustenta sozinha — é justamente aí que o defeito
                # se esconde.
                pergunta = self._question_marked_just_before(ordered, index, floor)
                if pergunta is not None and end - pergunta >= self.min_duration:
                    clip["start"] = round(pergunta, 3)
                    clip["duration"] = round(end - pergunta, 3)
                    rebuilt = self._text_between(sentences, pergunta, end)
                    if rebuilt:
                        clip["text"] = rebuilt
                    clip["opening_repaired_s"] = round(pergunta - start, 2)
                    clip["opening_source"] = "pergunta marcada"
                    repaired += 1
                    continue
                # A clip already opening on the interviewer is opening on the
                # question, and the answer follows inside it. That is a shape the
                # editor approved — the turn alignment puts boundaries there on
                # purpose — so it is left exactly where it is.
                if is_interviewer_sentence(str(ordered[index].get("text") or "")):
                    continue
                if self._opens_a_thought(ordered[index].get("text"), cased):
                    continue

            target = index
            while starts[target] >= floor:
                item = ordered[target]
                # Reaching the question is reaching solid ground: the clip opens
                # on what was asked and carries the answer to it.
                if is_interviewer_sentence(str(item.get("text") or "")):
                    break
                if self._opens_a_thought(item.get("text"), cased):
                    break
                if target == 0:
                    break
                previous = ordered[target - 1]
                # Do not rewind across a broadcast gap. The return is a new
                # editorial segment, even when the transcript has no silence.
                crosses_broadcast = any(
                    float(previous.get("end", 0) or 0) <= float(boundary.get("start_s", 0) or 0) + self.BROADCAST_BOUNDARY_PAD_S
                    and float(item.get("start", 0) or 0) >= float(boundary.get("end_s", 0) or 0) - self.BROADCAST_BOUNDARY_PAD_S
                    for boundary in self._broadcast_turns(ordered)
                )
                if crosses_broadcast or starts[target] - float(previous.get("end", 0) or 0) >= self.OPENING_PAUSE_S:
                    break
                target -= 1

            new_start = starts[target]
            if new_start < floor or (mid_sentence and forward_only):
                new_start = None
            if new_start is None or new_start > start + 0.05:
                # Rewinding is not affordable, or the walk landed ahead of where
                # the clip already began: open on the next whole sentence.
                ahead = next(
                    (value for value in starts if start + 0.35 < value <= start + self.MAX_OPENING_TRIM_S),
                    None,
                )
                if ahead is None or end - ahead < self.min_duration:
                    continue
                new_start = ahead

            if abs(new_start - start) < 0.35 or end - new_start < self.min_duration:
                continue

            clip["start"] = round(new_start, 3)
            clip["duration"] = round(end - new_start, 3)
            rebuilt = self._text_between(sentences, new_start, end)
            if rebuilt:
                clip["text"] = rebuilt
            clip["opening_repaired_s"] = round(new_start - start, 2)
            repaired += 1

        if repaired and emit_progress:
            emit_progress(
                f"[Início] {repaired} corte(s) abriam no meio da fala; a borda recuou até "
                "onde o raciocínio começa.",
                "info",
            )
        return clips

    def _refine_boundaries_with_words(self, clips, segments, emit_progress=None):
        """Snap candidate seams to covered word timestamps when safe.

        Word timestamps are a local precision aid, not a second selector. The
        method only considers words overlapping the current interval, requires
        enough lexical coverage, limits each seam's movement, and preserves the
        configured duration bounds. A candidate that cannot be refined remains
        unchanged but receives a reason for human review.
        """
        if not clips:
            return clips

        words = []
        seen = set()
        for segment in segments or []:
            if not isinstance(segment, dict):
                continue
            for item in segment.get("words", []) or []:
                if not isinstance(item, dict):
                    continue
                try:
                    start = float(item.get("start"))
                    end = float(item.get("end"))
                except (TypeError, ValueError):
                    continue
                token = str(item.get("word") or "").strip()
                if end <= start or not token:
                    continue
                key = (round(start, 3), round(end, 3), token)
                if key in seen:
                    continue
                seen.add(key)
                words.append({"start": start, "end": end, "word": token})
        words.sort(key=lambda item: (item["start"], item["end"]))

        available = bool(words)
        refined_count = 0
        review_count = 0
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            start = float(clip.get("start", 0) or 0)
            end = float(clip.get("end", start) or start)
            text_tokens = re.findall(r"[A-Za-zÀ-ÿ0-9À-ÿ-]+", str(clip.get("text") or ""))
            inside = [
                item for item in words
                if item["end"] > start - 0.25 and item["start"] < end + 0.25
            ]
            coverage = len(inside) / max(1, len(text_tokens))
            evidence = {
                "available": available,
                "applied": False,
                "reason": "sem_timestamps_por_palavra" if not available else "cobertura_insuficiente",
                "coverage": round(min(1.0, coverage), 3),
                "word_count": len(inside),
                "original_start": round(start, 3),
                "original_end": round(end, 3),
            }
            if (
                not inside
                or len(inside) < self.MIN_WORDS_FOR_BOUNDARY_REFINEMENT
                or coverage < self.MIN_WORD_BOUNDARY_COVERAGE
            ):
                if available:
                    review_count += 1
                clip["word_boundary_refinement"] = evidence
                continue

            proposed_start = inside[0]["start"]
            proposed_end = inside[-1]["end"]
            evidence.update({
                "proposed_start": round(proposed_start, 3),
                "proposed_end": round(proposed_end, 3),
            })
            if (
                abs(proposed_start - start) > self.MAX_WORD_BOUNDARY_SHIFT_S
                or abs(proposed_end - end) > self.MAX_WORD_BOUNDARY_SHIFT_S
            ):
                evidence["reason"] = "deslocamento_acima_do_limite"
                review_count += 1
                clip["word_boundary_refinement"] = evidence
                continue

            proposed_duration = proposed_end - proposed_start
            if proposed_duration < self.min_duration or proposed_duration > self.max_duration:
                evidence["reason"] = "duracao_fora_dos_limites"
                review_count += 1
                clip["word_boundary_refinement"] = evidence
                continue

            changed = abs(proposed_start - start) >= 0.05 or abs(proposed_end - end) >= 0.05
            clip["start"] = round(proposed_start, 3)
            clip["end"] = round(proposed_end, 3)
            clip["duration"] = round(proposed_duration, 3)
            evidence["applied"] = changed
            evidence["reason"] = "refinado_por_palavra" if changed else "ja_alinhado"
            clip["word_boundary_refinement"] = evidence
            if changed:
                refined_count += 1

        self._candidate_diagnostics["word_boundary_segments_available"] = available
        self._candidate_diagnostics["word_boundary_refined_count"] = refined_count
        self._candidate_diagnostics["word_boundary_review_count"] = review_count
        if refined_count and emit_progress:
            emit_progress(
                f"[Bordas] {refined_count} corte(s) tiveram início/fim refinados por timestamps de palavra.",
                "info",
            )
        return clips

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
        # Simétrico ao recuo de abertura: quem paga o alcance é o limite duro, não
        # o teto preferencial. Parar antes da resposta terminar para caber num
        # teto *suave* é o "termina antes da conclusão" — a queixa mais antiga do
        # editor, junto com a da abertura. O NORTE autoriza passar do teto
        # exatamente quando encurtar destrói a conclusão, e é este o caso.
        reachable = [
            seam for seam in seams
            if start + self.min_duration <= seam <= start + self.max_duration
        ]
        if not reachable:
            return end
        return min(reachable, key=lambda seam: abs(seam - end))

    @staticmethod
    def _text_between(sentences, start, end):
        """The transcript actually contained in a window, after it was moved.

        A tolerância de 0,25 s existe para arredondamento, e uma frase que
        *termina* dentro dela nunca chegou ao corte: a legenda do tactiq quebra
        a linha na marca de troca de locutor, e a última palavra do locutor
        anterior fica com duração de centésimos logo antes da borda. Ela não
        está no áudio do corte e não pode estar na legenda dele — foi assim que
        o corte que abre na pergunta de 22:00 começava escrito com um "E"
        pendurado que ninguém fala.
        """
        parts = [
            str(item.get("text") or "").strip()
            for item in sorted(sentences or [], key=lambda entry: float(entry.get("start", 0) or 0))
            if float(item.get("start", 0) or 0) >= start - 0.25
            and float(item.get("end", 0) or 0) <= end + 0.25
            and float(item.get("end", 0) or 0) > start + 0.05
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
        # The normal job passes a path, not the parsed snapshot. Read it here as
        # well as in the guided-seed path; otherwise local candidates silently
        # lose Chub block evidence while only guided proposals see it.
        if snapshot is None and isinstance(settings, dict) and settings.get("campaign_hub_snapshot_path"):
            try:
                from .campaign_hub import load_snapshot
                snapshot = load_snapshot(settings.get("campaign_hub_snapshot_path"))
            except (ImportError, OSError, ValueError):
                snapshot = None
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
            trust_tier = str(_block_field(best, "trust_tier", "trustTier") or "").strip().lower()
            coverage_of_candidate = round(best_overlap / (end - start), 3)
            # A rich Acervo block can provide identity evidence, but only when
            # the source is trusted, the block explicitly says Renan is speaking,
            # and the local candidate is substantially inside that same interval.
            # This is not diarization and it never approves a render by itself.
            aligned_renan_evidence = bool(
                renan_speaking is True
                and trust_tier in {"owner", "allied"}
                and coverage_of_candidate >= 0.75
            )
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
                "trust_tier": trust_tier,
                "coverage_of_candidate": coverage_of_candidate,
                "identity_evidence": "campaign_hub_aligned_owner_or_allied" if aligned_renan_evidence else "not_sufficient",
                "evidence_only": True,
            }
            if aligned_renan_evidence and self._speaker_identity_required:
                clip["speaker_identity_available"] = True
                clip["speaker_identity_basis"] = "campaign_hub_aligned_owner_or_allied"
                clip["speaker_identity_evidence_only"] = True
                refreshed = self._editorial_flags(
                    clip.get("text", ""),
                    {
                        "overlap_suspected": clip.get("overlap_suspected"),
                        "timing_ambiguous": clip.get("timing_ambiguous"),
                        "speaker_turn_valid": clip.get("speaker_turn_valid", True),
                        "speaker_identity_required": True,
                        "speaker_identity_available": True,
                        "timing_confidence": clip.get("timing_confidence"),
                    },
                )
                for key in ("context_complete", "qa_bridge", "speaker_identity_review_required"):
                    clip[key] = refreshed[key]
                clip["review_reasons"] = [
                    reason for reason in (clip.get("review_reasons") or [])
                    if "identidade do locutor" not in reason and "locutor não confirmado como Renan" not in reason
                ]
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

    @classmethod
    def _find_seed_text_anchor(cls, sentences, seed):
        """Find a conservative local sentence window for a distant Chub seed.

        A timestamp is authoritative only when it overlaps the local transcript or
        falls inside a short silence. When the source is a downloaded block or a
        re-timed copy, the highlight text can still identify the same moment. This
        method deliberately returns an auditable *review* anchor, never a hard
        approval or speaker assertion.
        """
        seed_text = " ".join(str(seed.get("seed_text") or "").split())
        if len(seed_text) < 18 or not sentences:
            return None

        stop_words = {
            "a", "as", "ao", "aos", "com", "da", "das", "de", "do", "dos", "e",
            "em", "esse", "essa", "isso", "na", "nas", "no", "nos", "o", "os",
            "por", "que", "se", "sem", "um", "uma", "uns", "umas", "para",
        }

        def normalize(value):
            decomposed = unicodedata.normalize("NFKD", str(value or "").lower())
            plain = "".join(char for char in decomposed if not unicodedata.combining(char))
            return re.sub(r"[^a-z0-9à-ÿ-]+", " ", plain).strip()

        def words(value):
            return {
                word for word in re.findall(r"[a-z0-9à-ÿ-]{3,}", normalize(value))
                if word not in stop_words
            }

        seed_words = words(seed_text)
        if len(seed_words) < 3:
            return None
        normalized_seed = normalize(seed_text)
        best = None
        max_width = min(cls.MAX_SEED_TEXT_ANCHOR_SENTENCES, len(sentences))
        for start_index in range(len(sentences)):
            for width in range(1, max_width + 1):
                end_index = start_index + width - 1
                if end_index >= len(sentences):
                    break
                text = " ".join(str(item.get("text") or "").strip() for item in sentences[start_index:end_index + 1]).strip()
                local_words = words(text)
                coverage = len(seed_words & local_words) / max(1, len(seed_words))
                if coverage < cls.MIN_SEED_TEXT_ANCHOR_COVERAGE:
                    continue
                sequence = SequenceMatcher(None, normalized_seed, normalize(text)).ratio()
                score = 0.70 * coverage + 0.30 * sequence
                if score < cls.MIN_SEED_TEXT_ANCHOR_SCORE:
                    continue
                candidate = {
                    "start_index": start_index,
                    "end_index": end_index,
                    "coverage": round(coverage, 3),
                    "sequence": round(sequence, 3),
                    "score": round(score, 3),
                    "matched_words": sorted(seed_words & local_words)[:20],
                }
                tie_break = (score, coverage, -abs(len(local_words) - len(seed_words)), -start_index)
                if best is None or tie_break > best[0]:
                    best = (tie_break, candidate)
        return best[1] if best else None

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
        alignment_method = "temporal_overlap"
        alignment_evidence = None
        if not overlapping:
            text_anchor = self._find_seed_text_anchor(sentences, seed)
            if text_anchor:
                overlapping = [text_anchor["start_index"], text_anchor["end_index"]]
                alignment_method = "text_anchor"
                alignment_evidence = text_anchor
            else:
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
                alignment_method = "nearest_sentence"
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
                "speaker_identity_required": bool(self._speaker_identity_required),
                "speaker_identity_available": all(bool(item.get("speakers") or item.get("speaker")) for item in window),
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
            "alignment_gate": "review_required" if alignment_method == "text_anchor" else "pass",
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
            "alinhamento textual conservador; revisão obrigatória" if alignment_method == "text_anchor" else "alinhamento temporal/local",
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
            "alignment_method": alignment_method,
            "alignment_evidence": alignment_evidence,
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
                "renan_speaking": seed.get("renan_speaking"),
                "speaker_gate": seed.get("speaker_gate"),
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
                "alignment_method": alignment_method,
                "alignment_evidence": alignment_evidence,
                "review_required": review_required,
                "provenance": seed.get("provenance") or {},
            },
            "technical_gate_status": "review" if review_required else "pass",
            "technical_gate_reasons": list(dict.fromkeys(
                gate_warnings
                + (["alinhamento textual exige conferência do intervalo"] if alignment_method == "text_anchor" else [])
            )),
        }

    def _prepare_context_matching(self, user_context):
        """Pre-process user context for efficient matching."""
        text_lower = user_context.lower()

        all_words = [w.strip('.,;:!?"()') for w in text_lower.split()]
        context_words = [w for w in all_words if len(w) > 2]

        stop_words_pt = {
            "quero", "quando", "como", "onde", "sobre", "para", "este", "esta",
            "esse", "essa", "principalmente", "extrair", "momentos", "esteja", "falando", "clips", "cortes", "video", "fazer", "pedir",
            "quais", "melhor", "mais", "menos", "muito", "pouco", "todos",
            "todas", "cada", "outro", "outra", "outros", "outras", "aqui",
            "ali", "isso", "isto", "aquilo", "dele", "dela", "deles", "delas",
            "nele", "nela", "neles", "nelas", "meu", "minha", "seu", "sua",
            "nosso", "nossa", "vosso", "vossa", "com", "sem", "por", "entre",
            "contra", "desde", "ate", "apos", "antes", "depois", "durante",
            "pode", "deve", "quer", "tem", "vai", "vem", "estao",
            "foram", "seria", "fosse", "sendo", "sido", "tendo",
            "faz", "fez", "faria", "somente", "apenas", "tambem",
            "ainda", "agora", "logo", "sempre", "nunca", "talvez", "sim",
            "nao", "bem", "mal", "assim", "entao", "pois", "porque", "sobresaia", "estaja", "respondendo", "perguntas", "mitando",
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
        speaker_identity_required = bool(metadata.get("speaker_identity_required"))
        speaker_identity_available = metadata.get("speaker_identity_available")
        speaker_identity_review_required = bool(
            speaker_identity_required and speaker_identity_available is not True
        )
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
            "speaker_identity_required": speaker_identity_required,
            "speaker_identity_available": speaker_identity_available,
            "speaker_identity_review_required": speaker_identity_review_required,
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
        reusable_question_blocks = 0

        def explicit_speaker(sentence):
            """Return a speaker label only when the transcript actually has one."""
            if not isinstance(sentence, dict):
                return ""
            direct = str(sentence.get("speaker") or sentence.get("speaker_label") or "").strip().lower()
            if direct:
                return direct
            speakers = sentence.get("speakers")
            if isinstance(speakers, (list, tuple, set)) and len(speakers) == 1:
                return str(next(iter(speakers)) or "").strip().lower()
            return ""

        def is_rhetorical_question(text):
            """Recognize short rhetorical tails without suppressing real Q&A."""
            normalized = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii").lower()
            normalized = re.sub(r"[^a-z0-9? ]+", " ", normalized)
            normalized = " ".join(normalized.replace("?", " ? ").split()).strip()
            return bool(
                re.match(r"^(e )?(quem nao|sabe quem nao)\b", normalized)
                or re.match(r"^(por que|porque) \?(?:\s|$)", normalized)
                or re.match(r"^(e )?e verdade( isso)? \?(?:\s|$)", normalized)
                or re.match(r"^(hein|ne|nao e|certo|entendeu) \?(?:\s|$)", normalized)
                or re.match(r"^direita ou esquerda \?(?:\s|$)", normalized)
            )

        unique_sentences = {}
        for block, _score in scored_blocks:
            for sentence in (block.get("sentences") or []):
                key = (
                    round(float(sentence.get("start", 0) or 0), 3),
                    round(float(sentence.get("end", 0) or 0), 3),
                    str(sentence.get("text") or "").strip(),
                )
                unique_sentences[key] = sentence
        all_sentences = list(unique_sentences.values())
        source_span = max((float(item.get("end", 0) or 0) for item in all_sentences), default=0.0)
        detected_turns = detect_interviewer_turns(all_sentences)
        allow_interview_question_recall = (
            (editorial_context is None and len(scored_blocks) == 1)
            or looks_like_an_interview(detected_turns, source_span)
        )
        def is_boundary_sentence(sentence, previous_sentence=None):
            text = str(sentence.get("text") or "")
            question = "?" in text or is_a_whole_question(text)
            speaker = explicit_speaker(sentence)
            previous_speaker = explicit_speaker(previous_sentence)
            same_known_speaker = bool(speaker and previous_speaker and speaker == previous_speaker)
            if same_known_speaker:
                return False
            if not question or is_rhetorical_question(text):
                return False
            # Interviews need recall even when Whisper dropped the vocative;
            # outside a detected Q&A, thematic block segmentation is safer than
            # treating every interrogative phrase in a monologue as a seam.
            return bool(allow_interview_question_recall)

        def split_question_boundaries(scored):
            """Expose interviewer questions hidden inside a long scored block.

            The Furia 1 block segmenter is intentionally conservative and may put
            an answer, the next question, and the beginning of its answer in one
            scored block. Reserving that whole block for the first winner made the
            next question impossible to discover. Split only at a clear question
            sentence; all other scoring metadata is retained, and the normal
            overlap pass remains the final authority on redundancy.
            """
            expanded = []
            for block, score in scored:
                sentences = sorted(block.get("sentences") or [], key=lambda item: float(item.get("start", 0) or 0))
                boundaries = [index for index, sentence in enumerate(sentences[1:], start=1) if is_boundary_sentence(sentence, sentences[index - 1])]
                if not boundaries:
                    expanded.append((block, score))
                    continue
                starts = [0] + boundaries
                for position, start_index in enumerate(starts):
                    end_index = (starts[position + 1] - 1) if position + 1 < len(starts) else len(sentences) - 1
                    subset = sentences[start_index:end_index + 1]
                    if not subset:
                        continue
                    piece = dict(block)
                    piece["sentences"] = subset
                    piece["start"] = float(subset[0].get("start", block.get("start", 0)) or 0)
                    piece["end"] = float(subset[-1].get("end", block.get("end", 0)) or 0)
                    piece["duration"] = max(0.0, piece["end"] - piece["start"])
                    piece["text"] = " ".join(str(item.get("text") or "").strip() for item in subset).strip()
                    piece["question_boundary_piece"] = start_index in boundaries
                    expanded.append((piece, score))
            return expanded

        def contains_question_boundary(block):
            """A question at a block edge is reusable evidence, not consumed inventory.

            Blocks are a discovery unit, not a global reservation. If a winning
            window ends on an interviewer question, that question must remain
            available to seed the next answer. The later overlap/similarity pass
            still decides whether the resulting proposal is genuinely redundant.
            A question mark is intentionally enough here: noisy captions may omit
            speaker labels, and losing a valid question is worse than carrying one
            extra review candidate.
            """
            sentences = (block or {}).get("sentences") or []
            if len(sentences) > 1:
                return any(is_boundary_sentence(sentence, sentences[index - 1]) for index, sentence in enumerate(sentences[1:], start=1))
            text = str((block or {}).get("text") or "")
            if not allow_interview_question_recall:
                return False
            return is_a_whole_question(text) and not is_rhetorical_question(text)

        scored_blocks = split_question_boundaries(scored_blocks)
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
                if not needs_previous or gap > 2.5 or joined_duration > self.preferred_max_duration:
                    break
                clip_blocks.insert(0, previous_block)
                clip_duration = joined_duration
                start_idx -= 1

            clip_text_preview = " ".join(b["text"] for b in clip_blocks)
            preview_flags = self._editorial_flags(
                clip_text_preview,
                {
                    "speaker_turn_valid": all(b.get("speaker_turn_valid", True) is not False for b in clip_blocks),
                    "speaker_identity_required": bool(self._speaker_identity_required),
                    "speaker_identity_available": all(bool(b.get("speaker_identity_available")) for b in clip_blocks),
                },
            )
            start_is_complete = (
                clip_duration >= self.min_duration
                and preview_flags.get("context_complete")
                and preview_flags.get("payoff_complete")
            )
            desfecho_encontrado = bool(start_is_complete)
            if not start_is_complete:
                for next_idx in range(start_idx + 1, len(scored_blocks)):
                    if next_idx in used_indices:
                        break
                    next_block = scored_blocks[next_idx][0]
                    new_duration = next_block["end"] - clip_blocks[0]["start"]

                    # O teto aqui é o preferido, não o técnico. Com o teto
                    # técnico (600 s) a procura por um desfecho completo
                    # atravessava blocos inteiros: numa sabatina real um bloco de
                    # 176 s virou candidato de 471 s, e outro de 173 s virou 293 s.
                    # Um trecho de cinco minutos não é corte — é pedaço do
                    # programa. Se o desfecho não aparece em 180 s, ele não
                    # pertence a este corte.
                    if new_duration > self.preferred_max_duration:
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
                            "speaker_identity_required": bool(self._speaker_identity_required),
                            "speaker_identity_available": all(bool(b.get("speaker_identity_available")) for b in clip_blocks),
                        },
                    )
                    if (
                        clip_duration >= self.min_duration
                        and natural_flags.get("context_complete")
                        and natural_flags.get("payoff_complete")
                    ):
                        clip_end_idx = next_idx
                        desfecho_encontrado = True
                        break

            if clip_duration < self.min_duration:
                continue

            for idx in range(start_idx, clip_end_idx + 1):
                block = scored_blocks[idx][0]
                if contains_question_boundary(block):
                    reusable_question_blocks += 1
                    continue
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
                    "speaker_identity_required": bool(self._speaker_identity_required),
                    "speaker_identity_available": all(bool(block.get("speaker_identity_available")) for block in clip_blocks),
                    "timing_confidence": min(
                        [float(block.get("timing_confidence")) for block in clip_blocks if block.get("timing_confidence") is not None]
                        or [1.0]
                    ),
                },
            )

            # Teto: quando o trecho estoura o preferido, quem decide onde ele
            # termina é o material, não o cronômetro. Cortar em
            # clip_start + teto reintroduzia o defeito dos candidatos de 180.0 s
            # exatos, que abriam e fechavam no meio do argumento. _split_to_clip_length
            # fecha no turno do entrevistador ou no maior silêncio.
            estourou = clip_end - clip_start > self.preferred_max_duration
            # Quando a expansão desiste de achar um desfecho, o fim do corte é
            # onde o laço parou — e isso é arbitrário tanto se parou no teto de
            # 180 s quanto se parou porque o próximo bloco não cabia. Foi o que
            # produziu candidatos fechando no meio do argumento. Havendo mais de
            # um bloco, quem escolhe a saída é o material: o turno do
            # entrevistador primeiro, senão o maior silêncio.
            desistiu_no_meio = not desfecho_encontrado and len(clip_blocks) > 1
            if estourou or desistiu_no_meio:
                sentencas = [s for block in clip_blocks for s in (block.get("sentences") or [])]
                # _best_cut_index, e não _split_to_clip_length: o divisor não faz
                # nada quando o trecho já cabe no teto, e o caso comum aqui é
                # justamente esse — o corte fechou em 164 s numa fronteira de
                # bloco tendo um silêncio aos 140 s.
                corte = self._best_cut_index(sentencas, clip_start) if len(sentencas) > 1 else 0
                if 0 < corte <= len(sentencas):
                    clip_end = float(sentencas[corte - 1]["end"])
                    clip_blocks = [b for b in clip_blocks if float(b["start"]) < clip_end] or clip_blocks[:1]
                    clip_text = " ".join(b["text"] for b in clip_blocks)
                elif estourou:
                    clip_end = clip_start + self.preferred_max_duration
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
                "review_required": bool(
                    clip_flags.get("speaker_identity_review_required")
                    or not clip_flags.get("context_complete")
                    or not clip_flags.get("payoff_complete")
                    or clip_flags.get("overlap_suspected")
                    or clip_flags.get("timing_ambiguous")
                ),
                "duration_preference": self._duration_label(clip_duration, {"flow": flow_grade}),
            })

        diagnostics = getattr(self, "_candidate_diagnostics", None)
        if reusable_question_blocks and isinstance(diagnostics, dict):
            diagnostics["reusable_question_blocks"] = reusable_question_blocks
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
            self._record_hard_negative(
                clip,
                "already_exported_fingerprint",
                details={"review_status": str(repeated.get("review_status") or "")[:24]},
            )
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
        def potential(item):
            return float(item.get("editorial_potential_score", item.get("viral_score", 0)) or 0)

        for clip in ordered:
            duplicate = False
            duplicate_reason = ""
            existing = None

            # Duas janelas que começam na mesma fala não são duas aberturas
            # editoriais. A extensão longa pode conter material novo, mas quando
            # passa muito do teto preferencial ela é um contêiner da mesma ideia,
            # não um segundo corte. O teste é simétrico para que a ordem do score
            # não deixe o aninhamento escapar.
            clip_start = float(clip.get("start", 0) or 0)
            clip_end = float(clip.get("end", 0) or 0)
            clip_duration = max(0.0, clip_end - clip_start)
            for previous in list(selected):
                previous_start = float(previous.get("start", 0) or 0)
                previous_end = float(previous.get("end", 0) or 0)
                previous_duration = max(0.0, previous_end - previous_start)
                same_start = abs(clip_start - previous_start) <= 0.75
                same_end = abs(clip_end - previous_end) <= 0.75
                clip_stabilized = bool(clip.get("opening_source") == "resposta estabilizada após intervenção")
                previous_stabilized = bool(previous.get("opening_source") == "resposta estabilizada após intervenção")
                if same_end and clip_stabilized != previous_stabilized:
                    if clip_stabilized:
                        self._record_candidate_relationship(
                            previous, clip, "alternative_of", "stabilized_opening_preferred"
                        )
                        selected.remove(previous)
                    else:
                        duplicate = True
                        duplicate_reason = "same_closing"
                        existing = previous
                    break
                if not (same_start or same_end):
                    continue
                nested = (
                    clip_end <= previous_end + 0.5
                    or previous_end <= clip_end + 0.5
                )
                if not nested:
                    continue
                if clip_end > previous_end + 0.5:
                    if same_start and (clip_duration > self.preferred_max_duration * 1.5 or potential(clip) <= potential(previous)):
                        duplicate = True
                        duplicate_reason = "same_opening"
                        existing = previous
                        break
                elif previous_end > clip_end + 0.5:
                    if same_start and (previous_duration > self.preferred_max_duration * 1.5 or potential(clip) >= potential(previous)):
                        selected.remove(previous)
                    elif same_end and potential(clip) < potential(previous):
                        duplicate = True
                        duplicate_reason = "same_closing"
                        existing = previous
                        break
                else:
                    # Same opening or same closing with equal endpoint: keep
                    # the shorter/higher-potential editorial alternative.
                    if potential(clip) >= potential(previous) or previous_duration > self.preferred_max_duration * 1.5:
                        selected.remove(previous)
                    else:
                        duplicate = True
                        duplicate_reason = "same_closing" if same_end else "same_opening"
                        existing = previous
                        break
            if duplicate:
                if str(clip.get("candidate_origin") or "") == "local_fallback":
                    self._candidate_diagnostics["fallback_discarded_count"] = int(
                        self._candidate_diagnostics.get("fallback_discarded_count", 0) or 0
                    ) + 1
                    self._candidate_diagnostics["fallback_discarded_overlap"] = int(
                        self._candidate_diagnostics.get("fallback_discarded_overlap", 0) or 0
                    ) + 1
                relation = "alternative_of" if duplicate_reason in {"same_opening", "same_closing"} else None
                if relation and existing is not None:
                    self._record_candidate_relationship(clip, existing, relation, duplicate_reason)
                self._record_hard_negative(
                    clip,
                    f"duplicate_{duplicate_reason or 'same_opening'}",
                    winner=existing,
                    details={"relation": relation} if relation else None,
                )
                self._registrar_descarte_por_sobreposicao(
                    clip, existing, duplicate_reason, 1.0, inedito_s=0.0
                )
                continue

            # ── a pergunta certa ────────────────────────────────────────────
            # A regra antiga era "quanto este candidato divide com aquele?", e
            # ela não distingue duas situações opostas. Medido na corrida real
            # do editor (PENÉLOPE, 21 descartes por sobreposição):
            #
            #   12 estavam INTEIROS dentro de um corte entregue. Não se perdeu
            #      nada: o corte longo contém aquela fala, e ele já disse que em
            #      resposta longa prefere o contexto inteiro.
            #    9 só encostavam na borda. Um deles cobria 19:54–21:45 — quase
            #      dois minutos que nenhum corte entregou.
            #
            # As duas morriam pelo mesmo motivo. A pergunta que separa não é
            # quanto o candidato REPETE, é quanto ele ACRESCENTA.
            inedito = self._material_inedito(clip, selected)
            duracao = max(0.0, float(clip.get("end", 0) or 0) - float(clip.get("start", 0) or 0))
            fracao = (inedito / duracao) if duracao > 0 else 0.0
            # Só entra na conta quem de fato divide material com alguém. Sem
            # esta guarda, um candidato curto e sozinho — 25s, sem encostar em
            # nada — morreria pelo piso de material inédito, que é uma régua de
            # REPETIÇÃO e não de duração. Seria reduzir a quantidade de cortes
            # por uma porta lateral, exatamente o que não pode acontecer.
            partilha_material = inedito < duracao - 0.5
            if selected and partilha_material and fracao < self.FRACAO_INEDITA_MINIMA:
                duplicate = True
                duplicate_reason = "overlap"
                existing = self._maior_sobreposicao(clip, selected)

            if not duplicate:
                for candidato_vencedor in selected:
                    text_similarity = self._text_similarity(
                        clip.get("text", ""), candidato_vencedor.get("text", "")
                    )
                    # Repeated wording in adjacent candidate windows is usually a
                    # rolling-caption duplicate. Require high lexical and sequence
                    # similarity so short common political phrases survive.
                    if text_similarity >= 0.90:
                        duplicate = True
                        duplicate_reason = "similarity"
                        existing = candidato_vencedor
                        break

            overlap = fracao
            text_similarity = (
                self._text_similarity(clip.get("text", ""), existing.get("text", ""))
                if existing is not None else 0.0
            )
            if duplicate:
                self._record_hard_negative(
                    clip,
                    "duplicate_overlap" if duplicate_reason == "overlap" else "duplicate_similarity",
                    winner=existing,
                    details={"overlap_or_similarity": round(overlap if duplicate_reason == "overlap" else text_similarity, 3)},
                )
                if str(clip.get("candidate_origin") or "") == "local_fallback":
                    self._candidate_diagnostics["fallback_discarded_count"] = int(
                        self._candidate_diagnostics.get("fallback_discarded_count", 0) or 0
                    ) + 1
                    field = "fallback_discarded_overlap" if duplicate_reason == "overlap" else "fallback_discarded_similarity"
                    self._candidate_diagnostics[field] = int(
                        self._candidate_diagnostics.get(field, 0) or 0
                    ) + 1
                self._registrar_descarte_por_sobreposicao(
                    clip,
                    existing,
                    duplicate_reason,
                    overlap if duplicate_reason == "overlap" else text_similarity,
                    inedito_s=inedito if duplicate_reason == "overlap" else None,
                )
                continue
            selected.append(clip)

        return selected

    def _registrar_descarte_por_sobreposicao(self, perdedor, vencedor, motivo, medida, inedito_s=None):
        """Anota quem a peneira derrubou, e por causa de quem.

        Medido no diagnóstico real do editor: 24 candidatos primários viraram 14
        finais, com 12 mortos aqui. O número sozinho não responde nada. Um
        candidato de 40 s inteiramente dentro de um corte de 143 s tem
        sobreposição 1,00 e morre; um candidato de 45 s que só herdou 6 s de
        pergunta da repórter tem 0,13 e sobrevive. São situações opostas e o
        contador dava o mesmo "1" para as duas.

        Só metadado — nenhum candidato deixa de ser considerado por causa disto.
        """
        try:
            inicio = float(perdedor.get("start", 0) or 0)
            fim = float(perdedor.get("end", 0) or 0)
            venc_inicio = float(vencedor.get("start", 0) or 0)
            venc_fim = float(vencedor.get("end", 0) or 0)
        except (TypeError, ValueError):
            return
        ledger = self._candidate_diagnostics.setdefault("descartados_por_sobreposicao", [])
        # Um vídeo de duas horas pode gerar centenas de descartes; o arquivo que
        # o editor envia precisa continuar abrível.
        if len(ledger) >= 60:
            return
        texto = " ".join(str(perdedor.get("text", "") or "").split())
        ledger.append({
            "motivo": motivo,
            # Em "overlap" a medida é a FRAÇÃO INÉDITA — quanto deste candidato
            # nenhum corte escolhido cobria. Em "similarity" é a semelhança de
            # texto. Nomes separados porque significam coisas opostas: fração
            # inédita ALTA é bom, semelhança ALTA é ruim.
            "medida": round(float(medida or 0), 3),
            "fracao_inedita": round(float(medida or 0), 3) if motivo == "overlap" else None,
            "inedito_s": round(float(inedito_s), 1) if inedito_s is not None else None,
            "inicio": round(inicio, 1),
            "fim": round(fim, 1),
            "duracao": round(max(0.0, fim - inicio), 1),
            "vencedor_inicio": round(venc_inicio, 1),
            "vencedor_fim": round(venc_fim, 1),
            "vencedor_duracao": round(max(0.0, venc_fim - venc_inicio), 1),
            # Estava inteiro dentro do vencedor? É a diferença entre "fragmento
            # redundante" e "corte perdido", e é a única pergunta que importa.
            "dentro_do_vencedor": bool(inicio >= venc_inicio - 0.5 and fim <= venc_fim + 0.5),
            "trecho": texto[:180],
        })

    # ─────────────────────────────────────────────────────────────────────────
    # QUANTO UM CANDIDATO PRECISA ACRESCENTAR PARA VALER UM CORTE
    #
    # Medido na base do CHUB, não achado: 4.109 cortes que a campanha realmente
    # publicou, nas três contas orgânicas, com duração entre 1s e 15min.
    #
    #     percentil 5   facebook 32s · instagram 36s · tiktok 46s
    #     percentil 10  facebook 44s · instagram 48s · tiktok 60s
    #     mediana       facebook 102s · instagram 91s · tiktok 123s
    #
    # Ou seja: 95% de tudo que eles publicam tem 32 segundos ou mais. Abaixo
    # disso é a exceção da exceção. Um candidato cujo material inédito não chega
    # lá não é um corte que se sustenta — é um pedaço de outro que já saiu.
    #
    # ── e por que o piso ABSOLUTO foi embora ────────────────────────────────
    #
    # A primeira versão disto tinha duas condições: material inédito abaixo de
    # 30s OU fração inédita abaixo de 40%. O teste do vazamento da repórter
    # pegou o erro na hora:
    #
    #     dois candidatos de 30s, com 6s de pergunta vazada na borda
    #     inédito = 24s  →  abaixo do piso  →  MORRIA
    #
    # Um candidato que repete 6 dos seus 30 segundos não é duplicata de coisa
    # nenhuma; ele só encosta. Eu tinha acabado de garantir ao editor que a
    # pergunta na borda não custa cortes, e o piso absoluto reintroduzia
    # exatamente aquele defeito por outra porta.
    #
    # A pergunta certa é PROPORÇÃO, não tamanho: quanto DESTE candidato já foi
    # entregue. 24 de 30 é 80% de novidade e sobrevive; 51 de 165 é 31% e não.
    # A medida de duração publicável acima continua valendo como referência do
    # que é um corte — só não serve como régua de repetição.
    FRACAO_INEDITA_MINIMA = 0.40

    @staticmethod
    def _material_inedito(clip, selecionados):
        """Segundos deste candidato que nenhum corte já escolhido cobre.

        A conta é sobre a UNIÃO dos escolhidos, não sobre cada um de cada vez.
        Comparar par a par escondia o caso mais comum: um candidato que dois
        vizinhos cobrem juntos, sem que nenhum dos dois o cubra sozinho.
        """
        inicio = float(clip.get("start", 0) or 0)
        fim = float(clip.get("end", 0) or 0)
        if fim <= inicio:
            return 0.0
        coberto = 0.0
        cursor = inicio
        faixas = sorted(
            (
                (float(outro.get("start", 0) or 0), float(outro.get("end", 0) or 0))
                for outro in selecionados
            ),
            key=lambda par: par[0],
        )
        for de, ate in faixas:
            de = max(de, inicio)
            ate = min(ate, fim)
            if ate <= de:
                continue
            de = max(de, cursor)
            if ate > de:
                coberto += ate - de
                cursor = ate
        return max(0.0, (fim - inicio) - coberto)

    @staticmethod
    def _maior_sobreposicao(clip, selecionados):
        """Qual escolhido é o principal responsável — para o registro dizer quem."""
        inicio = float(clip.get("start", 0) or 0)
        fim = float(clip.get("end", 0) or 0)
        melhor, maior = None, -1.0
        for outro in selecionados:
            partilha = min(fim, float(outro.get("end", 0) or 0)) - max(
                inicio, float(outro.get("start", 0) or 0)
            )
            if partilha > maior:
                melhor, maior = outro, partilha
        return melhor if melhor is not None else (selecionados[0] if selecionados else None)

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
