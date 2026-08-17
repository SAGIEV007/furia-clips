# Furia Clips

**Corte. Ranqueie. Domine.**

> **Versão atual: 2.6.** Esta release adiciona a primeira ponte funcional Campaign Hub→seeds→expansão→gates→propostas guiadas, mantendo a revisão humana obrigatória e o benchmark local. A integração completa de alinhamento com mídia baixada, renderização aprovada e ganho reproduzível de recall ainda está em evolução. A identidade de runtime é exibida no console, na interface e na API; a fonte única da versão é [`VERSION`](VERSION).

## Continuidade para novas sessões e IAs

Se você entregar apenas o link deste repositório a outra IA, ela deve começar por [`docs/continuity/START_HERE.md`](docs/continuity/START_HERE.md), [`docs/continuity/PROMPT_EXECUCAO_CHUB_CORTES.md`](docs/continuity/PROMPT_EXECUCAO_CHUB_CORTES.md), [`docs/continuity/PROMPT_MESTRE_IA.md`](docs/continuity/PROMPT_MESTRE_IA.md), [`docs/continuity/CHUB_INTEGRATION_CONTRACT.md`](docs/continuity/CHUB_INTEGRATION_CONTRACT.md) e depois ler [`AGENTS.md`](AGENTS.md), [`PROJECT_STATE.md`](docs/continuity/PROJECT_STATE.md), [`DECISIONS.md`](docs/continuity/DECISIONS.md), [`NEXT_CYCLE.md`](docs/continuity/NEXT_CYCLE.md) e o pacote [`docs/continuity/`](docs/continuity/). O prompt de execução Chub→cortes é o roteiro copiável para implementar a próxima hipótese; o prompt mestre consolida os prompts históricos e as regras de execução; o contrato Chub→cortes define o objetivo funcional; o START_HERE continua sendo a entrada operacional canônica. O padrão obrigatório de commits está em [`COMMIT_MESSAGE_TEMPLATE.md`](docs/continuity/COMMIT_MESSAGE_TEMPLATE.md), e o contrato de releases está em [`docs/VERSIONING.md`](docs/VERSIONING.md).

O arquivo [`docs/continuity/PROJECT_STATE.md`](docs/continuity/PROJECT_STATE.md) é atualizado ao final de cada rodada verificável. Ele não substitui o código nem o Git: a nova IA deve sempre confirmar `git status`, branch, commit e testes no checkout real.

O Furia Clips é uma ferramenta local em evolução para analisar vídeos longos e encontrar cortes precisos do Renan Santos/MBL. A release 2.6 possui a primeira ponte funcional que transforma seeds autorizadas do Campaign Hub em propostas guiadas, expandidas por contexto e marcadas com gates de proveniência e revisão. O alinhamento completo com cada mídia local, a persistência de propostas no benchmark e o ganho reproduzível de recall ainda são a próxima etapa. O processamento ocorre no computador do usuário; serviços de IA são opcionais e possuem fallback local/NLP quando não estão disponíveis.

## O que está implementado

