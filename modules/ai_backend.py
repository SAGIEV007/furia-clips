import json
import requests
import os


class AIBackend:
    def __init__(self, backend="ollama", settings=None):
        self.backend = str(backend or "ollama").strip().lower()
        self.settings = settings or {}
        self.last_provider = ""
        self.last_error = ""

    def generate(self, prompt, system_prompt="", emit_progress=None):
        """Generate text with an explicit, observable provider fallback chain.

        In ``auto`` mode, a configured Gemini key is tried first, followed by
        Ollama and then the deterministic local fallback. Provider failures are
        non-fatal and remain available through ``last_provider`` and
        ``last_error`` so the UI can explain what happened.
        """
        self.last_provider = ""
        self.last_error = ""
        if self.backend == "auto":
            gemini_key = str(self.settings.get("gemini_api_key", "") or "").strip()
            if gemini_key:
                response = self._generate_gemini(prompt, system_prompt, emit_progress)
                if response:
                    return response
            response = self._generate_ollama(prompt, system_prompt, emit_progress)
            if response:
                return response
            return self._generate_fallback(prompt)
        if self.backend == "ollama":
            return self._generate_ollama(prompt, system_prompt, emit_progress)
        if self.backend == "claude":
            return self._generate_claude(prompt, system_prompt, emit_progress)
        if self.backend == "gemini":
            return self._generate_gemini(prompt, system_prompt, emit_progress)
        return self._generate_fallback(prompt)

    def _generate_ollama(self, prompt, system_prompt, emit_progress=None):
        url = self.settings.get("ollama_url", "http://localhost:11434")
        model = self.settings.get("ollama_model", "llama3.2:3b")

        if emit_progress:
            emit_progress(f"Gerando com Ollama ({model})...")

        try:
            response = requests.post(
                f"{url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 2000},
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            self.last_provider = "ollama"
            return data.get("response", "")
        except requests.exceptions.ConnectionError as exc:
            self.last_error = f"Ollama indisponível: {exc}"
            if emit_progress:
                emit_progress("Ollama nao esta rodando. Usando o próximo provedor disponível.")
            return self._generate_fallback(prompt)
        except Exception as e:
            self.last_error = f"Erro Ollama: {e}"
            if emit_progress:
                emit_progress(f"Erro Ollama: {str(e)}")
            return self._generate_fallback(prompt)

    def _generate_claude(self, prompt, system_prompt, emit_progress=None):
        api_key = self.settings.get("claude_api_key", "")
        if not api_key:
            if emit_progress:
                emit_progress("Claude API key nao configurada. Usando fallback.")
            return self._generate_fallback(prompt)

        if emit_progress:
            emit_progress("Gerando com Claude API...")

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            self.last_provider = "claude"
            return message.content[0].text
        except Exception as e:
            self.last_error = f"Erro Claude: {e}"
            if emit_progress:
                emit_progress(f"Erro Claude: {str(e)}")
            return self._generate_fallback(prompt)

    def _generate_gemini(self, prompt, system_prompt, emit_progress=None):
        api_key = self.settings.get("gemini_api_key", "")
        if not api_key:
            if emit_progress:
                emit_progress("Gemini API key nao configurada. Usando fallback.")
            return self._generate_fallback(prompt)

        if emit_progress:
            emit_progress("Gerando com Google Gemini...")

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = model.generate_content(full_prompt)
            self.last_provider = "gemini"
            return response.text
        except Exception as e:
            self.last_error = f"Erro Gemini: {e}"
            if emit_progress:
                emit_progress(f"Erro Gemini: {str(e)}")
            return self._generate_fallback(prompt)

    def _generate_fallback(self, prompt):
        self.last_provider = self.last_provider or "local"
        return ""

    def generate_seo_content(self, transcript, channel_context="", emit_progress=None):
        system_prompt = f"""Voce e um especialista em SEO para YouTube, TikTok e Instagram.
Contexto do canal: {channel_context}
Responda SEMPRE em portugues brasileiro.
Formate sua resposta EXATAMENTE como JSON valido."""

        prompt = f"""Analise este trecho de video e gere conteudo SEO otimizado.

TRANSCRICAO:
{transcript[:2000]}

Gere um JSON com esta estrutura exata:
{{
  "titles": ["titulo1", "titulo2", "titulo3", "titulo4", "titulo5"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11", "tag12", "tag13", "tag14", "tag15"],
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5", "#hashtag6", "#hashtag7", "#hashtag8", "#hashtag9", "#hashtag10"],
  "description": "descricao completa otimizada para SEO com call to action",
  "pinned_comment": "sugestao de comentario fixado para engajamento",
  "thumbnail_text": "texto curto e impactante para thumbnail"
}}

Retorne APENAS o JSON, sem texto adicional."""

        response = self.generate(prompt, system_prompt, emit_progress)

        try:
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            return json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            return self._generate_basic_seo(transcript)

    def _generate_basic_seo(self, transcript):
        words = transcript.split()[:10]
        base_title = " ".join(words).strip(".,!?")

        return {
            "titles": [
                f"{base_title} - CORTE VIRAL",
                f"VOCE PRECISA VER ISSO: {base_title}",
                f"{base_title} | Furia da Nacao",
                f"CHOCANTE: {base_title}",
                f"{base_title} #shorts",
            ],
            "tags": [
                "politica", "brasil", "renan santos", "mbl",
                "corte podcast", "shorts", "viral", "direita",
                "conservador", "liberdade", "furia da nacao",
                "politica brasileira", "cortes", "debate", "opiniao",
            ],
            "hashtags": [
                "#politica", "#brasil", "#shorts", "#viral",
                "#renansantos", "#mbl", "#direita", "#conservador",
                "#furiadanacao", "#cortespolitica",
            ],
            "description": f"{base_title}\n\nInscreva-se no canal e ative o sininho!\n\n#politica #brasil #shorts",
            "pinned_comment": "Concorda? Deixe sua opiniao nos comentarios! 👇",
            "thumbnail_text": base_title[:30].upper(),
        }
