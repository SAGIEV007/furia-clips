# Relatório de testes — Fúria Clips

> Este documento contém o relatório inicial de testes (histórico) e o status atual da suíte.

## Status atual (2026-08-30)

A suíte atual está estabilizada com:

- **866 testes aprovados**
- **3 testes ignorados**
- **0 erros**
- **Tempo de execução**: ~43s

Ferramenta: `pytest` via `run_pytest.py`.  
Profiling de imports: `scripts/measure_imports.py`.

---

## Relatório inicial de testes

## Ambiente

Os testes foram executados no clone local `/home/ubuntu/furia-clips-rebuild`, na branch `devin/1782248654-furia-clips`, com Python 3 e FFmpeg/ffprobe disponíveis no PATH. Foi usada a suíte padrão `unittest`, sem depender de pytest.

## Fixture

Foi gerada `tests/fixtures/sample_av.mp4` com 2 segundos, vídeo 320×180, áudio AAC e vídeo H.264. A duração confirmada por `ffprobe` foi 2.000000 segundos.

## Comando

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Resultado

A suíte inicial terminou com **10 testes aprovados**:

| Área | Testes | Resultado |
| --- | ---: | --- |
| Timeline original/derivada | 4 | Aprovado |
| Validação de mídia | 3 | Aprovado |
| Seleção NLP e anti-overlap | 3 | Aprovado |

Os testes da timeline comprovam que um trecho localizado em 5–8 segundos no vídeo derivado, após remover o intervalo original de 5–10 segundos, é convertido para 10–13 segundos no vídeo original. Também foi coberto o mapeamento de um intervalo que atravessa a fronteira entre dois segmentos de fala.

## Limitações atuais

Ainda não foram executados testes que exijam modelo Whisper, MediaPipe, Ollama, Gemini, Claude, navegador ou vídeo real de longa duração. Também ainda não existe teste de integração do servidor Flask, cancelamento de subprocesso, persistência de jobs, segurança de symlinks ou renderização de legendas. Esses testes serão adicionados nas fases correspondentes.

## Validação final da reconstrução

Após a integração de jobs, ranking editorial, presets, revisão humana, feedback, lote e fallback de SocketIO, foram executados:

```bash
node --check static/js/app.js
python3 -m py_compile app.py config.py database.py modules/*.py tests/*.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

O resultado final foi de **32 testes aprovados**. A suíte inclui smoke tests HTTP do Flask, migração SQLite, API de presets, bloqueio de traversal, jobs persistidos, score editorial, timeline, validação ffprobe, renderização 9:16 com áudio, legendas ASS/SRT, feedback, lote e deduplicação.

O smoke test de importação do servidor também foi aprovado depois do fallback opcional para Flask-SocketIO. A tentativa de instalação das dependências declaradas falhou por indisponibilidade de DNS para PyPI no ambiente de execução; por isso, a funcionalidade que depende de `faster-whisper`, MediaPipe, Ollama ou provedores online ainda requer validação em uma máquina com essas dependências instaladas.
