"""Gemini multimodal video analysis with resumable Files API upload.

The module is intentionally optional: when no key is configured or the online
analysis fails, callers can continue with the canonical transcript path. API
keys are sent only in headers and never included in logs or returned payloads.
"""

from __future__ import annotations

import json
import mimetypes
import os
import random
import subprocess
import tempfile
import time
from pathlib import Path

import requests


class GeminiVideoError(RuntimeError):
    pass


class GeminiVideoAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = str(api_key or "").strip()
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com"
        self.session = requests.Session()
        self.session.headers.update({"x-goog-api-key": self.api_key})

    def analyze(self, video_path: str, editorial_context: dict | None = None, user_context: str = "", emit_progress=None, cancel_check=None) -> dict:
        if not self.api_key:
            raise GeminiVideoError("Gemini não configurado")
        path = Path(video_path).expanduser().resolve()
        if not path.is_file():
            raise GeminiVideoError("Vídeo não encontrado para análise multimodal")

        if cancel_check:
            cancel_check()
        analysis_path, analysis_meta = self._prepare_analysis_media(path, emit_progress, cancel_check)
        espera = self._analysis_timeout(analysis_meta.get("original_duration_seconds") or 0)
        analysis_meta["network_timeout_seconds"] = espera
        try:
            mime_type = mimetypes.guess_type(analysis_path.name)[0] or "video/mp4"
            if emit_progress:
                emit_progress(
                    f"[Gemini] Enviando a cópia audiovisual compactada para análise online "
                    f"(espera de até {espera // 60} min, proporcional à duração da fonte)...",
                    "info",
                )
            file_info = self._upload_file(analysis_path, mime_type, emit_progress, cancel_check, timeout=espera)
            self._wait_until_active(file_info.get("name", ""), emit_progress, cancel_check)

            prompt_context = dict(editorial_context or {})
            prompt_context["analysis_input"] = analysis_meta
            prompt = self._build_prompt(prompt_context, user_context)
            request_payload = {
                "contents": [{
                    "parts": [
                        {"file_data": {"mime_type": mime_type, "file_uri": file_info.get("uri", "")}},
                        {"text": prompt},
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 8192,
                    "responseMimeType": "application/json",
                },
            }
            response = self._generate_content(request_payload, emit_progress, cancel_check, timeout=espera)
            if response.status_code != 200:
                raise GeminiVideoError(f"Gemini retornou HTTP {response.status_code}: {self._error_text(response)}")
            payload = response.json()
            text = self._extract_text(payload)
            if not text:
                raise GeminiVideoError("Gemini não retornou conteúdo multimodal")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = json.loads(self._strip_fence(text))
            if not isinstance(parsed, dict):
                raise GeminiVideoError("Resposta multimodal fora do formato esperado")
            parsed["source"] = "gemini_video"
            parsed["model"] = self.model
            parsed["analysis_input"] = analysis_meta
            identity = parsed.get("source_identity") if isinstance(parsed.get("source_identity"), dict) else {}
            raw_status = str(identity.get("status") or "unverified").strip().lower()
            status_aliases = {"validated": "validated", "confirmed": "validated", "match": "validated", "mismatch": "mismatch", "wrong_source": "mismatch", "uncertain": "unverified", "unknown": "unverified"}
            parsed["source_identity_status"] = status_aliases.get(raw_status, "unverified")
            try:
                parsed["source_identity_confidence"] = max(0.0, min(1.0, float(identity.get("confidence", 0) or 0)))
            except (TypeError, ValueError):
                parsed["source_identity_confidence"] = 0.0
            parsed["multimodal_evidence_policy"] = "auxiliary_until_identity_validated"
            return parsed
        finally:
            if analysis_path != path:
                try:
                    analysis_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _probe_duration(path: Path) -> float:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return max(0.0, float((result.stdout or "").strip() or 0.0))
        except (OSError, ValueError, subprocess.SubprocessError):
            return 0.0

    @classmethod
    def _proxy_profile(cls, duration_seconds: float) -> dict:
        duration = max(0.0, float(duration_seconds or 0.0))
        if duration > 45 * 60:
            fps, maxrate = "1/12", "100k"
        elif duration > 20 * 60:
            fps, maxrate = "1/8", "130k"
        elif duration > 10 * 60:
            fps, maxrate = "1/4", "180k"
        else:
            fps, maxrate = "1", "350k"
        return {"fps": fps, "maxrate": maxrate, "max_width": 640, "audio_bitrate": "16k"}

    # Quanto esperar pela rede, medido contra o que a fonte é — não um número fixo.
    #
    # O perfil acima já sabe que a fonte é longa: acima de 45 minutos ele desce a
    # 1 quadro a cada 12 segundos para caber. Só que os dois tempos-limite de rede
    # eram 180 segundos, sempre, e isso condenava a chamada antes de ela sair.
    #
    # No diagnóstico que o editor exportou: um vídeo de 139,7 minutos levou 15
    # minutos e 26 segundos só para compactar, mais 47 segundos de upload — e aí
    # o programa deu ao Gemini 3 minutos para analisar duas horas de material e
    # desistiu com "Read timed out. (read timeout=180)". Aconteceu duas vezes na
    # mesma sessão: 45 minutos de espera para nenhum resultado.
    #
    # Gastar quinze minutos preparando e três esperando é a proporção errada.
    ANALYSIS_TIMEOUT_MIN_S = 180
    ANALYSIS_TIMEOUT_MAX_S = 1500
    ANALYSIS_TIMEOUT_PER_MINUTE_S = 12

    @classmethod
    def _analysis_timeout(cls, duration_seconds: float) -> int:
        minutos = max(0.0, float(duration_seconds or 0.0)) / 60.0
        estimado = cls.ANALYSIS_TIMEOUT_MIN_S + minutos * cls.ANALYSIS_TIMEOUT_PER_MINUTE_S
        return int(min(cls.ANALYSIS_TIMEOUT_MAX_S, max(cls.ANALYSIS_TIMEOUT_MIN_S, estimado)))

    @classmethod
    def _prepare_analysis_media(cls, path: Path, emit_progress=None, cancel_check=None):
        duration = cls._probe_duration(path)
        profile = cls._proxy_profile(duration)
        descriptor = {
            "used_proxy": True,
            "original_duration_seconds": round(duration, 3) if duration else None,
            "visual_sampling": f"{profile['fps']} fps",
            "max_width": profile["max_width"],
            "audio": "mono 16 kHz",
            "purpose": "reduzir tamanho e tokens; a transcrição canônica permanece textual",
        }
        if emit_progress:
            emit_progress(
                f"[Gemini] Compactando cópia de análise: até {profile['max_width']} px, {profile['fps']} fps, áudio mono 16 kHz; a fonte original não será alterada.",
                "info",
            )
        if cancel_check:
            cancel_check()
        fd, proxy_name = tempfile.mkstemp(prefix="furia-gemini-proxy-", suffix=".mp4")
        os.close(fd)
        proxy = Path(proxy_name)
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
            "-vf", f"scale='min({profile['max_width']},iw)':-2,fps={profile['fps']}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "36",
            "-maxrate", profile["maxrate"], "-bufsize", profile["maxrate"],
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", profile["audio_bitrate"],
            "-ac", "1", "-ar", "16000", "-movflags", "+faststart", str(proxy),
        ]
        process = None
        try:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            while process.poll() is None:
                if cancel_check:
                    try:
                        cancel_check()
                    except Exception:
                        process.kill()
                        process.wait(timeout=10)
                        raise
                time.sleep(0.5)
            stderr = process.stderr.read() if process.stderr else ""
            if process.returncode != 0:
                raise GeminiVideoError(f"Não foi possível compactar a cópia para análise: {stderr[-240:]}")
            return proxy, descriptor
        except FileNotFoundError as exc:
            proxy.unlink(missing_ok=True)
            raise GeminiVideoError("FFmpeg é necessário para preparar a cópia compactada do Gemini.") from exc
        except Exception:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            proxy.unlink(missing_ok=True)
            raise

    def _generate_content(self, request_payload: dict, emit_progress=None, cancel_check=None, timeout: int | None = None):
        """Retry only transient API failures; the video upload is not repeated."""
        endpoint = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        retryable = {408, 429, 500, 502, 503, 504}
        max_attempts = 3
        last_response = None
        for attempt in range(1, max_attempts + 1):
            if cancel_check:
                cancel_check()
            response = self.session.post(
                endpoint, json=request_payload, timeout=timeout or self.ANALYSIS_TIMEOUT_MIN_S
            )
            last_response = response
            if response.status_code == 200:
                return response
            if response.status_code not in retryable or attempt == max_attempts:
                break
            if emit_progress:
                emit_progress(
                    f"[Gemini] HTTP {response.status_code} transitório; nova tentativa "
                    f"{attempt + 1}/{max_attempts} com backoff...",
                    "warning",
                )
            self._sleep_with_cancel(min(2 ** (attempt - 1), 8) + random.uniform(0.0, 0.5), cancel_check)
        raise GeminiVideoError(
            f"Gemini retornou HTTP {last_response.status_code}: {self._error_text(last_response)}"
        )

    @staticmethod
    def _sleep_with_cancel(seconds, cancel_check=None):
        deadline = time.monotonic() + max(0.0, float(seconds))
        while True:
            if cancel_check:
                cancel_check()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.5, remaining))

    def _upload_file(self, path: Path, mime_type: str, emit_progress=None, cancel_check=None, timeout: int | None = None) -> dict:
        if cancel_check:
            cancel_check()
        size = path.stat().st_size
        start = self.session.post(
            f"{self.base_url}/upload/v1beta/files",
            headers={
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(size),
                "X-Goog-Upload-Header-Content-Type": mime_type,
                "Content-Type": "application/json",
            },
            json={"file": {"display_name": path.name}},
            timeout=60,
        )
        if start.status_code not in {200, 201}:
            raise GeminiVideoError(f"Falha ao iniciar upload: HTTP {start.status_code}")
        upload_url = start.headers.get("x-goog-upload-url") or start.headers.get("X-Goog-Upload-URL")
        if not upload_url:
            raise GeminiVideoError("Gemini não retornou URL de upload resumível")

        if cancel_check:
            cancel_check()
        with path.open("rb") as handle:
            upload = self.session.post(
                upload_url,
                headers={
                    "Content-Length": str(size),
                    "X-Goog-Upload-Offset": "0",
                    "X-Goog-Upload-Command": "upload, finalize",
                    "Content-Type": mime_type,
                },
                data=handle,
                timeout=timeout or self.ANALYSIS_TIMEOUT_MIN_S,
            )
        if cancel_check:
            cancel_check()
        if upload.status_code not in {200, 201}:
            raise GeminiVideoError(f"Falha ao enviar vídeo: HTTP {upload.status_code}")
        if emit_progress:
            emit_progress("[Gemini] Upload concluído; aguardando processamento do arquivo...", "info")
        return upload.json().get("file", upload.json())

    def _wait_until_active(self, file_name: str, emit_progress=None, cancel_check=None) -> None:
        if not file_name:
            raise GeminiVideoError("Gemini não informou o identificador do arquivo")
        for attempt in range(180):
            if cancel_check:
                cancel_check()
            result = self.session.get(f"{self.base_url}/v1beta/{file_name}", timeout=30)
            if result.status_code != 200:
                raise GeminiVideoError(f"Falha ao consultar arquivo: HTTP {result.status_code}")
            payload = result.json()
            state = payload.get("state") or payload.get("file", {}).get("state")
            if state == "ACTIVE":
                return
            if state == "FAILED":
                raise GeminiVideoError("Gemini falhou ao processar o vídeo")
            if emit_progress and attempt % 6 == 0:
                emit_progress(f"[Gemini] Processando vídeo online ({attempt * 5}s)...", "info")
            self._sleep_with_cancel(5, cancel_check)
        raise GeminiVideoError("Tempo limite aguardando processamento do vídeo no Gemini")

    @staticmethod
    def _build_prompt(editorial_context: dict, user_context: str) -> str:
        focus = str(editorial_context.get("focus", "generic_political") or "generic_political").strip().lower()
        renan_focus = focus in {"renan_santos", "renan", "renan_santos_politics"}
        role = (
            "editor sênior de cortes políticos do Renan Santos/MBL"
            if renan_focus
            else "editor sênior de cortes políticos, sem presumir a identidade de qualquer participante"
        )
        default_instruction = (
            "Nenhuma; aplique automaticamente o perfil político do Renan Santos/MBL, mas confirme a identidade no vídeo."
            if renan_focus
            else "Nenhuma; aplique um critério editorial político genérico e identifique os participantes apenas quando houver evidência."
        )
        transcript_reference = str(editorial_context.get("transcript_reference", "") or "").strip()
        analysis_input = editorial_context.get("analysis_input") if isinstance(editorial_context.get("analysis_input"), dict) else {}
        transcript_block = (
            "\nTRANSCRIÇÃO CANÔNICA FORNECIDA PELO EDITOR:\n"
            f"{transcript_reference}\n"
            "Use-a como fonte principal para as falas e para localizar o argumento. Ela pode ser mais confiável que uma nova transcrição automática; não substitua a timeline dela.\n"
            if transcript_reference else ""
        )
        return f"""Você é um analista audiovisual e {role}.
Analise o vídeo inteiro usando áudio e imagem, sem inventar fatos externos. O objetivo é preparar uma etapa posterior de corte, não escrever legendas.

Identidade esperada da fonte e do foco editorial:
{json.dumps({'source_file_name': editorial_context.get('source_file_name', ''), 'expected_focus': editorial_context.get('focus', 'generic_political')}, ensure_ascii=False)}

Contexto determinístico já extraído da transcrição:
{json.dumps(editorial_context, ensure_ascii=False)[:12000]}

Instrução opcional do editor:
{user_context or default_instruction}
{transcript_block}
Entrada audiovisual enviada:
{json.dumps(analysis_input, ensure_ascii=False)}

Entregue apenas JSON neste formato:
{{
  "source_identity": {{"status": "validated|mismatch|unverified", "observed_title_or_program": "...", "primary_subject": "...", "evidence": "...", "confidence": 0.0}},
  "global_description": "descrição objetiva do programa, entrevista e assuntos",
  "transcript_segments": [{{"start": "MM:SS", "end": "MM:SS", "text": "fala literal ou fiel ao áudio", "speaker": "Renan|mediador|convidado|desconhecido", "is_question": false}}],
  "focus_windows": [{{"start": "MM:SS", "end": "MM:SS", "reason": "...", "confidence": 0.0}}],
  "speaker_observations": [{{"window": "MM:SS-MM:SS", "speaker_role": "Renan|mediador|convidado|desconhecido", "evidence": "...", "confidence": 0.0}}],
  "qa_moments": [{{"start": "MM:SS", "end": "MM:SS", "question_present": true, "answer_present": true, "renan_focus": true, "overlap_suspected": false, "reason": "...", "confidence": 0.0}}],
  "audio_visual_signals": [{{"start": "MM:SS", "end": "MM:SS", "signal": "pausa|sobreposicao|risos|aplausos|tensao|musica|mudanca_de_bloco|enquadramento", "note": "..."}}],
  "visual_observations": [{{"start": "MM:SS", "end": "MM:SS", "visual_format": "talking_head|entrevista|podcast|react|split_screen|evidencia_externa|b_roll_argumentativo|palco|institucional|campanha|text_panel|fake_tweet|visual_meme|desconhecido", "has_text_panel": false, "fake_tweet": false, "social_post": false, "visual_meme": false, "split_screen": false, "external_evidence": false, "composition_note": "...", "confidence": 0.0}}],
  "limitations": ["..."],
  "analysis_confidence": 0.0
}}

Timestamps devem usar MM:SS. Gere segmentos suficientes para a seleção editorial, sem inventar falas. Não afirme reconhecimento perfeito de voz. Marque como desconhecido quando houver dúvida. Preserve a pergunta quando ela for necessária para entender a resposta. Antes de usar qualquer observação visual como evidência, compare o programa e o sujeito observados com a identidade esperada; se não puder confirmar, use source_identity.status=unverified. Se identificar fonte incompatível, use mismatch e não trate o restante como evidência de treinamento.

Para visual_observations, registre apenas sinais realmente visíveis no intervalo: painel de headline incorporado, post social/fake tweet, montagem/arte composta, split-screen, evidência externa ou palco. Não use o texto da transcrição como prova visual. Quando houver dúvida, use visual_format=desconhecido e confidence baixa. Composição com post, reação, entrevistado ou palco deve ser preservada; não recomende crop centrado em uma única face nesses casos."""

    @staticmethod
    def _extract_text(payload: dict) -> str:
        for candidate in payload.get("candidates", []):
            parts = candidate.get("content", {}).get("parts", [])
            for part in parts:
                if part.get("text") and not part.get("thought"):
                    return part["text"].strip()
        return ""

    @staticmethod
    def _strip_fence(text: str) -> str:
        value = text.strip()
        if value.startswith("```"):
            value = value.split("\n", 1)[1] if "\n" in value else value[3:]
            if value.rstrip().endswith("```"):
                value = value.rstrip()[:-3]
        return value.strip()

    @staticmethod
    def _error_text(response) -> str:
        try:
            return str(response.json().get("error", {}).get("message", "erro desconhecido"))[:240]
        except Exception:
            return response.text[:240]


def analyze_video_with_gemini(
    video_path: str,
    api_key: str,
    editorial_context=None,
    user_context="",
    emit_progress=None,
    cancel_check=None,
    model: str = "gemini-2.5-flash",
) -> dict:
    analyzer = GeminiVideoAnalyzer(api_key, model=model)
    return analyzer.analyze(video_path, editorial_context, user_context, emit_progress, cancel_check)