- **Pipeline executável em evolução:** upload, transcrição, seleção, ranking, corte, legendas, validação e persistência existem no código e devem ser validados em mídia real antes de serem considerados confiáveis.
- **Timeline canônica:** todos os estágios usam a mesma linha do tempo do vídeo original, inclusive depois da análise de silêncio.
- **Seleção editorial explicável:** cada clip pode exibir score, confiança, fatores de hook, fluxo, valor, contexto, energia, clareza, completude e diversidade.
- **Perfil editorial Renan Santos/MBL:** classifica o subtipo político quando aplicável e também reconhece as famílias `politico`, `humor`, `reacao`, `bastidor`, `descontraido` e `conversa`, sem forçar todo momento a parecer político.
- **Portfólio diário global:** compete candidatos de várias lives, aplica gates de contexto/conclusão/clareza, deduplica semanticamente, limita concentração por live e só trata 39–50 como faixa operacional quando houver material suficiente.
- **Contexto e ritmo audiovisual:** o ranking penaliza aberturas com pronomes sem antecedente, aceita densidade de mudanças de cena quando fornecida pelo pipeline e mantém energia de áudio como sinal explicável.
- **Destinos de exportação:** presets para Shorts, Reels, TikTok, quadrado e paisagem, com resolução, proporção e área segura coerentes.
- **Legendas:** geração ASS/SRT com karaoke por palavra, escaping seguro, timestamps protegidos contra valores inválidos e destaque vermelho opcional para termos políticos/números de impacto.
- **Jobs persistidos:** progresso, erro, resultado, cancelamento cooperativo e recuperação após reconexão por `job_id`.
- **Revisão humana:** aprovar, rejeitar, anotar e ajustar clips sem perder o histórico.
- **Lotes locais:** descoberta segura de vídeos, hash de conteúdo, deduplicação, manifesto reproduzível e endpoint `/api/batch/rank` para seleção global de candidatos entre lives.
- **Segurança local:** proteção contra path traversal, nomes inseguros, symlinks externos e exposição acidental do servidor na rede.
- **Validação de mídia:** exports só são considerados prontos depois de uma verificação objetiva com `ffprobe`.
- **Memória local do Campaign Hub:** exports autorizados podem ser instalados ou mesclados fora do checkout; o job normal continua offline-first, usando a última memória válida sem consultar o MCP a cada corte.
- **Pré-análise por blocos:** a interface lista blocos filtrados pela fonte, mostra resumo, pergunta, locutor provável, destaques e riscos, e permite selecionar/exportar um intervalo local; essa tela ainda é superfície de diagnóstico e revisão.
- **Timeline de bloco:** quando um MP4 baixado corresponde ao intervalo de uma fonte longa, timestamps absolutos são mapeados para a linha local com confirmação e registro do método.
- **Benchmark editorial local:** compara candidatos do Furia com highlights autorizados do Campaign Hub, mede recall, IoU e erro de fronteira e salva o resultado fora do Git; a comparação não aprova cortes nem consulta o Chub durante o job.
- **Highlights individuais:** o painel de Blocos pode exportar um highlight específico no aspecto original quando o MP4 correspondente já está disponível.
- **Ponte Chub→cortes:** `modules/campaign_hub_guidance.py` normaliza blocos/highlights reais em seeds auditáveis; `ClipSelector` expande seeds para propostas guiadas com contexto, payoff, locutor, timing, risco e gates de proveniência, sem autoaprovação; ver [`docs/continuity/CHUB_INTEGRATION_CONTRACT.md`](docs/continuity/CHUB_INTEGRATION_CONTRACT.md).

## Instalação no Windows

O caminho recomendado é simplesmente executar o launcher automático:

```text
run.bat
```

O launcher faz o bootstrap do computador: procura Python, instala Python 3.12 automaticamente quando necessário, prepara FFmpeg e `ffprobe`, cria o ambiente virtual, instala as dependências, prepara o modelo Whisper e inicia o servidor local. Em Windows 10/11, ele usa WinGet quando disponível; se WinGet não estiver disponível, tenta o instalador oficial do Python e um build público de FFmpeg referenciado pelo projeto FFmpeg.

Na primeira execução é necessário ter conexão com a internet e permitir eventuais avisos de instalação do Windows. Depois que os runtimes e dependências estiverem em `.runtime` e `venv`, as execuções seguintes reutilizam o que já foi instalado. **Não é necessário instalar Python, FFmpeg, Ollama ou Gemini manualmente para começar.** Ollama e Gemini são otimizações opcionais; sem eles o ranking NLP local continua funcionando.

O launcher grava diagnóstico detalhado em `logs\\bootstrap-latest.log` e `logs\\run-latest.log`. Depois de iniciar o Flask, ele aguarda `http://127.0.0.1:3001` responder e abre uma nova aba no Opera GX quando encontrado, com fallback ao navegador padrão. Se algo falhar, os últimos eventos são exibidos automaticamente no console; envie esses dois arquivos junto com a mensagem de erro para permitir uma investigação objetiva.

Se preferir executar manualmente:

