"""
Clip Selector — Intelligent clip selection using LLM (Ollama) or NLP fallback.

This replaces the old brute-force approach (generate all windows → rank by regex)
with an intelligent approach:
1. Build sentences from transcription segments
2. Send to LLM with user context for intelligent selection
3. Fall back to NLP-based selection if LLM unavailable
"""

import json
import re
import math
import requests
from collections import Counter

# Portuguese filler words to detect
FILLER_WORDS_PT = {
    "ne", "né", "tipo", "ah", "eh", "éh", "então", "entao",
    "sabe", "basicamente", "na verdade", "ou seja", "entendeu",
    "digamos", "assim", "enfim", "bom", "olha", "veja",
    "quer dizer", "pois é", "pois e", "ta", "tá", "cara",
}


class ClipSelector:
    def __init__(self, target_duration=45, max_clips=15, min_duration=20, max_duration=90):
        self.target_duration = target_duration
        self.max_clips = max_clips
        self.min_duration = min_duration
        self.max_duration = max_duration

    def select_clips(self, transcription, energy_profile=None, user_context="",
                     settings=None, emit_progress=None, scene_changes=None,
                     video_layout=None):
        settings = settings or {}
        self._selection_source = None
        sentences = self._build_sentences(transcription["segments"])

        if emit_progress:
            emit_progress(f"Transcricao dividida em {len(sentences)} sentencas")

        # Extract context keywords for display
        if user_context and emit_progress:
            keywords = self._extract_context_keywords(user_context)
            if keywords:
                emit_progress(f"Contexto aplicado: {', '.join(keywords[:8])}...", "info")

        # Try LLM-based selection first
        clips = self._select_with_llm(
            sentences, energy_profile, user_context, settings, emit_progress
        )

        if clips:
            self._selection_source = "llm"
            if emit_progress:
                emit_progress("[IA] Selecao inteligente via Ollama concluida!", "success")
        else:
            self._selection_source = "nlp"
            if emit_progress:
                emit_progress("[NLP] Usando selecao por palavras-chave (menos preciso)...", "warning")
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
            source_label = "IA (Ollama)" if self._selection_source == "llm" else "NLP basico"
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

    def _build_sentences(self, segments):
        """Group transcription segments into natural sentences based on punctuation and pauses."""
        sentences = []
        current_text = ""
        current_start = None
        current_end = None
        last_end = 0

        for seg in segments:
            pause_before = seg["start"] - last_end if last_end > 0 else 0

            # Start new sentence on long pause (>0.8s) or if current is empty
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

            # Split on sentence-ending punctuation
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

        # Don't forget the last chunk
        if current_text.strip():
            sentences.append({
                "text": current_text.strip(),
                "start": current_start,
                "end": current_end,
                "duration": current_end - current_start,
            })

        return sentences

    def _select_with_llm(self, sentences, energy_profile, user_context, settings, emit_progress):
        """Use Ollama to intelligently select the best clips."""
        ollama_url = settings.get("ollama_url", "http://localhost:11434")
        ollama_model = settings.get("ollama_model", "llama3.2:3b")

        # Build a condensed transcript with indices for the LLM
        transcript_blocks = self._build_transcript_blocks(sentences)

        if not transcript_blocks:
            return []

        # Send in chunks if transcript is too long (smaller chunks = faster per request on CPU)
        all_selections = []
        chunk_size = 25  # blocks per chunk (smaller = faster response from llama3.2:3b on CPU)

        for chunk_idx in range(0, len(transcript_blocks), chunk_size):
            chunk = transcript_blocks[chunk_idx:chunk_idx + chunk_size]
            prompt = self._build_llm_prompt(chunk, user_context, chunk_idx, len(transcript_blocks))

            if emit_progress:
                emit_progress(f"Analisando trecho {chunk_idx // chunk_size + 1}/{math.ceil(len(transcript_blocks) / chunk_size)} com IA...")

            try:
                response = requests.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": ollama_model,
                        "prompt": prompt,
                        "system": self._get_system_prompt(),
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 1500},
                    },
                    timeout=600,  # 10 min — llama3.2:3b on CPU is slow with large transcripts
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "")

                selections = self._parse_llm_response(text, sentences, transcript_blocks, chunk_idx)
                all_selections.extend(selections)

            except requests.exceptions.ConnectionError:
                if emit_progress:
                    emit_progress("Ollama nao disponivel.")
                return []
            except Exception as e:
                if emit_progress:
                    emit_progress(f"Erro na IA: {str(e)}")
                return []

        # Sort by score descending
        all_selections.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
        return all_selections

    def _build_transcript_blocks(self, sentences):
        """Group sentences into blocks of ~30-60 seconds for LLM analysis."""
        blocks = []
        current_block_sentences = []
        current_start = None
        current_duration = 0

        for sent in sentences:
            if current_start is None:
                current_start = sent["start"]

            current_block_sentences.append(sent)
            current_duration = sent["end"] - current_start

            # Create a block every ~20-30 seconds of speech
            if current_duration >= 20 or (sent["text"].strip()[-1:] in ".!?" and current_duration >= 10):
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

    def _get_system_prompt(self):
        return """Voce e um editor de video especialista em conteudo viral para YouTube Shorts, TikTok e Reels.
Sua tarefa e analisar a transcricao de um video e selecionar os melhores momentos para cortar como clips virais.

REGRAS FUNDAMENTAIS:
- Cada clip DEVE ter um PENSAMENTO COMPLETO (comeco, meio e fim)
- Cada clip DEVE comecar com uma frase forte que prende atencao (gancho)
- NUNCA cortar no meio de uma frase ou raciocinio
- Selecionar momentos de partes DIFERENTES do video (diversidade)
- Cada clip deve fazer sentido SOZINHO, sem contexto adicional
- Preferir momentos com opiniao forte, emocao, frases de efeito
- Duração ideal: 30-60 segundos por clip

FORMATO DE RESPOSTA - retorne APENAS JSON valido:
[
  {
    "blocks": [3, 4, 5],
    "title": "Titulo curto e cativante para o clip",
    "reason": "Por que este momento e viral",
    "hook": "A",
    "flow": "A",
    "value": "A",
    "energy": "B"
  }
]

Onde hook/flow/value/energy sao notas A (excelente), B (bom) ou C (fraco).
- hook: Os primeiros segundos prendem atencao?
- flow: O clip tem comeco, meio e fim coerentes?
- value: Oferece insight, opiniao forte, emocao ou informacao util?
- energy: O tom de voz e intenso, animado, emocionante?"""

    def _build_llm_prompt(self, blocks, user_context, chunk_offset, total_blocks):
        lines = []
        for b in blocks:
            timestamp = f"[{self._format_time(b['start'])} - {self._format_time(b['end'])}]"
            lines.append(f"BLOCO {b['index']}: {timestamp} ({b['duration']}s)\n{b['text']}\n")

        transcript_text = "\n".join(lines)

        context_instruction = ""
        if user_context:
            context_instruction = f"\n\nCONTEXTO DO USUARIO (priorize clips que se encaixem nisso): {user_context}"

        return f"""Analise esta transcricao e selecione os {min(5, len(blocks) // 3 + 1)} MELHORES momentos para clips virais.
{context_instruction}

TRANSCRICAO (blocos {chunk_offset} a {chunk_offset + len(blocks) - 1} de {total_blocks} total):

{transcript_text}

Selecione combinando blocos consecutivos para formar clips de 30-60 segundos.
Retorne APENAS o JSON com os clips selecionados. Nada mais."""

    def _parse_llm_response(self, response_text, sentences, all_blocks, chunk_offset):
        """Parse LLM JSON response into clip data with timestamps."""
        try:
            json_str = response_text.strip()
            # Extract JSON from potential markdown code blocks
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                parts = json_str.split("```")
                if len(parts) >= 3:
                    json_str = parts[1]

            # Try to find JSON array in the response
            start_idx = json_str.find("[")
            end_idx = json_str.rfind("]") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = json_str[start_idx:end_idx]

            selections = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return []

        clips = []
        for sel in selections:
            if not isinstance(sel, dict):
                continue

            block_indices = sel.get("blocks", [])
            if not block_indices:
                continue

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
            if clip_duration < self.min_duration or clip_duration > self.max_duration:
                # Try to trim if too long
                if clip_duration > self.max_duration:
                    clip_end = clip_start + self.max_duration
                    clip_duration = self.max_duration
                elif clip_duration < self.min_duration:
                    continue

            clip_text = " ".join(b["text"] for b in valid_blocks)

            # Convert letter grades to scores
            grade_to_score = {"A": 95, "B": 70, "C": 40}
            hook_score = grade_to_score.get(sel.get("hook", "B"), 70)
            flow_score = grade_to_score.get(sel.get("flow", "B"), 70)
            value_score = grade_to_score.get(sel.get("value", "B"), 70)
            energy_score = grade_to_score.get(sel.get("energy", "B"), 70)

            # Weighted final score
            viral_score = int(
                hook_score * 0.30 +
                flow_score * 0.25 +
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
                "viral_score": viral_score,
                "has_hook": sel.get("hook", "C") in ("A", "B"),
                "breakdown": {
                    "hook": sel.get("hook", "B"),
                    "flow": sel.get("flow", "B"),
                    "value": sel.get("value", "B"),
                    "energy": sel.get("energy", "B"),
                },
                "source": "llm",
            })

        return clips

    def _select_with_nlp(self, sentences, energy_profile, user_context, emit_progress):
        """NLP-based fallback when Ollama is not available."""
        if emit_progress:
            emit_progress("[NLP] Construindo clips com analise por palavras-chave...")

        blocks = self._build_transcript_blocks(sentences)
        if not blocks:
            return []

        # Pre-compute context matching data
        context_data = self._prepare_context_matching(user_context) if user_context else None

        # Score each block
        scored_blocks = []
        for block in blocks:
            score = self._nlp_score_block(block, user_context, energy_profile, context_data)
            scored_blocks.append((block, score))

        # Build clips by combining consecutive high-scoring blocks
        clips = self._build_clips_from_scored_blocks(scored_blocks, context_data)

        # Sort by score
        clips.sort(key=lambda x: x["viral_score"], reverse=True)

        if emit_progress:
            emit_progress(f"[NLP] Encontrou {len(clips)} clips candidatos")

        return clips

    def _prepare_context_matching(self, user_context):
        """Pre-process user context for efficient matching."""
        text_lower = user_context.lower()

        # Extract individual words (min 2 chars)
        all_words = [w.strip('.,;:!?"()') for w in text_lower.split()]
        context_words = [w for w in all_words if len(w) > 1]

        # Common Portuguese stop words / verbs / prepositions that are NOT names
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
        }

        # Extract names: any word 2-12 chars that isn't a common stop word
        # This catches "kim", "Kim", "KIM" etc.
        names = []
        for w in user_context.split():
            clean = w.strip('.,;:!?"()')
            if not clean or len(clean) < 2 or len(clean) > 12:
                continue
            clean_lower = clean.lower()
            # Skip stop words
            if clean_lower in stop_words_pt:
                continue
            # Skip pure numbers
            if clean.isdigit():
                continue
            # If capitalized in original OR is a short word (2-6 chars) not in stop list,
            # treat as potential name
            if clean[0].isupper() or (len(clean) <= 6 and clean_lower not in stop_words_pt):
                # Additional filter: skip very common verbs/adverbs even if short
                common_short = {"que", "mas", "nem", "dos", "das", "nos", "nas",
                                "uns", "uma", "umas", "ele", "ela", "eles", "elas",
                                "sao", "era", "foi", "ser", "ter", "ver", "dar",
                                "vir", "por", "pre", "pos", "sub", "pro"}
                if clean_lower not in common_short:
                    if clean_lower not in names:
                        names.append(clean_lower)

        # Extract multi-word phrases (3+ word sequences between punctuation/commas)
        phrases = []
        parts = re.split(r'[,;.!?]', text_lower)
        for part in parts:
            part = part.strip()
            words_in_part = part.split()
            if len(words_in_part) >= 3:
                phrases.append(part)
            # Also extract numeric phrases like "1 trilhao 100 bilhoes"
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
        score = 40  # Base score (lowered to give more room for context)

        # Hook detection (strong opening)
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

        # User context relevance (DOMINANT FACTOR when context exists)
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

        # Sentence completeness (ends with punctuation)
        if block["text"].strip()[-1:] in ".!?":
            completeness_score = 10
        else:
            completeness_score = -15

        total = (score + hook_score + emotional_score + punct_score
                 + context_score + duration_score + completeness_score
                 - filler_penalty)
        return max(0, min(100, total))

    def _compute_context_score(self, text, context_data):
        """Compute context relevance score — the most important factor for user intent."""
        score = 0

        # 1. Phrase matching (highest value — multi-word sequences)
        for phrase in context_data["phrases"]:
            if phrase in text:
                score += 20  # Full phrase match is very valuable

        # 2. Name matching (very high value — user mentioned specific people)
        for name in context_data["names"]:
            if name in text:
                score += 25  # Name match is critical for intent

        # 3. Individual word matching (standard value)
        for cw in context_data["words"]:
            if len(cw) > 1 and cw in text:
                score += 5

        # Cap at 60 but name matches can push higher
        name_bonus = sum(25 for n in context_data["names"] if n in text)
        if name_bonus > 0:
            return min(80, score)  # Names can dominate ranking
        return min(60, score)

    def _build_clips_from_scored_blocks(self, scored_blocks, context_data=None):
        """Build clips by combining consecutive blocks to reach target duration."""
        clips = []
        used_indices = set()

        # Sort by score to process best blocks first
        sorted_by_score = sorted(enumerate(scored_blocks), key=lambda x: x[1][1], reverse=True)

        for start_idx, (start_block, start_score) in sorted_by_score:
            if start_idx in used_indices:
                continue

            # Try to build a clip starting from this block
            clip_blocks = [start_block]
            clip_duration = start_block["duration"]
            clip_end_idx = start_idx

            # Extend forward to reach target duration
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

            # Mark used indices
            for idx in range(start_idx, clip_end_idx + 1):
                used_indices.add(idx)

            clip_text = " ".join(b["text"] for b in clip_blocks)
            clip_start = clip_blocks[0]["start"]
            clip_end = clip_blocks[-1]["end"]

            # Calculate average score of included blocks
            avg_score = sum(scored_blocks[i][1] for i in range(start_idx, clip_end_idx + 1)) / (clip_end_idx - start_idx + 1)

            # Determine grades
            hook_grade = "A" if start_score > 75 else ("B" if start_score > 50 else "C")
            flow_grade = "A" if clip_text.strip()[-1:] in ".!?" else "B"
            value_grade = "A" if avg_score > 70 else ("B" if avg_score > 50 else "C")
            energy_grade = "B"  # Default without LLM

            viral_score = int(avg_score)

            # Generate a simple title from first sentence
            title = self._generate_simple_title(clip_text)

            # Generate reason based on context match
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
        # Get first sentence
        for end_char in ["!", "?", "."]:
            idx = text.find(end_char)
            if 10 < idx < 80:
                title = text[:idx + 1].strip()
                return title

        # Fallback: first ~50 characters at word boundary
        words = text.split()[:8]
        title = " ".join(words)
        if len(title) > 60:
            title = title[:57] + "..."
        return title

    def _adjust_to_scene_boundaries(self, clips, scene_changes):
        """Adjust clip start/end to nearest scene boundary to avoid cutting mid-transition."""
        if not scene_changes or len(scene_changes) < 2:
            return clips

        adjusted = []
        for clip in clips:
            best_start = clip["start"]
            best_end = clip["end"]

            # Find nearest scene change within 2s of clip start
            for sc in scene_changes:
                if abs(sc - clip["start"]) < 2.0:
                    best_start = sc
                    break

            # Find nearest scene change within 2s of clip end
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

        # Already sorted by score
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
