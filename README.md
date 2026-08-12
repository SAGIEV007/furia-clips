# Furia Clips

**Corte. Ranqueie. Domine.**

O Furia Clips é uma ferramenta local para transformar vídeos longos em clipes verticais para Shorts, Reels e TikTok. O pipeline combina transcrição, seleção editorial explicável, renderização por plataforma, legendas, persistência de jobs, revisão humana e processamento em lote. O processamento ocorre no computador do usuário; serviços de IA são opcionais e possuem fallback local/NLP quando não estão disponíveis.

## O que está implementado

- **Pipeline completo:** upload, transcrição, seleção, ranking, corte, legendas, validação e persistência do resultado.
- **Timeline canônica:** todos os estágios usam a mesma linha do tempo do vídeo original, inclusive depois da análise de silêncio.
- **Seleção editorial explicável:** cada clip pode exibir score, confiança, fatores de hook, fluxo, valor, contexto, energia, clareza, completude e diversidade.
- **Destinos de exportação:** presets para Shorts, Reels, TikTok, quadrado e paisagem, com resolução, proporção e área segura coerentes.
- **Legendas:** geração ASS/SRT com karaoke por palavra, escaping seguro e timestamps protegidos contra valores inválidos.
- **Jobs persistidos:** progresso, erro, resultado, cancelamento cooperativo e recuperação após reconexão por `job_id`.
- **Revisão humana:** aprovar, rejeitar, anotar e ajustar clips sem perder o histórico.
- **Lotes locais:** descoberta segura de vídeos, hash de conteúdo, deduplicação e manifesto reproduzível.
- **Segurança local:** proteção contra path traversal, nomes inseguros, symlinks externos e exposição acidental do servidor na rede.
- **Validação de mídia:** exports só são considerados prontos depois de uma verificação objetiva com `ffprobe`.

## Instalação no Windows

O caminho recomendado é usar o launcher versionado:

```text
run.bat
```

O launcher cria ou reutiliza o ambiente virtual, instala as dependências e inicia o servidor local. É necessário ter **Python 3.10 ou superior** e **FFmpeg** instalados e disponíveis no `PATH`.

Se preferir executar manualmente:

```powershell
py -3 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Acesse [http://127.0.0.1:3001](http://127.0.0.1:3001).

## Instalação no Linux ou macOS

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Acesse [http://127.0.0.1:3001](http://127.0.0.1:3001). O servidor fica limitado ao loopback por padrão. Para expor deliberadamente a aplicação na rede local, configure `FURIA_HOST` conscientemente antes de iniciar.

## Dependências do sistema

O projeto requer **FFmpeg e ffprobe** no `PATH`. O Whisper usa `faster-whisper` e pode funcionar em CPU; uma GPU NVIDIA é opcional. Em Linux, também pode ser necessário instalar bibliotecas do sistema exigidas pelo OpenCV/MediaPipe conforme a distribuição.

## Backends de IA

A aplicação pode trabalhar em três níveis, conforme a configuração disponível:

| Backend | Custo | Uso | Requisito |
| --- | --- | --- | --- |
| Ollama | Local | Seleção e conteúdo com fallback local | Ollama instalado e um modelo disponível |
| Google Gemini | Conforme a conta/API | Seleção contextual e geração de conteúdo | Chave configurada na interface ou no ambiente |
| Claude API | Conforme a conta/API | Geração de conteúdo | Chave da Anthropic |
| NLP local | Gratuito | Fallback determinístico | Nenhum serviço externo |

Nunca coloque chaves de API em commits. Use a interface local, variáveis de ambiente ou a persistência protegida prevista pelo aplicativo.

## Testes

Com o ambiente virtual ativo, instale `pytest` se necessário e execute:

```bash
python -m pip install pytest
python -m pytest -q
```

A suíte cobre timeline, segurança, jobs, banco e migrações, ranking editorial, seleção, presets, legendas, renderização FFmpeg, descoberta em lote e smoke tests HTTP. A fixture audiovisual determinística está em `tests/fixtures/sample_av.mp4`.

## Estrutura relevante

```text
app.py                     servidor Flask e endpoints
config.py                  defaults e configuração do ambiente
database.py                SQLite, migrações e feedback
modules/timeline.py        timeline canônica
modules/job_manager.py     jobs persistidos e cancelamento
modules/editorial_ranker.py ranking explicável
modules/video_cutter.py    corte e exportação por preset
modules/subtitle_generator.py legendas ASS/SRT
modules/media_validation.py validação objetiva com ffprobe
modules/batch_queue.py     descoberta e deduplicação de lotes
static/js/app.js           estado, progresso e revisão no frontend
templates/index.html       interface principal
tests/                     regressões e smoke tests
docs/                      arquitetura, roadmap e relatórios
```

## Status da reconstrução

A branch `manus/rebuild-opus-parity` contém a reconstrução incremental comparada à branch base `devin/1782248654-furia-clips`. A implementação foi validada localmente com uma suíte de 32 casos, incluindo smoke tests HTTP e renderização real com FFmpeg. O relatório detalhado está em [`docs/rebuild-report.md`](docs/rebuild-report.md), e os critérios de qualidade estão em [`docs/quality-gates.md`](docs/quality-gates.md).

Esta versão aproxima o produto de um fluxo profissional de clipping, mas não afirma paridade total com plataformas comerciais. Ainda são evoluções futuras o editor visual de timeline com handles, reenquadramento temporal contínuo de rostos/objetos, rerender parcial e calibração estatística do ranking usando um histórico amplo de feedback.

## Segurança e dados locais

O Furia Clips é uma aplicação local. Os arquivos enviados, bancos SQLite, transcrições, artefatos de workspace e exports devem permanecer fora do controle de versão, conforme o `.gitignore`. Antes de abrir a aplicação para uma rede, revise o host, CORS, permissões do diretório de trabalho e as chaves configuradas.