```powershell
py -3 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Acesse [http://127.0.0.1:3001](http://127.0.0.1:3001). Se o bootstrap não puder concluir por falta de internet, política corporativa ou bloqueio do instalador, execute `run.bat` novamente após corrigir a conectividade.

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

O projeto usa **FFmpeg e ffprobe** para cortar e validar mídia. No Windows, `run.bat` prepara esses executáveis automaticamente. No Linux/macOS, eles precisam estar instalados no `PATH`. O Whisper usa `faster-whisper` e pode funcionar em CPU; uma GPU NVIDIA é opcional. Em Linux, também pode ser necessário instalar bibliotecas do sistema exigidas pelo OpenCV/MediaPipe conforme a distribuição.

## Backends de IA

O padrão é **Automático**, que tenta Gemini somente se uma chave já estiver configurada, depois verifica Ollama e finalmente usa o ranking NLP local. Portanto, o programa inicia, seleciona cortes e renderiza sem qualquer chave de API.


| Backend | Custo | Comportamento | Requisito |
| --- | --- | --- | --- |
| Automático | Gratuito no caminho local | Gemini → Ollama → NLP local | Nenhum requisito obrigatório |
| Ollama | Local | Seleção contextual offline, se o serviço estiver disponível | Ollama e um modelo, ambos opcionais |
| Google Gemini | Conforme a conta/API | Seleção contextual online mais avançada | Chave opcional na interface ou no ambiente |
| Claude API | Conforme a conta/API | Geração de conteúdo | Chave opcional da Anthropic |
| NLP local | Gratuito | Fallback determinístico de seleção | Nenhum serviço externo |

Uma chave Gemini melhora a seleção contextual e habilita a análise multimodal online do vídeo quando a API está acessível, mas não é necessária para usar o programa. Se você informar uma chave, o modo automático passa a considerá-la; o fluxo tenta analisar o vídeo com áudio e imagem antes da seleção e reaproveita os segmentos retornados, com fallback para Whisper/Ollama/NLP em caso de falha. A análise multimodal pode exigir upload do arquivo e ter latência/cota. Nunca coloque chaves de API em commits.

## Fontes de análise

A biblioteca mantém o upload local existente e agora oferece uma central de fontes com três caminhos compatíveis. O upload continua sendo a opção mais previsível para renderização. A transcrição manual aceita texto Tactiq com timestamps, além de `.srt` e `.vtt`; quando a fonte é válida, o pipeline pula o Whisper e preserva a timeline original. O link público aceita URLs `http(s)`, faz uma prévia e pode baixar a mídia automaticamente via yt-dlp para o workspace, sem cookies, login, bypass de DRM ou acesso a conteúdo privado. YouTube público é a primeira fonte recomendada; outras plataformas dependem do extrator disponível.

Antes do ranking, o sistema gera uma pré-análise determinística com perguntas, possíveis respostas, referências ao Renan, janelas de entrevista, sobreposição temporal e confiança. Quando Gemini está configurado, essa pré-análise é enriquecida por áudio e imagem. A identidade do falante é tratada como hipótese revisável, não como reconhecimento perfeito.

## Perfil editorial político

O perfil `renan_santos_politics` vem selecionado por padrão e foi desenhado para encontrar cortes políticos autossuficientes, com contexto suficiente para o espectador entender a tese, o conflito e a consequência. Ele não tenta decidir a verdade de uma afirmação: usa sinais da transcrição para priorizar estrutura editorial, especificidade e evidência, deixando a aprovação final com o editor.

Na interface, selecione **Perfil editorial → Renan Santos / MBL** e, quando necessário, use os chips de contexto para orientar a busca, como **confronto/reação**, **proposta/programa**, **dado/denúncia**, **crítica jurídica**, **segurança pública**, **corrupção**, **impostos** e **mobilização**. Os chips funcionam como contexto de seleção; eles não inventam falas, números ou fatos que não estejam presentes no vídeo.

Os cortes políticos continuam classificados em cinco subtipos: **confronto/reação**, para respostas e embates com alvo identificável; **proposta/programa**, para soluções e compromissos; **dado/denúncia**, para exposição sustentada por número, documento ou acusação contextualizada; **discurso/posicionamento**, para teses políticas completas; e **mobilização**, para chamadas à ação e construção de comunidade. Antes disso, o sistema escolhe uma família editorial dominante: **político, humor, reação, bastidor, descontraído ou conversa**. A classificação e os sinais usados aparecem na revisão humana para facilitar a decisão de aprovar ou rejeitar.

Para uma saída vertical dedicada, escolha **Política Editorial — 9:16** no campo **Preset de Plataforma**. Esse preset mantém 1080×1920, limita a duração a 180 segundos e desloca as legendas para uma área segura maior, adequada às sobreposições comuns de Shorts, Reels e TikTok. Os presets `shorts`, `reels` e `tiktok` continuam disponíveis para publicação específica por plataforma.

A documentação detalhada, incluindo fatores, limites e exemplos de uso editorial, está em [`docs/editorial-profile.md`](docs/editorial-profile.md). A pesquisa audiovisual pública e a matriz de padrões estão em [`docs/video-analysis/editorial-patterns.md`](docs/video-analysis/editorial-patterns.md); ela registra o que foi observado diretamente e o que permanece hipótese.

## Testes

Com o ambiente virtual ativo, instale `pytest` se necessário e execute:

```bash
python -m pip install pytest
python -m pytest -q
```

A suíte cobre timeline, segurança, jobs, banco e migrações, ranking editorial, portfólio diário global, seleção, perfil político, presets, legendas, renderização FFmpeg, descoberta em lote e smoke tests HTTP. A fixture audiovisual determinística está em `tests/fixtures/sample_av.mp4`.

## Estrutura relevante

```text
app.py                     servidor Flask e endpoints
config.py                  defaults e configuração do ambiente
database.py                SQLite, migrações e feedback
modules/timeline.py        timeline canônica
modules/job_manager.py     jobs persistidos e cancelamento
modules/editorial_ranker.py ranking explicável, família editorial e diversidade entre lives
modules/political_profile.py taxonomia, scoring político e completude de contexto
modules/daily_portfolio.py seleção global 39–50 com gates e limites por fonte
modules/video_cutter.py    corte e exportação por preset
modules/subtitle_generator.py legendas ASS/SRT e áreas seguras por preset
modules/media_validation.py validação objetiva com ffprobe
modules/batch_queue.py     descoberta e deduplicação de lotes
modules/transcript_parser.py parser Tactiq/SRT/VTT e timeline manual
modules/editorial_context.py pré-análise de entrevista, perguntas e sinais
modules/source_ingest.py      validação e download de fontes públicas
modules/gemini_video.py       upload e análise multimodal online
modules/native_dialogs.py     exploradores nativos locais
static/js/app.js           estado, fontes, progresso e revisão no frontend
templates/index.html       interface principal
tests/                     regressões e smoke tests
docs/                      arquitetura, roadmap e relatórios, incluindo pesquisa audiovisual
```

## Status da reconstrução

A branch `manus/rebuild-opus-parity` contém a reconstrução incremental comparada à branch base `devin/1782248654-furia-clips`. A implementação base foi validada localmente com 52 casos; esta evolução acrescenta cobertura de parser, fontes públicas, diálogo local e contexto de entrevista, totalizando 63 testes aprovados na última execução. A validação cobre o perfil editorial político, famílias de humor/reação, contexto de abertura, energia de áudio por janela, portfólio global entre lives, bootstrap automático, fallback sem chave, smoke tests HTTP e renderização real com FFmpeg.
O relatório detalhado está em [`docs/rebuild-report.md`](docs/rebuild-report.md), o perfil editorial está em [`docs/editorial-profile.md`](docs/editorial-profile.md) e os critérios de qualidade estão em [`docs/quality-gates.md`](docs/quality-gates.md).

Esta versão aproxima o produto de um fluxo profissional de clipping, mas não afirma paridade total com plataformas comerciais. Ainda são evoluções futuras o editor visual de timeline com handles, reenquadramento temporal contínuo de rostos/objetos, rerender parcial e calibração estatística do ranking usando um histórico amplo de feedback.

## Segurança e dados locais

O Furia Clips é uma aplicação local. Os arquivos enviados, bancos SQLite, transcrições, artefatos de workspace e exports devem permanecer fora do controle de versão, conforme o `.gitignore`. Antes de abrir a aplicação para uma rede, revise o host, CORS, permissões do diretório de trabalho e as chaves configuradas.
