# ESTADO — o quadro de aviso

> Este arquivo é lido **antes de qualquer ação**, por qualquer modelo. Ele é a
> memória curta compartilhada. Uma página. Se passar de uma página, alguma coisa
> aqui virou história e devia ter ido para o cofre.
>
> Quem termina uma tarefa atualiza este arquivo. Sem exceção.

---

## Onde o trabalho acontece

| | |
|---|---|
| Branch do turno da noite | `furia-treino-noturno` |
| Branch que o editor baixa | `claude/repo-access-commits-imgjmk` — **não tocar de madrugada** |
| Outra linha em andamento | `furia-sync-portable` — outro agente trabalha lá; não mexer sem combinar |

## A régua

| | |
|---|---|
| Script | `python scripts/regua.py` |
| Gabarito | `tests/fixtures/acervo_sabatina_band.json` — versionado no repositório |
| Verdade de fora | 10 blocos do Acervo (CHUB), supervisionados por gente |
| Números que contam | `abre junto com o bloco`, `fecha junto com o bloco`, `blocos alcançados`, `pior repetição` |
| Números que **não** são meta | tudo sob "diagnóstico — o Furia se avaliando" |
| Histórico | `docs/hermes/medicoes.txt` (use `--salvar <rótulo>`) |

Roda sem instalar nada e sem depender de pasta temporária. A régua da outra
branch (`bench_contexto.py`, em `furia-sync-portable`) lê o gabarito de
`AppData/Local/Temp/` — pasta temporária some, e régua que some no meio da noite
é pior que régua nenhuma, porque o turno continua rodando e passa a medir nada.
Esta lê do próprio repositório.

## Última medição

```
2026-09-03  linha-de-base  (sabatina da Band, 1923s)
  blocos do Acervo alcançados ...  5/10   50%
  abre junto com o assunto ......  2/5    40%   (dos blocos alcançados)
  atravessa dois assuntos .......  1/11    9%
  pior repetição entre cortes ...        18%
  blocos engolidos ..............         1
  entregues 11 · adiados 5 · o Acervo diz que cabem 32
```

Medida igual na máquina do editor e na minha — o número é reproduzível, dá para
usar como referência comum.

**O que ela já ensina:** o Furia marca "contexto completo" em 10 de 11 cortes,
e não chega em metade dos assuntos que o Acervo marcou.

## A fila de ideias

Ordem de tamanho do ganho. Uma de cada vez, sempre com medição antes e depois.

### 1. Os quinze minutos que não rendem corte nenhum  ← COMEÇAR POR AQUI

Os blocos 1 a 5 do Acervo (31,6 s a 894,3 s — **45% do vídeo**) receberam
**zero** cortes entregues. O Acervo diz que cabem **16** cortes ali.

Já apurado, para não refazer:

- o portão editorial **não** é o culpado: só 3 candidatos chegaram nele vindos
  dessa metade, e os 3 eram ruins de verdade (abre no jornalista, abre no meio
  da frase, contém a chamada do intervalo);
- a peneira de entrevista **não** é a culpada: antes dela já eram 4 candidatos
  na primeira metade contra 21 na segunda;
- ou seja: **o desequilíbrio nasce na geração de candidatos.** O seletor produz
  39 candidatos e quase todos na segunda metade.

Primeiro passo: instrumentar a geração de candidatos para contar quantos nascem
por bloco, e comparar os sinais que ela usa (densidade de fala, energia,
frequência de turno) entre as duas metades. **Descobrir antes de mudar.**

Alvo: `blocos do Acervo alcançados` subir de 5/10.

### 2. O corte que atravessa dois assuntos

1 em 11 hoje. O caso concreto: o corte 1742,3–1773,4 pisa no bloco 8
(prefeitos/reeleição) e no bloco 9 (privatizações) — dois assuntos colados num
clipe só.

O Furia lê a fonte em **8** blocos temáticos próprios; o Acervo marca **10**. A
travessia acontece onde as duas leituras discordam. Comparar as duas divisões e
ver onde elas se afastam.

Alvo: `atravessa dois assuntos` chegar a 0/11.

### 3. Abrir onde o assunto começa

2 de 5 hoje. Quando o Furia entra num assunto, ele começa no lugar certo em 40%
das vezes.

Existe pesquisa pronta para isso na branch `furia-sync-portable`:
`modules/fronteira_assunto.py` — recuo até a fronteira do assunto, com validação
contra 400 trechos de gabarito humano (anáfora órfã: 100% de precisão;
conectivo dependente: 87,5%). **Portar e medir**, não reescrever do zero.

Alvo: `abre junto com o assunto` subir de 40%.

## Linhas mortas — não tentar de novo sem ideia nova

Registrar aqui o que já foi tentado três vezes sem mover o número.

- (nada ainda)

## O modelo dos bots

`stepfun/step-3.7-flash:free`, provider `nous`
(`inference-api.nousresearch.com`). Modelo pequeno e rápido.

Isso é seguro no desenho porque **quem decide manter ou desfazer uma mudança é o
número da régua, não a opinião do modelo**. Um modelo pequeno consegue rodar o
laço; ele não precisa julgar corte.

Não achei documentação pública dizendo se o nível grátis da Nous treina em cima
do que recebe. Enquanto não houver, vale a regra conservadora: **transcrição,
fala do Renan, dados do CHUB e chaves não passam por bot.** Bot mexe em código e
número.

## Travado / precisa do editor

- **Faltam exemplos aprovados e rejeitados.** Dez cortes que ele aprovaria e dez
  que rejeitaria. Sem isso, a calibração de headline continua no meu julgamento
  em vez do dele, e dois testes seguem parados.
  → O caderno de vereditos (`skills/caderno-de-vereditos.md`) é o caminho para
  isso: trinta vereditos etiquetados resolvem, e ele os produz revisando pelo
  WhatsApp, que é coisa que já ia fazer de qualquer jeito.
- **A chave do CHUB foi commitada num repositório público.** Ela precisa ser
  trocada por quem opera o CHUB. Apagar do código não resolve: o histórico
  guarda.

## Consertado recentemente (para não reabrir)

- Duas moagens rodando ao mesmo tempo; o botão de parar mirava o trabalho errado.
- A nota passou a descontar quando o corte abre no apresentador (intervalo,
  encerramento, cortesia) em vez de no entrevistado.
- Pergunta de jornalista com mais de 8s é aparada; até 8s fica.
- Portões medidos do CHUB (`+14 / −28 / −18`) entraram na nota.
