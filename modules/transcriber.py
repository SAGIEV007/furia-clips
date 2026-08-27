import os
import json
import hashlib
import time
import subprocess
import shutil
import gc
import tempfile
import re as _re

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "cache")


# Marcas de uma falha da pilha de GPU, e não do áudio nem do modelo. A biblioteca
# só é aberta de verdade quando a inferência começa, então a queda para CPU que
# existia na carga nunca chegava a valer: numa máquina com placa presente, driver
# presente e cuBLAS ausente o modelo carregava em CUDA e morria quinze segundos
# depois, com o vídeo inteiro por transcrever.
_GPU_FAILURE_MARKS = (
    "cublas", "cudnn", "cudart", "libcu", "cuda", "nvidia",
    "no kernel image", "out of memory", "device-side assert",
)


def _looks_like_a_gpu_failure(exc):
    """Whether this exception is the GPU stack failing, not the audio."""
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(mark in text for mark in _GPU_FAILURE_MARKS)


def _normalize_for_echo(text):
    """Compara texto ignorando pontuação e caixa, que é como o eco volta."""
    return _re.sub(r"[^a-zà-ÿ0-9 ]+", "", str(text or "").lower()).strip()


class Transcriber:
    # O openai-whisper carrega o áudio inteiro em uma matriz float32. Em uma
    # entrevista de 45 minutos isso cria um pico desnecessário; a transcrição
    # longa usa janelas independentes e mantém somente os segmentos JSON.
    LONG_SOURCE_CHUNK_SECONDS = 300.0

    # A janela do `initial_prompt` do Whisper é curta.
    # São 337 entradas no
    # léxico: enfiar todas trocaria um erro de nome por um reconhecedor pior no
    # vídeo inteiro.
    VOCABULARY_PROMPT_MAX_CHARS = 380
    # Só a abertura pode ser eco do prompt. Depois disso é outra coisa, e
    # descartar seria adivinhar.
    ECHOED_PROMPT_WINDOW_S = 30.0

    def __init__(self, model_name="small", language="pt", word_timestamps=False, beam_size=1,
                 device="auto", vocabulary_bias=True):
        self.model_name = model_name
        self.language = language
        self.word_timestamps = bool(word_timestamps)
        self.beam_size = max(1, int(beam_size or 1))
        self.requested_device = str(device or "auto").lower()
        self.device = "cpu"
        self.compute_type = "int8"
        self.model = None
        self._engine = "cache"
        # `initial_prompt` é conhecido por induzir repetição em alguns áudios.
        # Um recurso que às vezes piora precisa de interruptor, senão um vídeo
        # estragado não tem como ser recuperado sem editar código.
        self.vocabulary_bias = bool(vocabulary_bias)
        self._vocabulary_prompt_cache = None
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _vocabulary_prompt(self):
        """O viés de vocabulário que vai antes do reconhecedor decidir.

        O léxico do projeto diz o problema na própria nota: "'Nicolas Ferreira'
        aparece mais vezes que 'Nikolas Ferreira', e a forma rara é a certa". Um
        reconhecedor escolhe a frequente. Corrigir depois conserta a grafia, mas
        não recupera o que virou outra palavra — "Kataguiri" ouvido como "cata
        guiri" é erro de segmentação, e nenhuma tabela de troca alcança isso.

        Sai como **frase**, não como lista: uma lista solta faz o reconhecedor
        repetir, e a frase ainda modela a pontuação do que vem depois — que é o
        que separa uma legenda utilizável de um bloco de 128 palavras sem um
        ponto final.

        Só nomes com ``confirmado=true``. Enviesar para uma grafia que ninguém
        aprovou seria corrigir em silêncio pela porta dos fundos, pior que
        corrigir depois, porque não deixa rastro em ``conferir_no_audio``.
        """
        if not self.vocabulary_bias:
            return ""
        if self._vocabulary_prompt_cache is not None:
            return self._vocabulary_prompt_cache

        nomes = []
        try:
            caminho = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "lexico", "entidades_chub.json",
            )
            with open(caminho, encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            entradas = [item for item in dados.get("entradas", []) if item.get("confirmado")]
            entradas.sort(key=lambda item: int(item.get("mencoes_chub") or 0), reverse=True)
            for item in entradas:
                nome = str(item.get("canonico") or "").strip()
                if nome and nome not in nomes:
                    nomes.append(nome)
        except (OSError, ValueError, KeyError, TypeError):
            nomes = []

        abertura = "Entrevista em português do Brasil com Renan Santos, do MBL e do Partido Missão"
        assunto = []
        for nome in nomes:
            if nome in abertura or nome in assunto:
                continue
            tentativa = assunto + [nome]
            frase = f"{abertura}, falando sobre {', '.join(tentativa)}."
            if len(frase) > self.VOCABULARY_PROMPT_MAX_CHARS:
                break
            assunto = tentativa
        prompt = f"{abertura}, falando sobre {', '.join(assunto)}." if assunto else f"{abertura}."
        self._vocabulary_prompt_cache = prompt
        return prompt

    def _drop_echoed_prompt(self, result):
        """Tira o viés da transcrição quando o reconhecedor o devolve como fala.

        É um modo de falha documentado do `initial_prompt`, e aqui ele é caro: a
        linha vira a primeira legenda do vídeo, entra no corte e pode virar aspas
        numa headline. Uma citação de algo que ninguém disse é o erro mais grave
        que este projeto pode cometer, e ele nasceria de um recurso feito para
        melhorar a transcrição.

        Só o eco literal sai, e só na abertura. Ele cita esses nomes o tempo
        todo — é o assunto dele —, então qualquer regra mais larga apagaria fala
        de verdade.
        """
        prompt = self._vocabulary_prompt()
        if not prompt:
            return
        alvo = _normalize_for_echo(prompt)
        segments = result.get("segments") or []
        mantidos = [
            segment for segment in segments
            if not (
                float(segment.get("start", 0) or 0) <= self.ECHOED_PROMPT_WINDOW_S
                and _normalize_for_echo(segment.get("text", "")) == alvo
            )
        ]
        if len(mantidos) == len(segments):
            return
        for posicao, segment in enumerate(mantidos):
            segment["id"] = posicao
        result["segments"] = mantidos
        result["segment_count"] = len(mantidos)
        result["full_text"] = " ".join(
            str(segment.get("text") or "") for segment in mantidos
        ).strip()
        result["prompt_ecoado_removido"] = True

    def _detect_device(self):
        if self.requested_device in {"cpu", "cuda"}:
            return self.requested_device
        try:
            import ctranslate2
            return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except (ImportError, AttributeError, RuntimeError):
            return "cpu"

    def _get_cache_key(self, audio_path):
        stat = os.stat(audio_path)
        raw = f"{os.path.abspath(audio_path)}|{stat.st_size}|{stat.st_mtime}|{self.model_name}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cache_path(self, cache_key):
        return os.path.join(CACHE_DIR, f"transcription_{cache_key}.json")

    def _load_from_cache(self, audio_path, emit_progress=None):
        cache_key = self._get_cache_key(audio_path)
        cache_path = self._get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if emit_progress:
                    emit_progress("Transcricao carregada do cache (instantaneo)!")
                return data
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def _save_to_cache(self, audio_path, result):
        cache_key = self._get_cache_key(audio_path)
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except IOError:
            pass

    def load_model(self, emit_progress=None):
        if emit_progress:
            emit_progress(f"Carregando modelo Whisper '{self.model_name}'...")

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            if emit_progress:
                emit_progress("faster-whisper nao encontrado. Usando openai-whisper como fallback...")
            import whisper
            import torch
            # ``requested_device`` is honoured here too, otherwise a fall back to
            # CPU after a GPU failure would reload straight back onto the card.
            if self.requested_device in {"cpu", "cuda"}:
                device = self.requested_device
            else:
                device = "cuda" if torch.cuda.is_available() else "cpu"
            self.device = device
            self.compute_type = "float16" if device == "cuda" else "float32"
            self.model = whisper.load_model(self.model_name, device=device)
            self._engine = "openai-whisper"
            if emit_progress:
                emit_progress(f"Modelo carregado: openai-whisper no {device}")
            return

        detected_device = self._detect_device()
        device_candidates = [detected_device]
        if detected_device == "cuda":
            device_candidates.append("cpu")
        load_errors = []
        for device in device_candidates:
            compute_candidates = ["float16", "int8_float16", "int8"] if device == "cuda" else ["int8", "int8_float32", "float32"]
            for compute_type in compute_candidates:
                model_kwargs = {
                    "device": device,
                    "compute_type": compute_type,
                }
                if device == "cpu":
                    model_kwargs["cpu_threads"] = max(1, (os.cpu_count() or 4) - 1)
                try:
                    self.model = WhisperModel(self.model_name, **model_kwargs)
                    self.device = device
                    self.compute_type = compute_type
                    self._engine = "faster-whisper"
                    if emit_progress:
                        emit_progress(
                            f"Modelo carregado: faster-whisper ({self.compute_type}) no {self.device.upper()}; "
                            f"beam={self.beam_size}, word_timestamps={'on' if self.word_timestamps else 'off'}"
                        )
                        if detected_device == "cuda" and device == "cpu":
                            emit_progress(
                                "[Whisper] CUDA detectada, mas o backend não aceitou os tipos disponíveis; usando CPU com configuração segura.",
                                "warning",
                            )
                    return
                except (OSError, RuntimeError, ValueError) as exc:
                    load_errors.append(f"{device}/{compute_type}: {str(exc)[:160]}")

        detail = " | ".join(load_errors[-4:])
        raise RuntimeError(f"Não foi possível carregar faster-whisper com configuração segura. {detail}")

    def _probe_duration(self, video_path):
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return None
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", video_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
            )
            return float(result.stdout.strip()) if result.stdout.strip() else None
        except (OSError, ValueError, subprocess.SubprocessError):
            return None

    def _check_audio_stream(self, video_path, emit_progress=None):
        """Check if the video file contains an audio stream. Returns True if audio exists."""
        try:
            ffprobe = shutil.which("ffprobe")
            if not ffprobe:
                return True  # Can't check, assume it has audio

            result = subprocess.run(
                [ffprobe, "-v", "quiet", "-show_streams", "-select_streams", "a", video_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
            )
            if "codec_type=audio" not in result.stdout:
                if emit_progress:
                    emit_progress(
                        "ERRO: Este video NAO contem audio! "
                        "Provavelmente foi baixado no formato DASH (so video). "
                        "Baixe novamente com audio incluido.",
                        "error",
                    )
                return False
            return True
        except Exception:
            return True  # Can't check, assume it has audio

    def _sanitize_path_for_ffmpeg(self, audio_path):
        """Copy file to a safe temp path if filename has special chars that break FFmpeg on Windows."""
        basename = os.path.basename(audio_path)
        if _re.search(r'[^\w\s.\-()]', basename, _re.ASCII):
            safe_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "cache")
            os.makedirs(safe_dir, exist_ok=True)
            ext = os.path.splitext(basename)[1]
            cache_key = self._get_cache_key(audio_path)
            safe_path = os.path.join(safe_dir, f"temp_audio_{cache_key[:16]}{ext}")
            if not os.path.exists(safe_path):
                shutil.copy2(audio_path, safe_path)
            return safe_path
        return audio_path

    def transcribe(self, audio_path, emit_progress=None, cancel_check=None):
        if cancel_check:
            cancel_check()
        cached = self._load_from_cache(audio_path, emit_progress)
        if cached:
            return cached

        # Check for audio stream before anything else
        if not self._check_audio_stream(audio_path, emit_progress):
            raise ValueError(
                "O video nao contem stream de audio. "
                "Baixe o video novamente incluindo o audio. "
                "No yt-dlp use: -f bestvideo+bestaudio --merge-output-format mp4"
            )

        duration = self._probe_duration(audio_path)
        if duration and duration >= 900 and emit_progress:
            minutes = duration / 60
            emit_progress(
                f"Fallback local: vídeo de {minutes:.1f} min; processamento CPU pode levar vários minutos. "
                "Gemini Online é recomendado para reduzir este tempo.",
                "warning",
            )

        if self.model is None:
            self.load_model(emit_progress)
        if cancel_check:
            cancel_check()

        # Handle filenames with special characters (accents, etc)
        working_path = self._sanitize_path_for_ffmpeg(audio_path)

        if emit_progress:
            emit_progress("Iniciando transcricao...")

        start_time = time.time()

        try:
            result = self._run_engine(working_path, emit_progress, cancel_check)
        except Exception as exc:
            # Cancellation and audio problems carry none of these marks and are
            # re-raised untouched.
            if self.device != "cuda" or not _looks_like_a_gpu_failure(exc):
                raise
            if emit_progress:
                emit_progress(
                    f"[Whisper] A placa aceitou o modelo mas falhou ao transcrever "
                    f"({str(exc)[:120]}). Recomeçando na CPU; vai demorar mais e vai terminar.",
                    "warning",
                )
            self._fall_back_to_cpu(emit_progress)
            result = self._run_engine(working_path, emit_progress, cancel_check)

        elapsed = time.time() - start_time
        if emit_progress:
            emit_progress(
                f"Transcricao completa: {len(result['segments'])} segmentos, "
                f"{len(result['full_text'])} caracteres ({elapsed:.0f}s)"
            )

        # Antes da revisão: o eco do próprio viés não é fala, e deixá-lo passar
        # o entregaria à correção de nomes como se fosse.
        self._drop_echoed_prompt(result)
        self._revise_captions(result, emit_progress)
        self._save_to_cache(audio_path, result)
        return result

    @staticmethod
    def _revise_captions(result, emit_progress=None):
        """Fix the names and the numbers before anything downstream reads them.

        This pass existed as a module and was wired to nothing, which is why the
        editor kept seeing "Quim Catagui" on screen after it was written: every
        clip, every caption and every headline was reading the raw recogniser
        output. It runs here, at the one point both engines pass through, so no
        later path can skip it.

        What it changes is narrow on purpose — proper nouns somebody vouched for,
        the digits that were spoken as articles, and question marks on sentences
        that are unambiguously questions. Words whose twin would change the
        meaning are counted and reported, never rewritten.
        """
        from .caption_lexicon import review_caption

        changed = 0
        to_check: list[str] = []
        for segment in result.get("segments") or []:
            verdict = review_caption(segment.get("text", ""))
            if verdict["alterado"]:
                segment["text"] = verdict["texto"]
                changed += 1
            for item in verdict["conferir"]:
                to_check.append(str(item.get("palavra") or ""))
        if changed:
            result["full_text"] = " ".join(
                str(segment.get("text") or "") for segment in result.get("segments") or []
            ).strip()
        result["revisao_legenda"] = {"linhas_corrigidas": changed, "conferir_no_audio": sorted(set(to_check))}
        if emit_progress and changed:
            aviso = f"; {len(set(to_check))} palavra(s) para conferir no áudio" if to_check else ""
            emit_progress(f"[Léxico] {changed} linha(s) corrigidas (nomes, números, interrogação){aviso}.", "info")

    def _run_engine(self, audio_path, emit_progress=None, cancel_check=None):
        if self._engine == "faster-whisper":
            return self._transcribe_faster_whisper(audio_path, emit_progress, cancel_check)
        return self._transcribe_openai_whisper(audio_path, emit_progress, cancel_check)

    def _fall_back_to_cpu(self, emit_progress=None):
        """Rebuild the model on the CPU after the GPU failed mid-transcription.

        The device is pinned rather than re-detected: detection is what chose
        CUDA in the first place, and it will choose it again — a card that is
        present and a runtime that is missing look identical to
        ``get_cuda_device_count``.
        """
        self.model = None
        self.requested_device = "cpu"
        self.device = "cpu"
        self.load_model(emit_progress)
        if self.device != "cpu":
            raise RuntimeError("A queda para CPU não foi respeitada ao recarregar o modelo.")

    def _transcribe_faster_whisper(self, audio_path, emit_progress=None, cancel_check=None):
        segments_iter, info = self.model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            beam_size=self.beam_size,
            word_timestamps=self.word_timestamps,
            # O viés de vocabulário: nomes do léxico antes de o reconhecedor
            # decidir, em vez de tabela de troca depois que ele já errou.
            initial_prompt=self._vocabulary_prompt() or None,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
        )

        segments = []
        full_text_parts = []

        for seg in segments_iter:
            if cancel_check:
                cancel_check()
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                    })

            segment_data = {
                "id": len(segments),
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": words,
            }
            segments.append(segment_data)
            full_text_parts.append(seg.text.strip())

            if emit_progress and len(segments) % 50 == 0:
                emit_progress(f"Transcrevendo... {len(segments)} segmentos processados")

        full_text = " ".join(full_text_parts)
        return {
            "segments": segments,
            "segment_count": len(segments),
            "full_text": full_text,
            "language": self.language,
        }

    def _transcribe_openai_whisper(self, audio_path, emit_progress=None, cancel_check=None):
        if cancel_check:
            cancel_check()
        duration = self._probe_duration(audio_path)
        if duration and duration >= self.LONG_SOURCE_CHUNK_SECONDS * 2:
            return self._transcribe_openai_whisper_chunked(
                audio_path, duration, emit_progress, cancel_check
            )

        # O openai-whisper usa fp16=True por padrão, mas CPU não oferece suporte
        # eficiente a esse tipo. O fallback precisa fixar fp16=False fora de CUDA.
        result = self.model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            verbose=False,
            word_timestamps=self.word_timestamps,
            # O mesmo viés do outro motor: os dois caminhos têm de ouvir os
            # mesmos nomes, senão a qualidade da legenda passa a depender de qual
            # biblioteca a máquina do editor tinha instalada.
            initial_prompt=self._vocabulary_prompt() or None,
            fp16=self.device == "cuda",
        )
        return self._normalize_openai_result(result, cancel_check)

    def _transcribe_openai_whisper_chunked(self, audio_path, duration, emit_progress=None, cancel_check=None):
        """Transcreve uma fonte longa em janelas de áudio independentes.

        ``clip_timestamps`` devolve timestamps absolutos, portanto o restante do
        Furia 1 continua navegando, gerando captions e selecionando cortes na
        mesma linha do tempo. Cada janela libera a matriz de áudio antes da
        próxima, evitando o OOM observado na entrevista de 44,5 minutos.
        """
        segments = []
        full_text_parts = []
        chunk_count = max(1, int((duration + self.LONG_SOURCE_CHUNK_SECONDS - 1) // self.LONG_SOURCE_CHUNK_SECONDS))
        prompt = self._vocabulary_prompt() or None
        for chunk_index in range(chunk_count):
            if cancel_check:
                cancel_check()
            start = chunk_index * self.LONG_SOURCE_CHUNK_SECONDS
            end = min(float(duration), start + self.LONG_SOURCE_CHUNK_SECONDS)
            if emit_progress:
                emit_progress(
                    f"Transcrevendo janela {chunk_index + 1}/{chunk_count} "
                    f"({start / 60:.1f}–{end / 60:.1f} min)..."
                )
            chunk_path = self._extract_audio_chunk(audio_path, start, end)
            try:
                result = self.model.transcribe(
                    chunk_path,
                    language=self.language,
                    task="transcribe",
                    verbose=False,
                    word_timestamps=self.word_timestamps,
                    initial_prompt=prompt if chunk_index == 0 else None,
                    condition_on_previous_text=False,
                    fp16=self.device == "cuda",
                )
                normalized = self._normalize_openai_result(result, cancel_check)
                for seg in normalized["segments"]:
                    # The temporary audio begins at ``start``; move every
                    # segment/word back onto the source timeline before the
                    # temporary file is discarded.
                    seg["start"] = round(float(seg["start"]) + start, 3)
                    seg["end"] = round(float(seg["end"]) + start, 3)
                    for word in seg.get("words") or []:
                        word["start"] = round(float(word["start"]) + start, 3)
                        word["end"] = round(float(word["end"]) + start, 3)
                    # Whisper can return a blank boundary segment. It is not
                    # useful to captions or candidate generation and can become
                    # a duplicate if a future decoder adds overlap around this
                    # seam.
                    if str(seg.get("text") or "").strip():
                        segments.append(seg)
                full_text_parts.append(normalized["full_text"])
                del result, normalized
                gc.collect()
            finally:
                try:
                    os.unlink(chunk_path)
                except OSError:
                    pass
        for index, segment in enumerate(segments):
            segment["id"] = index
        return {
            "segments": segments,
            "segment_count": len(segments),
            "full_text": " ".join(part for part in full_text_parts if part).strip(),
            "language": self.language,
            "chunked": True,
            "chunk_count": chunk_count,
        }

    def _extract_audio_chunk(self, audio_path, start, end):
        """Extract one bounded PCM window so Whisper never loads the full source."""
        duration = max(0.1, float(end) - float(start))
        handle = tempfile.NamedTemporaryFile(prefix="furia-whisper-", suffix=".wav", dir=CACHE_DIR, delete=False)
        chunk_path = handle.name
        handle.close()
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg é necessário para transcrever fontes longas em janelas de memória segura.")
        command = [
            ffmpeg, "-nostdin", "-loglevel", "error", "-y",
            "-ss", f"{float(start):.3f}", "-i", audio_path,
            "-t", f"{duration:.3f}", "-vn", "-ac", "1", "-ar", "16000",
            "-f", "wav", chunk_path,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(180, int(duration * 3)),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            try:
                os.unlink(chunk_path)
            except OSError:
                pass
            raise RuntimeError(f"Não foi possível extrair uma janela de áudio: {exc}") from exc
        if result.returncode != 0:
            try:
                os.unlink(chunk_path)
            except OSError:
                pass
            detail = (result.stderr or "").strip()[-400:]
            raise RuntimeError(f"FFmpeg falhou ao extrair janela de áudio: {detail}")
        return chunk_path

    def _normalize_openai_result(self, result, cancel_check=None):
        segments = []
        for seg in result.get("segments", []):
            if cancel_check:
                cancel_check()
            segment_data = {
                "id": len(segments),
                "start": round(seg["start"], 3),
                "end": round(seg["end"], 3),
                "text": seg["text"].strip(),
                "words": [],
            }
            for word_info in seg.get("words", []):
                segment_data["words"].append({
                    "word": word_info["word"].strip(),
                    "start": round(word_info["start"], 3),
                    "end": round(word_info["end"], 3),
                })
            segments.append(segment_data)
        return {
            "segments": segments,
            "segment_count": len(segments),
            "full_text": result.get("text", "").strip(),
            "language": result.get("language", self.language),
        }
