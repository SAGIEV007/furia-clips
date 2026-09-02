# Auditoria das branches e estratégia do Furia — 02/09/2026

> **Para quem lê isto sendo um agente:** este arquivo é o plano de trabalho
> corrente do Furia. Ele existe para sobreviver à perda de janela de contexto.
> Se você vai mexer no repositório, leia até o fim antes de escolher uma base.
> As leis da seção 6 valem para qualquer agente, em qualquer harness.
>
> Versão legível para humano (mesmo conteúdo, com o mapa desenhado):
> https://claude.ai/code/artifact/9bdfe6a0-fae7-4967-b165-cc066092579a
> *(página privada da conta do Fernando — um programa que não esteja logado
> como ele não consegue abrir. Use este arquivo.)*

---

## 0. Como estes números foram obtidos

Cada branch foi baixada num `git worktree` descartável e a suíte inteira foi
executada ali, no dia 02/09/2026. **Nenhum número abaixo foi lido de relatório.**
Isso importa porque um dos achados é justamente um relatório que discorda do
repositório.

Para repetir a medição:

```
git worktree add -f /tmp/wt <branch>
cd /tmp/wt && python3 -m pytest -q | tail -3
git worktree remove --force /tmp/wt
```

---

## 1. O estado do repositório

Doze branches remotas. Cinco linhas de trabalho vivas. **Três delas estão
construindo a mesma coisa** — o Furia Studio por cima do motor do Furia 1 —
partindo do mesmo commit e sem saber uma da outra.

| Branch | Base | Passando | Quebrados | O que é |
|---|---|---|---|---|
| `claude/furia-1-antes-do-furia-2` | — | 891 | **0** | A versão 6.61 intacta (`fb51dae`). Rede de segurança. |
| `claude/repo-access-commits-imgjmk` | 6.61 | 1082 | **0** | Estúdio + motor real + console + blocos + painel + CHUB. **Tronco recomendado.** |
| `furia-studio-experimental-20260828` | 6.61 | 882 | **25** | O melhor motor de corte que existe hoje. Apagou a interface antiga e deixou os testes dela quebrados. |
| `furia-studio-f1-integration` | 6.61 | — | idem | Versão anterior da de cima. Não precisa existir. |
| `furia-sync-portable` | **antes** da 6.61 | — | **13** | 253 commits numa linha que se separou 10 dias antes. Perdeu 19 módulos. |
| `manus/*`, `arena/*`, `devin/*`, `publish-context-only`, `base-init` | várias | — | — | Paradas há semanas. Ruído. |

### Onde cada uma se separou

```
15 ago ──── 38d0794 ──┬── 182 commits ──── fb51dae (6.61) ──┬── studio-experimental (28 ago)
                      │                                     ├── studio-f1-integration (28 ago)
                      │                                     ├── repo-access-commits (26 ago→02 set)
                      │                                     └── furia-1-antes-do-furia-2 (cópia)
                      │
                      └── 253 commits ───────────────────────── furia-sync-portable (01 set)
```

A `furia-sync-portable` **não contém** os 182 commits que levaram até a 6.61.
Ela nunca recebeu o Painel, o espelho do CHUB, o Acervo nem o sistema de blocos.

---

## 2. O que melhorou

### O corte — na `furia-studio-experimental`

`modules/clip_selector.py` ganhou **742 linhas**, todas sobre *onde a resposta
realmente começa* numa entrevista. Funções novas que interessam:

- `_broadcast_turns` / `_broadcast_boundary_between` — a virada do entrevistador
- `_first_sentence_after_boundary` — a primeira frase depois da fronteira
- `_is_stabilized_response_opener` / `_stabilized_response_start` — reconhecer
  quando o entrevistado ainda está se recompondo e a resposta de verdade vem
  depois
- `_evaluate_interview_boundaries`
- `_select_with_gemini` — seleção assistida, opcional e com orçamento

Módulos que cresceram junto: `interview_turns.py` (+157), `video_cutter.py`
(+236), `gemini_video.py` (+248), `transcriber.py` (+146),
`transcript_parser.py` (+109), e `editorial_disagreement.py` (novo, 245).

### O defeito real que essa branch achou

Transcrição do **Tactiq com horário absoluto de gravação** em linhas separadas
do texto fazia o motor entregar **2 cortes onde a referência humana tinha 9**.
Depois da correção no leitor (blocos Tactiq explícitos têm preferência sobre
timestamps embutidos; relógio absoluto só é deslocado quando excede claramente
a duração do vídeo): **9 cortes**, batendo com a referência.

Isso foi encontrado processando material de verdade e comparando com seleção
humana — é o único tipo de evidência que vale sobre qualidade de corte.

### A interface

As três branches independentes chegaram à mesma conclusão: o Furia Studio é
melhor que o Furia 1 e melhor que o Furia 2 para este trabalho. Convergência
independente é sinal forte.

---

