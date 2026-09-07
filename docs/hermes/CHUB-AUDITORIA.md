# O que o CHUB tem, e o que o Furia usa

Auditoria feita em 07/09 porque o editor cobrou, e a cobrança estava certa:

> *"esse tipo de coisa era crucial e você tinha que ter notado ANTES, por isso,
> antes de fazer essa terceira régua, verifique TUDO o que realmente pode ser
> utilizado do chub"*

---

## Primeiro, uma correção minha

Eu escrevi que *"o Furia lê a sabatina em 8 blocos próprios; o Acervo marca
10"*, e ele leu isso — com razão — como **"acertou 8 de 10"**. Não é isso, e a
frase foi mal escrita.

São duas medidas diferentes:

| o que é | o número |
|---|---|
| **assuntos alcançados** — dos 10 blocos do Acervo, em quantos o Furia entregou algum corte | **9 de 10**, medido |
| **granularidade própria** — em quantos pedaços o Furia divide o mesmo vídeo | **8**, contra 10 do Acervo |

O segundo **não é uma nota**. Dividir em 8 em vez de 10 não quer dizer acertar
8; quer dizer cortar o vídeo em pedaços maiores. **Nunca medi se aqueles 8 caem
nos mesmos lugares que os 10.** Não vou repetir aquele número como se fosse
desempenho.

---

## As 18 ferramentas do CHUB, e quem as usa

| ferramenta | o que dá | o Furia usa? |
|---|---|---|
| `chub_acervo_blocks` | blocos temáticos QA-gated de um vídeo | **sim** |
| `chub_acervo_transcript` | transcrição com tempo, turno, troca de locutor | **sim** |
| `chub_transcript` | texto dos cortes **publicados** | **agora sim** (régua 3) |
| `chub_top_posts` | os publicados que mais renderam | **agora sim** (régua 3) |
| `chub_acervo_pauta` | candidatos de pauta com razões e score | não |
| `chub_acervo_stats` | avanço e qualidade do Acervo | não |
| `chub_search` | busca semântica no acervo de posts | não |
| `chub_video_metrics` | desempenho por vídeo | não |
| `chub_tag_performance` | desempenho por tema | não |
| `chub_audience` / `chub_cohort_stats` | quem assiste | não |
| `chub_top_posts` por gancho | famílias de gancho | parcial |
| `chub_mission_book_search` | Livro Amarelo, dossiês | não |
| `chub_city_dossiers` | dossiês municipais | não |
| `chub_x_interactions`, `chub_ads`, `chub_accounts`, `chub_sql`, `chub_youtube_longform_search` | outras superfícies | não |

**O julgamento honesto:** a maioria dos "não" é **certa**. Desempenho por tema,
audiência, dossiê municipal e Livro Amarelo dizem **sobre o que falar** — pauta,
não corte. O Furia não escolhe assunto; ele corta o que já foi falado. Ligar
tudo isso seria confundir duas ferramentas.

As que faltavam de verdade eram as duas dos publicados, e agora estão ligadas.

---

## O defeito que a pergunta dele achou

> *"o fúria não deveria estar SEMPRE usando o chub? mesmo de régua?"*

**Deveria, e não estava.** Não por decisão — por um fio solto.

O programa tinha as duas pontas e nada entre elas:

```
find_snapshot_for      procurava o Acervo deste vídeo NO DISCO
ChubClient.exportar    sabia BUSCAR o Acervo de qualquer vídeo
```

Resultado: se o arquivo não tivesse sido baixado antes **à mão**
(`scripts/sincronizar_acervo.py`), a moagem seguia cega — **mesmo com o vídeo
publicado no Acervo e a chave configurada**. Todo corte saía com `bloco_chub:
null` num vídeo que tinha bloco revisado por gente.

É o mesmo formato do erro dos pesos do CHUB, que ficaram semanas no disco sem
ninguém lê-los: **a capacidade existia, a ligação não.**

**Consertado.** `buscar_no_acervo_se_faltar` entra na hora da moagem: se o vídeo
tem id do YouTube, o export não está no disco e o CHUB está configurado, ele
busca. Sem CHUB, sem rede, ou sem bloco publicado, devolve vazio e a moagem
segue com a leitura própria — que continua sendo o caminho normal da live de
ontem.

---

## E a pergunta que fica: por que não 10 de 10?

Ele perguntou por que, usando o CHUB, não dá 10 de 10. Duas respostas, e as duas
importam:

**1. Até hoje ele não estava usando** nas moagens sem export baixado à mão. A
medição de 9/10 da sabatina saiu da régua, que lê o gabarito do arquivo — não da
moagem normal do programa. Com o fio ligado, a moagem passa a ver o que a régua
já via.

**2. Mesmo com o CHUB, 10 de 10 não é automático.** O Acervo diz **onde o
assunto está**; ele não corta. Alcançar os 10 blocos exige que o seletor produza
candidato aproveitável em cada um — e o bloco 4 tem 33 segundos, abaixo de
muitos mínimos. É alcançável, não é de graça.

O caminho para 10 de 10 passa por usar os blocos do Acervo como **fronteira de
candidato** quando eles existem, e não só como evidência anexada depois. Isso é
ideia de fila, com medição antes e depois — não mexo sem medir.
