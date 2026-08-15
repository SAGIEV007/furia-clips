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
        mime_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
        if emit_progress:
            emit_progress("[Gemini] Enviando o vídeo para análise multimodal online...", "info")
        file_info = self._upload_file(path, mime_type, emit_progress, cancel_check)
        self._wait_until_active(file_info.get("name", ""), emit_progress, cancel_check)

        prompt = self._build_prompt(editorial_context or {}, user_context)
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
        response = self._generate_content(request_payload, emit_progress, cancel_check)
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

    def _generate_content(self, request_payload: dict, emit_progress=None, cancel_check=None):
        """Retry only transient API failures; the video upload is not repeated."""
        endpoint = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        retryable = {408, 429, 500, 502, 503, 504}
        max_attempts = 3
        last_response = None
        for attempt in range(1, max_attempts + 1):
            if cancel_check:
                cancel_check()
            response = self.session.post(endpoint, json=request_payload, timeout=600)
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

    def _upload_file(self, path: Path, mime_type: str, emit_progress=None, cancel_check=None) -> dict:
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
                timeout=1800,
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
            result = self.session.get(f"{self.base_url}/v1beta/{file_name}", timeout=60)
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
        return f"""Você é um analista audiovisual e {role}.
Analise o vídeo inteiro usando áudio e imagem, sem inventar fatos externos. O objetivo é preparar uma etapa posterior de corte, não escrever legendas.

Identidade esperada da fonte e do foco editorial:
{json.dumps({'source_file_name': editorial_context.get('source_file_name', ''), 'expected_focus': editorial_context.get('focus', 'generic_political')}, ensure_ascii=False)}

Contexto determinístico já extraído da transcrição:
{json.dumps(editorial_context, ensure_ascii=False)[:12000]}

Instrução opcional do editor:
{user_context or default_instruction}

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
