# Furia Clips

**Corte. Ranqueie. Domine.**

Ferramenta local completa para converter videos longos em shorts virais. Roda 100% no seu PC via navegador, sem depender de creditos ou servicos pagos.

## Funcionalidades

- **Remover Silencio** - Detecta e remove pausas automaticamente com FFmpeg
- **Gerar Legendas** - Transcreve com Whisper e adiciona legendas estilo CapCut (karaoke palavra por palavra)
- **Cortar Shorts** - Cortes inteligentes por fala/cena com ranqueamento viral (score 0-100)
- **Face Tracking** - Centraliza o rosto do palestrante ao converter para 9:16
- **Gerar Conteudo SEO** - Titulos, tags, descricao e hashtags via IA
- **Gerar Thumbnail** - Capas com identidade visual do canal
- **Processo Completo** - Pipeline completo com um clique

## Como Usar

### Windows
Duplo clique no arquivo `run.bat`

### Linux/Mac
```bash
chmod +x run.sh
./run.sh
```

Acesse `http://localhost:3001` no navegador.

## Requisitos

- Python 3.10+
- FFmpeg instalado e no PATH
- 8GB+ de RAM (recomendado 16GB)
- GPU NVIDIA opcional (acelera Whisper e Ollama)

## Backend de IA

A ferramenta suporta 3 backends para geracao de conteudo:

| Backend | Custo | Qualidade | Requisito |
|---------|-------|-----------|-----------|
| **Ollama** (padrao) | Gratis | Boa | Ollama instalado localmente |
| **Google Gemini** | Gratis (tier free) | Muito boa | API key do Google |
| **Claude API** | Pago | Excelente | API key da Anthropic |

## Stack

- Python + Flask + WebSocket
- FFmpeg (corte e exportacao)
- OpenAI Whisper (transcricao local)
- MediaPipe (face tracking)
- Pillow (thumbnails)
- SQLite (configuracoes e historico)
- HTML/CSS/JS (interface)
