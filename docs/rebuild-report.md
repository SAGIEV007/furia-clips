# Relatório de reconstrução do Furia Clips

**Autor:** Manus AI  
**Branch local:** `manus/rebuild-opus-parity`  
**Commits locais:** `893204e` e `6d11d34`  
**Data:** 12 de agosto de 2026

## Síntese executiva

O Furia Clips foi reconstruído de forma incremental para se aproximar, em experiência e confiabilidade, de uma plataforma profissional de clipping automatizado. O benchmark foi baseado nas capacidades públicas do OpusClip — descoberta por prompt, análise multimodal, score de potencial, reenquadramento, legendas, revisão e automação — sem copiar código proprietário [1] [2] [5].

A intervenção priorizou os problemas que impediam o produto de cumprir sua promessa: desalinhamento de timeline após remoção de silêncio, score pouco explicável, ausência de validação objetiva dos exports, estado global frágil para jobs, exposição insegura de caminhos locais e falta de uma etapa de revisão humana persistente.

O resultado é uma base de engenharia significativamente mais sólida. A suíte final executou **32 testes aprovados**, incluindo testes HTTP reais do Flask, migração do SQLite, jobs persistidos, timeline reversível, validação com `ffprobe`, renderização vertical com áudio, legendas ASS/SRT, score editorial, feedback humano, deduplicação de lotes e bloqueio de traversal.

> **Estado honesto:** o código foi implementado e validado localmente, mas ainda não é possível afirmar paridade total com o OpusClip. A qualidade final da transcrição, detecção facial, análise multimodal e provedores de IA depende das dependências e credenciais instaladas na máquina do usuário, de vídeos reais e de calibração com feedback histórico.

## Principais entregas

| Área | Entrega realizada | Benefício prático |
| --- | --- | --- |
| Timeline | Camada canônica e reversível em `modules/timeline.py` | Evita cortes e legendas fora de sincronia quando houver vídeo derivado sem silêncio |
| Segurança | `modules/security.py`, validação de caminhos, bloqueio de traversal e symlinks externos | Reduz acesso acidental ou malicioso fora do workspace |
| Jobs | `modules/job_manager.py` com estados persistidos, progresso, cancelamento cooperativo e recuperação | Permite reconectar, consultar e cancelar sem depender de estado global volátil |
| Ranking | `modules/editorial_ranker.py` com score explicável, fatores, confiança, contexto e diversidade | Substitui a impressão de “viralidade” por potencial editorial auditável |
| Renderização | Presets Shorts, Reels, TikTok, quadrado e paisagem, com validação `ffprobe` | Padroniza resolução, aspecto, áudio e qualidade de saída |
| Legendas | Escaping ASS, timestamps não negativos e suporte a destaque palavra a palavra | Evita arquivos de legenda inválidos e mantém sincronização previsível |
| Revisão | Feedback persistido por clip, aprovação/rejeição e fatores visíveis no card | Cria um ciclo humano de seleção antes da publicação |
| Automação | Scanner de lotes com hash SHA-256, deduplicação e manifesto reproduzível | Prepara processamento local em lote sem duplicar arquivos |
| Frontend | Recuperação de jobs, preset de plataforma e painel de fatores editoriais | Aproxima o fluxo de revisão de uma ferramenta de edição profissional |
| Resiliência | Fallback HTTP quando Flask-SocketIO não está instalado | Permite diagnóstico e operação mínima em instalações incompletas |

## Arquitetura implementada

O pipeline agora segue uma sequência com contratos explícitos: ingestão segura, identificação e metadados, transcrição e sinais, timeline canônica, geração de candidatos, score editorial, deduplicação, revisão, renderização por preset, legendas, validação de mídia, persistência e feedback.

A seleção conserva `viral_score` para não quebrar a interface existente, mas passa a produzir também `editorial_potential_score`, `editorial_score_version`, `factors`, `confidence`, `reason` e `diversity_penalty`. Os fatores são hook, flow, value, context match, audio energy, clarity e completeness. Isso é deliberadamente uma heurística explicável; sem dados históricos não deve ser apresentada como previsão estatística de viralização.