## 3. O que piorou

- **Um relatório diz verde onde o repositório está vermelho.**
  `docs/CYCLE_REPORT_2026-08-28.md` registra "880 testes aprovados". Rodando
  hoje na mesma branch: 882 passando e **25 quebrados**, todos com
  `ReferenceError: state is not defined` — testes de navegador da interface
  antiga apontando para `/`, que agora serve o Studio.

- **Sete arquivos de teste foram esvaziados, não corrigidos.**
  `tests/archived/*.archived.txt`, todos com **zero bytes**. Eram os testes da
  interface antiga. Outros três arquivos da mesma interface ficaram para trás
  e são os que quebram.

- **19 MB de PNG entraram no repositório** sem compressão, incluindo
  `poolsuite-studio-reference.png`, que nenhuma tela usa.

- **A `furia-sync-portable` perdeu 19 módulos**, entre eles:
  `preanalysis_blocks`, `editorial_block_memory` (o sistema de blocos),
  `espelho_chub` (os 29.596 posts do Painel), `acervo_library`, `speaker_id`,
  `interview_turns`, `source_reading`, `topic_segmenter`, `chub_client`,
  `campaign_hub_memory`, `headline_copy`, `headline_quote`,
  `editorial_benchmark`, `editorial_learning_store`, `estilo_publicado`,
  `non_content_detector`, `caption_lexicon`, `source_boundary`,
  `source_interval`. E tem 86 arquivos de teste contra 124 do tronco.

- **O que a `sync-portable` ganhou** e vale resgatar: `chub_mcp.py` (211 linhas,
  CHUB ao vivo via MCP com endereço e chave em variável de ambiente — feito do
  jeito certo), `youtube_importer.py` (215), `fronteira_assunto.py` (312),
  `editorial_search.py` (552), `approved_clip_priors.py` (296),
  `quality_metrics.py` (256).

---

## 4. O plano: um tronco, o resto vira colheita

**Regra de execução:** cada passo só começa depois que a suíte inteira estiver
verde na máquina de quem funde. Verde medido, nunca declarado.

### Passo 1 — fixar o tronco
`claude/repo-access-commits-imgjmk`. Escolhida por ser a única com zero testes
quebrados, por preservar a interface antiga em `/classico` em vez de apagá-la,
e por já ter de volta o que foi pedido pelo nome: console, blocos, painel, CHUB.

### Passo 2 — trazer o leitor de transcrição
De `furia-studio-experimental-20260828`: `modules/transcript_parser.py` e os
testes `test_transcript_request.py`. É defeito real com evidência real e não
depende de tela nenhuma. Primeiro por ser o de maior retorno e menor risco.

### Passo 3 — trazer a precisão de corte
`modules/interview_turns.py` e o trabalho de fronteiras em
`modules/clip_selector.py`, com `test_sabatina_boundaries.py` e
`test_pergunta_e_fronteira.py` junto.
**Portão:** depois deste passo, rodar uma fonte real e comparar com a seleção
humana antes de seguir. Sem essa comparação não se sabe se melhorou.

### Passo 4 — trazer o endurecimento do motor
`video_cutter.py` (cancelamento), `gemini_video.py` (orçamento e fallback),
`transcriber.py` (reserva). São proteções contra travar no meio de meia hora
de trabalho.

### Passo 5 — colher três peças da `furia-sync-portable` e aposentá-la
Só `chub_mcp.py`, `youtube_importer.py` e `fronteira_assunto.py`. Fundir os 253
commits traria de volta a perda dos blocos e do espelho. Depois de colhidas, a
branch vira arquivo histórico.

### Passo 6 — apagar o ruído
`furia-studio-f1-integration` (contida na experimental), `manus/*`, `arena/*`,
`devin/*`. Doze branches é escolher corte olhando doze pastas.

---

## 5. Orquestração: Opus 5, modelos gratuitos e Obsidian

### A regra que falta

> **Modelo grátis prepara e confere. Modelo grátis não decide.**

Preparar e conferir são baratos e verificáveis na hora. Decidir o que é um bom
corte não é verificável na hora, e um corte errado custa uma tarde de trabalho.

### Os papéis

| Quem | Faz | Custo |
|---|---|---|
| **Opus 5** | Decide: o que é corte bom, onde a borda entra, o que vai para a tela, qual branch vira tronco. Escreve o código. | caro, use bem |
| **Modelo grátis (produção)** | Baixa fonte, normaliza transcrição, roda `ffprobe`, monta inventário, resume diff, lista diferenças entre branches. | grátis, em paralelo |
| **Modelo grátis (conferente)** | Roda a suíte e devolve o número cru. Tira foto em 1366×768. Procura chave e transcrição num diff. **Nunca opina — só relata.** | grátis, sempre |
| **Fernando** | Assiste ao corte e diz se presta. Única medida externa de qualidade que o programa tem. | o gargalo real |

### O vault do Obsidian

