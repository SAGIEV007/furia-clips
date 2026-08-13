# Furia Clips

**Corte. Ranqueie. Domine.**

O Furia Clips é uma ferramenta local para transformar vídeos longos em clipes verticais para Shorts, Reels e TikTok. O pipeline combina transcrição, seleção editorial explicável, renderização por plataforma, legendas, persistência de jobs, revisão humana e processamento em lote. O processamento ocorre no computador do usuário; serviços de IA são opcionais e possuem fallback local/NLP quando não estão disponíveis.

## O que está implementado

- **Pipeline completo:** upload, transcrição, seleção, ranking, corte, legendas, validação e persistência do resultado.
- **Timeline canônica:** todos os estágios usam a mesma linha do tempo do vídeo original, inclusive depois da análise de silêncio.
- **Seleção editorial explicável:** cada clip pode exibir score, confiança, fatores de hook, fluxo, valor, contexto, energia, clareza, completude e diversidade.
- **Perfil político Renan Santos/MBL:** modo especializado que classifica confronto/reação, proposta/programa, dado/denúncia, discurso/posicionamento e mobilização, priorizando tese, contexto, evidência e conclusão.
- **Contexto e ritmo audiovisual:** o ranking penaliza aberturas com pronomes sem antecedente, aceita densidade de mudanças de cena quando fornecida pelo pipeline e mantém energia de áudio como sinal explicável.
- **Destinos de exportação:** presets para Shorts, Reels, TikTok, quadrado e paisagem, com resolução, proporção e área segura coerentes.
- **Legendas:** geração ASS/SRT com karaoke por palavra, escaping seguro, timestamps protegidos contra valores inválidos e destaque vermelho opcional para termos políticos/números de impacto.
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

## Perfil editorial político

O perfil `renan_santos_politics` vem selecionado por padrão e foi desenhado para encontrar cortes políticos autossuficientes, com contexto suficiente para o espectador entender a tese, o conflito e a consequência. Ele não tenta decidir a verdade de uma afirmação: usa sinais da transcrição para priorizar estrutura editorial, especificidade e evidência, deixando a aprovação final com o editor.

Na interface, selecione **Perfil editorial → Renan Santos / MBL** e, quando necessário, use os chips de contexto para orientar a busca, como **confronto/reação**, **proposta/programa**, **dado/denúncia**, **crítica jurídica**, **segurança pública**, **corrupção**, **impostos** e **mobilização**. Os chips funcionam como contexto de seleção; eles não inventam falas, números ou fatos que não estejam presentes no vídeo.

Os cortes são classificados em cinco formatos editoriais: **confronto/reação**, para respostas e embates com alvo identificável; **proposta/programa**, para soluções e compromissos; **dado/denúncia**, para exposição sustentada por número, documento ou acusação contextualizada; **discurso/posicionamento**, para teses políticas completas; e **mobilização**, para chamadas à ação e construção de comunidade. A classificação e os sinais usados aparecem na revisão humana para facilitar a decisão de aprovar ou rejeitar.

Para uma saída vertical dedicada, escolha **Política Editorial — 9:16** no campo **Preset de Plataforma**. Esse preset mantém 1080×1920, limita a duração a 180 segundos e desloca as legendas para uma área segura maior, adequada às sobreposições comuns de Shorts, Reels e TikTok. Os presets `shorts`, `reels` e `tiktok` continuam disponíveis para publicação específica por plataforma.

A documentação detalhada, incluindo fatores, limites e exemplos de uso editorial, está em [`docs/editorial-profile.md`](docs/editorial-profile.md). A pesquisa audiovisual pública e a matriz de padrões estão em [`docs/video-analysis/editorial-patterns.md`](docs/video-analysis/editorial-patterns.md); ela registra o que foi observado diretamente e o que permanece hipótese.

## Testes

Com o ambiente virtual ativo, instale `pytest` se necessário e execute:

```bash
python -m pip install pytest
python -m pytest -q
```

A suíte cobre timeline, segurança, jobs, banco e migrações, ranking editorial, seleção, perfil político, presets, legendas, renderização FFmpeg, descoberta em lote e smoke tests HTTP. A fixture audiovisual determinística está em `tests/fixtures/sample_av.mp4`.

## Estrutura relevante

```text
app.py                     servidor Flask e endpoints
config.py                  defaults e configuração do ambiente
database.py                SQLite, migrações e feedback
modules/timeline.py        timeline canônica
modules/job_manager.py     jobs persistidos e cancelamento
modules/editorial_ranker.py ranking explicável e sinais políticos
modules/political_profile.py taxonomia, scoring político e completude de contexto
modules/video_cutter.py    corte e exportação por preset
modules/subtitle_generator.py legendas ASS/SRT e áreas seguras por preset
modules/media_validation.py validação objetiva com ffprobe
modules/batch_queue.py     descoberta e deduplicação de lotes
static/js/app.js           estado, progresso e revisão no frontend
templates/index.html       interface principal
tests/                     regressões e smoke tests
docs/                      arquitetura, roadmap e relatórios, incluindo pesquisa audiovisual
```

## Status da reconstrução

A branch `manus/rebuild-opus-parity` contém a reconstrução incremental comparada à branch base `devin/1782248654-furia-clips`. A implementação foi validada localmente com uma suíte de 40 casos, incluindo o perfil editorial político, contexto de abertura, energia de áudio por janela, ritmo visual, smoke tests HTTP e renderização real com FFmpeg. O relatório detalhado está em [`docs/rebuild-report.md`](docs/rebuild-report.md), o perfil editorial está em [`docs/editorial-profile.md`](docs/editorial-profile.md) e os critérios de qualidade estão em [`docs/quality-gates.md`](docs/quality-gates.md).

Esta versão aproxima o produto de um fluxo profissional de clipping, mas não afirma paridade total com plataformas comerciais. Ainda são evoluções futuras o editor visual de timeline com handles, reenquadramento temporal contínuo de rostos/objetos, rerender parcial e calibração estatística do ranking usando um histórico amplo de feedback.

## Segurança e dados locais

O Furia Clips é uma aplicação local. Os arquivos enviados, bancos SQLite, transcrições, artefatos de workspace e exports devem permanecer fora do controle de versão, conforme o `.gitignore`. Antes de abrir a aplicação para uma rede, revise o host, CORS, permissões do diretório de trabalho e as chaves configuradas.
