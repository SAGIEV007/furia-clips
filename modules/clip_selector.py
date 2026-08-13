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
from collections import Counter

from .political_profile import PROFILE_NAME, build_political_prompt_fragment

# Portuguese filler words to detect
FILLER_WORDS_PT = {
    "ne", "ne\u0301", "tipo", "ah", "eh", "e\u0301h", "enta\u0303o", "entao",
    "sabe", "basicamente", "na verdade", "ou seja", "entendeu",
    "digamos", "assim", "enfim", "bom", "olha", "veja",
    "quer dizer", "pois e\u0301", "pois e", "ta", "ta\u0301", "cara",
}


class ClipSelector:
    def __init__(self, target_duration=45, max_clips=15, min_duration=20, max_duration=180):
        self.target_duration = target_duration
        self.max_clips = max_clips
        self.min_duration = min_duration
        self.max_duration = max_duration

    def select_clips(self, transcription, energy_profile=None, user_context="",
                     settings=None, emit_progress=None, scene_changes=None,
                     video_layout=None):
        settings = settings or {}
        self._selection_source = None
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
                sentences, energy_profile, user_context, emit_progress
            )

        # Filter clips at scene boundaries if available
        if scene_changes:
            clips = self._adjust_to_scene_boundaries(clips, scene_changes)

        # Apply anti-overlap filter
        clips = self._remove_overlaps(clips)

        # Limit to max_clips
        clips = clips[:self.max_clips]

        if emit_progress:
            source_labels = {"gemini": "Gemini Flash", "llm": "IA (Ollama)", "nlp": "NLP basico"}
            source_label = source_labels.get(self._selection_source, "NLP basico")
            emit_progress(f"Selecionados {len(clips)} clips de partes diferentes do video (via {source_label})")

        return clips

    def get_selection_source(self):
        return self._selection_source or "nlp"

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
        """Group transcription segments into natural sentences based on punctuation and pauses.
        Caps sentence length at 30s to prevent mega-blocks."""
        sentences = []
        current_text = ""
        current_start = None
        current_end = None
        last_end = 0
        MAX_SENTENCE_DURATION = 30  # Force split at 30s to keep blocks manageable

        for seg in segments:
            pause_before = seg["start"] - last_end if last_end > 0 else 0

            if pause_before > 0.8 and current_text:
                sentences.append({
                    "text": current_text.strip(),
                    "start": current_start,
                    "end": current_end,
                    "duration": current_end - current_start,
                })
                current_text = ""
                current_start = None

            if current_start is None:
                current_start = seg["start"]

            current_text += " " + seg["text"]
            current_end = seg["end"]
            last_end = seg["end"]

            # Force split if sentence exceeds max duration
            current_duration = current_end - current_start
            if current_duration >= MAX_SENTENCE_DURATION:
                sentences.append({
                    "text": current_text.strip(),
                    "start": current_start,
                    "end": current_end,
                    "duration": current_duration,
                })
                current_text = ""
                current_start = None
                continue

            text_stripped = current_text.strip()
            if text_stripped and text_stripped[-1] in ".!?" and len(text_stripped.split()) >= 5:
                sentences.append({
                    "text": text_stripped,
                    "start": current_start,
                    "end": current_end,
                    "duration": current_end - current_start,
                })
                current_text = ""
                current_start = None

        if current_text.strip():
            sentences.append({
                "text": current_text.strip(),
                "start": current_start,
                "end": current_end,
                "duration": current_end - current_start,
            })

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

        # Try multiple models with retry for transient errors (503)
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
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
   - Cada clip: 30 a 180 segundos. Prefira 45 a 120 segundos.
   - Clips mais longos sao OTIMOS se o pensamento estiver completo e o conteudo justificar.
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
            editorial_instruction = f"""

PRÉ-ANÁLISE EDITORIAL DETERMINÍSTICA:
{editorial_context.get('description', '')}
Foco padrão: Renan Santos/MBL. Confiança inicial de participante: {editorial_context.get('participant_confidence', 0):.0%}.
Janelas prováveis de entrevista: {windows}.
Candidatos pergunta–resposta detectados: {qa}.
Use esses sinais como orientação, não como prova. Quando houver dúvida sobre locutor ou sobreposição de fala, reduza a confiança ou rejeite.
"""

        num_clips = min(15, max(5, len(blocks) // 4))

        return f"""Analise esta transcricao completa e selecione os {num_clips} MELHORES momentos para clips curtos.
{editorial_instruction}
{context_instruction}

TRANSCRICAO COMPLETA ({len(blocks)} blocos, {self._format_time(blocks[-1]['end'])} de video):

{transcript_text}

Combine blocos consecutivos para formar clips de 30-180 segundos com CONTEXTO COMPLETO.
Lembre: cada clip deve ter inicio (contexto/pergunta), meio (desenvolvimento) e fim (conclusao do raciocinio).
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
5. DURACAO: 30 a 180 segundos por clip. Clips longos sao OK se o conteudo justificar.
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
            editorial_instruction = f"\nPRÉ-ANÁLISE: {editorial_context.get('description', '')}\n"

        num_clips = min(8, max(3, len(blocks) // 3))
        return f"""Selecione os {num_clips} MELHORES momentos para clips curtos.
{editorial_instruction}
{context_instruction}

TRANSCRICAO (blocos {chunk_offset} a {chunk_offset + len(blocks) - 1} de {total_blocks} total):

{transcript_text}

Combine blocos consecutivos para clips de 30-180 segundos com contexto completo.
Retorne APENAS o JSON."""

    def _build_transcript_blocks(self, sentences):
        """Group sentences into blocks of ~40-60 seconds for analysis."""
        blocks = []
        current_block_sentences = []
        current_start = None
        current_duration = 0

        for sent in sentences:
            if current_start is None:
                current_start = sent["start"]

            current_block_sentences.append(sent)
            current_duration = sent["end"] - current_start

            # Create a block every ~40-60 seconds for better context
            if current_duration >= 40 or (sent["text"].strip()[-1:] in ".!?" and current_duration >= 25):
                block_text = " ".join(s["text"] for s in current_block_sentences)
                blocks.append({
                    "index": len(blocks),
                    "start": current_start,
                    "end": sent["end"],
                    "duration": round(current_duration, 1),
                    "text": block_text.strip(),
                    "sentences": current_block_sentences.copy(),
                })
                current_block_sentences = []
                current_start = None
                current_duration = 0

        if current_block_sentences:
            block_text = " ".join(s["text"] for s in current_block_sentences)
            blocks.append({
                "index": len(blocks),
                "start": current_start,
                "end": current_block_sentences[-1]["end"],
                "duration": round(current_block_sentences[-1]["end"] - current_start, 1),
                "text": block_text.strip(),
                "sentences": current_block_sentences.copy(),
            })

        return blocks

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

            block_indices = sel.get("blocks", [])
            if not block_indices:
                continue

            # Handle both 0-indexed and 1-indexed block references
            # Check if any index exceeds our block count (likely 1-indexed)
            max_idx = max(block_indices) if block_indices else 0
            if max_idx >= len(all_blocks) and min(block_indices) >= 1:
                # Likely 1-indexed, convert to 0-indexed
                block_indices = [i - 1 for i in block_indices]

            # Map block indices to actual timestamps
            valid_blocks = [
                all_blocks[i] for i in block_indices
                if 0 <= i < len(all_blocks)
            ]
            if not valid_blocks:
                continue

            clip_start = valid_blocks[0]["start"]
            clip_end = valid_blocks[-1]["end"]
            clip_duration = clip_end - clip_start

            # Validate duration
            if clip_duration < self.min_duration:
                continue
            if clip_duration > self.max_duration:
                clip_end = clip_start + self.max_duration
                clip_duration = self.max_duration

            clip_text = " ".join(b["text"] for b in valid_blocks)

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
            })

        return clips

    # ═══════════════════════════════════════════════════
    # NLP — Keyword-based fallback (always available)
    # ═══════════════════════════════════════════════════

    def _select_with_nlp(self, sentences, energy_profile, user_context, emit_progress):
        """NLP-based fallback when no AI backend is available."""
        if emit_progress:
            emit_progress("[NLP] Construindo clips com analise por palavras-chave...")

        blocks = self._build_transcript_blocks(sentences)
        if not blocks:
            return []

        context_data = self._prepare_context_matching(user_context) if user_context else None

        scored_blocks = []
        for block in blocks:
            score = self._nlp_score_block(block, user_context, energy_profile, context_data)
            scored_blocks.append((block, score))

        clips = self._build_clips_from_scored_blocks(scored_blocks, context_data)

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

    def _nlp_score_block(self, block, user_context, energy_profile, context_data=None):
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

        # Duration penalty (prefer 25-55s)
        duration = block["duration"]
        if 25 <= duration <= 55:
            duration_score = 10
        elif duration < 15:
            duration_score = -10
        else:
            duration_score = 0

        # Sentence completeness
        if block["text"].strip()[-1:] in ".!?":
            completeness_score = 10
        else:
            completeness_score = -15

        total = (score + hook_score + emotional_score + punct_score
                 + context_score + duration_score + completeness_score
                 - filler_penalty)
        return max(0, min(100, total))

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

    def _build_clips_from_scored_blocks(self, scored_blocks, context_data=None):
        """Build clips by combining consecutive blocks to reach target duration.
        Enforces max_duration on ALL clips including single-block clips."""
        clips = []
        used_indices = set()

        sorted_by_score = sorted(enumerate(scored_blocks), key=lambda x: x[1][1], reverse=True)

        for start_idx, (start_block, start_score) in sorted_by_score:
            if start_idx in used_indices:
                continue

            clip_blocks = [start_block]
            clip_duration = start_block["duration"]
            clip_end_idx = start_idx

            for next_idx in range(start_idx + 1, len(scored_blocks)):
                if next_idx in used_indices:
                    break
                next_block = scored_blocks[next_idx][0]
                new_duration = next_block["end"] - clip_blocks[0]["start"]

                if new_duration > self.max_duration:
                    break

                clip_blocks.append(next_block)
                clip_duration = new_duration
                clip_end_idx = next_idx

                if clip_duration >= self.target_duration:
                    break

            if clip_duration < self.min_duration:
                continue

            for idx in range(start_idx, clip_end_idx + 1):
                used_indices.add(idx)

            clip_text = " ".join(b["text"] for b in clip_blocks)
            clip_start = clip_blocks[0]["start"]
            clip_end = clip_blocks[-1]["end"]

            # ENFORCE max_duration — truncate if clip exceeds limit
            if clip_end - clip_start > self.max_duration:
                clip_end = clip_start + self.max_duration
                clip_duration = self.max_duration
            else:
                clip_duration = clip_end - clip_start

            avg_score = sum(scored_blocks[i][1] for i in range(start_idx, clip_end_idx + 1)) / (clip_end_idx - start_idx + 1)

            hook_grade = "A" if start_score > 75 else ("B" if start_score > 50 else "C")
            flow_grade = "A" if clip_text.strip()[-1:] in ".!?" else "B"
            value_grade = "A" if avg_score > 70 else ("B" if avg_score > 50 else "C")
            energy_grade = "B"

            viral_score = int(avg_score)

            title = self._generate_simple_title(clip_text)

            reason = ""
            if context_data and context_data["names"]:
                matched_names = [n for n in context_data["names"] if n in clip_text.lower()]
                if matched_names:
                    reason = f"Contem mencao a: {', '.join(matched_names)}"

            clips.append({
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

    def _remove_overlaps(self, clips):
        """Remove clips that overlap more than 30% with higher-scored clips."""
        if not clips:
            return []

        selected = []
        for clip in clips:
            overlaps = False
            for existing in selected:
                overlap = self._calculate_overlap(clip, existing)
                if overlap > 0.30:
                    overlaps = True
                    break
            if not overlaps:
                selected.append(clip)

        return selected

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