O Hermes tem memória própria em quatro camadas e a recomendação da própria
documentação é **não entregar o vault inteiro**: uma pasta com escopo, fatos
duráveis num arquivo, preferências noutro, segredo nenhum lá dentro.

```
Furia/
  00-NORTE.md          as leis que não mudam
  01-ESTADO.md         onde o programa está HOJE — reescrito a cada ciclo
  02-DECISOES/         uma nota por decisão: o quê, quando, por quê, o que foi descartado
  03-DEFEITOS/         o que quebrou, como se reproduz, qual teste guarda
  04-CICLOS/           hipótese → o que rodou → número medido → conclusão
  05-MATERIAL/         só conclusões editoriais. NADA de transcrição, mídia ou chave
  99-INBOX.md          o que o agente jogou e ainda não foi arrumado
```

Duas regras que mantêm a pasta útil: **`01-ESTADO.md` é reescrito, nunca
acrescentado** (senão vira log e ninguém lê), e **nada entra em `05-MATERIAL`
que não seria publicado** — transcrição de entrevista não publicada e chave de
API ficam fora do vault, sempre.

### Skills que valem escrever

Cada uma nasce de um erro que já aconteceu neste repositório. Skill boa não é a
que faz coisa nova — é a que impede a repetição de um erro caro. Lugar:
`~/.hermes/skills/`, que é compartilhado por todos os agentes da máquina.

| Skill | Impede |
|---|---|
| `furia-verdade` | Aceitar branch por relatório. Roda a suíte numa cópia descartável e devolve o número cru. |
| `furia-colher` | Perder peça sem notar. Compara duas branches por **capacidade**: módulos, rotas, testes que entraram e sumiram. |
| `furia-corte-a-corte` | Achar que melhorou sem prova. Roda uma fonte e compara com a seleção humana. |
| `furia-tela` | Esquecer que a tela tem 768px de altura. Foto de cada tela e acusação do que ficou abaixo da dobra, sobreposto ou ilegível. |
| `furia-segredo` | Chave ou transcrição indo para repositório público. Varre o diff antes de qualquer envio. |
| `furia-registro` | Registro livre virar log ilegível. Escreve o ciclo no Obsidian na estrutura fixa. |

O Hermes cria skills sozinho a partir do que deu certo. Isso ajuda, mas skill
nascida de acerto ensina a repetir o acerto; **skill nascida de erro impede o
prejuízo**. As seis acima são do segundo tipo.

### Harness e provedores

- **Hermes Agent** (Nous Research) — fique. Já tem prontas as duas coisas que a
  estratégia atual monta à mão: memória que sobrevive à janela de contexto, e
  disparo de até três sub-agentes paralelos com modelos diferentes, cada um com
  terminal e chamadas próprias. Skills compartilhadas em `~/.hermes/skills/`.
- **OpenCode Zen** — use como fonte de modelo barato para preparar e conferir.
  **Trava séria:** na faixa gratuita os prompts podem ser usados para treinar os
  modelos, e o conjunto de modelos grátis gira. Transcrição, dados do CHUB e o
  espelho **nunca** passam por lá. Modelo grátis toca código e número, nunca
  material.
- **OpenRouter / NVIDIA NIM** — outras fontes de modelo gratuito para os mesmos
  papéis, com a mesma trava.
- **DeepSeek Harness (dsh)** — ainda não. É MIT, roda em Node, tudo é plugin
  (modelo, ferramentas, sessão, sandbox, laço, orquestração e tela). Mas a
  própria DeepSeek chama de *developer preview* e avisa que virão mudanças que
  quebram compatibilidade. O Furia já sofre de troca de base demais.

---

## 6. Leis de repositório

A fragmentação não veio de modelo ruim. Veio de falta de regra. Estas cinco
custam pouco e teriam evitado tudo o que está descrito acima.

1. **Um tronco só.** Todo agente parte do tronco e volta para o tronco. Branch
   que vive mais de uma semana longe vai divergir, e divergência de 253 commits
   não se resolve com merge — se resolve com colheita manual, que é cara.

2. **Verde é medido, nunca declarado.** Nenhum trabalho entra no tronco por
   relatório dizendo que passou. Entra quando a suíte roda na máquina de quem
   funde e o número aparece.

3. **Teste não se esvazia.** Teste que quebrou por mudança de tela ou se
   conserta ou se apaga com o motivo no commit. Arquivo de zero byte numa pasta
   `archived` é um teste apagado fingindo que não foi.

4. **Peça que some tem que aparecer.** Antes de fundir, comparação por
   capacidade: o que entrou, o que sumiu. Perder o sistema de blocos sem
   ninguém notar só é possível porque ninguém olhou.

5. **O material nunca sai da máquina.** Transcrição, mídia, dados do CHUB e
   chave não entram no repositório, não entram no vault e não passam por modelo
   de faixa gratuita. Uma vez já foi.