A renderização utiliza presets alinhados aos formatos públicos de vídeo curto e às necessidades de layout por canal [6]. O preset selecionado é salvo em configuração e aplicado tanto ao cortador quanto à geração de legendas. Cada export pode ser rejeitado pelo pipeline se não tiver os streams esperados, resolução configurada, duração compatível ou áudio quando requerido.

## Verificação executada

Foram executados os seguintes comandos na branch local:

```bash
node --check static/js/app.js
python3 -m py_compile app.py config.py database.py modules/*.py tests/*.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

O resultado foi de **32 testes aprovados**. Também foi executado um smoke test de importação do servidor, que confirmou a disponibilidade do app, do gerenciador de jobs e do workspace.

A tentativa de instalar dependências ausentes do `requirements.txt` falhou por indisponibilidade de resolução DNS para PyPI no ambiente de execução. Portanto, a validação desta sessão cobre a arquitetura, o fallback NLP, a execução FFmpeg e os contratos do servidor; ela não substitui um teste com `faster-whisper`, MediaPipe, Ollama ou chaves de Gemini/Claude ativos.

## GitHub e artefatos de transferência

A branch local foi criada sem alterar a branch principal. O commit principal é `893204e`; o segundo commit registra o estado de entrega local. A publicação automática falhou com **HTTP 403**, pois o GitHub recusou a permissão do token disponível para `SAGIEV007/furia-clips.git`. Não foi feito merge nem foi fingido que o push foi concluído.

Foram gerados os seguintes artefatos:

| Arquivo | Uso |
| --- | --- |
| `furia-clips-rebuild-rebuild.patch` | Aplicar os dois commits sobre um clone compatível |
| `furia-clips-rebuild.bundle` | Transferir a branch e seu histórico completo para outro clone Git |
| `docs/architecture.md` | Arquitetura-alvo e decisões de engenharia |
| `docs/roadmap.md` | Roteiro de evolução por prioridade |
| `docs/quality-gates.md` | Critérios de aprovação de jobs e exports |
| `docs/test-report.md` | Detalhamento da validação realizada |
| `furia-opus-benchmark.md` | Benchmark público e critérios de paridade prática |

Para publicar quando a autenticação for corrigida, o fluxo local é:

```bash
git remote -v
git push -u origin manus/rebuild-opus-parity
gh pr create --base main --head manus/rebuild-opus-parity \
  --title "Rebuild clipping pipeline for explainable editorial workflow" \
  --body-file docs/rebuild-report.md
```

## O que ainda falta para se aproximar mais do benchmark

A próxima etapa de maior impacto é transformar o revisor em um editor de timeline real: permitir arrastar início e fim, recalcular legendas sem retranscrever, rerenderizar somente o clip alterado e salvar ajustes. Em seguida, deve ser implementado reenquadramento temporal suave por rosto/objeto, em vez de apenas crop central ou média de posições.

Também falta fechar o processamento em lote de ponta a ponta. Esta execução implementou descoberta, hash, deduplicação e manifesto; a fila de execução deve ser conectada ao pipeline completo depois que a função principal for extraída para um serviço reutilizável. Por fim, a qualidade do ranking deve ser calibrada com aprovações/rejeições reais, métricas de retenção e comparação por canal, em vez de depender somente de heurísticas textuais.

## Referências

[1]: https://help.opus.pro/docs/article/introduction-to-opusclip "Introdução oficial ao OpusClip"

[2]: https://help.opus.pro/docs/article/9947095-clip-anything "ClipAnything: análise multimodal"

[3]: https://help.opus.pro/docs/article/how-to-use-clipanything "Como usar ClipAnything"

[4]: https://help.opus.pro/docs/article/clip-anything-prompt-manual "Manual de prompts do ClipAnything"

[5]: https://help.opus.pro/docs/article/virality-score "Score de viralidade do OpusClip"

[6]: https://help.opus.pro/docs/article/apply-the-layouts "Layouts por cena"

[7]: https://www.opus.pro/api "API oficial do OpusClip"

[8]: https://www.opus.pro/pricing "Tabela pública de capacidades e planos"
