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
| Branch do trabalho autônomo | `furia-treino-noturno` |
| Branch que o editor baixa | `claude/repo-access-commits-imgjmk` — **não tocar sem ele olhando** |
| Outra linha em andamento | `furia-sync-portable` — outro agente trabalha lá; não mexer sem combinar |

## A régua

| | |
|---|---|
| Régua do assunto | `python scripts/regua.py [--material <arquivo>]` |
| Régua do editor | `python scripts/regua_vereditos.py` |
| Régua da forma | `python scripts/regua_publicados.py` (contra os cortes publicados) |
| Régua do assunto próprio | `python scripts/regua_assuntos.py` (o Furia enxerga as viradas?) |
| Material novo | `python scripts/novo_material.py --sortear` (traz do Acervo, com gabarito) |
| Gabarito padrão | `tests/fixtures/acervo_sabatina_band.json` — versionado no repositório |
| Verdade de fora | 10 blocos do Acervo (CHUB), supervisionados por gente |
| Números que contam | `blocos alcançados`, `abre junto com o assunto`, `atravessa dois assuntos`, `pior repetição` |
| Números que **não** são meta | tudo sob "diagnóstico — o Furia se avaliando" |
| Histórico | `docs/hermes/medicoes.txt` (use `--salvar <rótulo>`) |

Rodam sem instalar nada e sem depender de pasta temporária. A régua da outra
branch (`bench_contexto.py`, em `furia-sync-portable`) lê o gabarito de
`AppData/Local/Temp/` — pasta temporária some, e régua que some no meio da noite
é pior que régua nenhuma, porque o trabalho continua e passa a medir nada. Esta
lê do próprio repositório.

**Material novo tem que vir do Acervo, não do YouTube solto.** Sem gabarito não
há como saber se o corte ficou bom. São 5.391 blocos revisados por gente
disponíveis — cada vídeo de lá já vem com a resposta.

## Última medição

```
2026-09-03  depois-vocativo-solto  (sabatina da Band, 1923s)
  blocos do Acervo alcançados ...  9/10   90%    (era 5/10)
  abre junto com o assunto ......  2/9    22%    (era 2/5 — o de baixo cresceu)
  atravessa dois assuntos .......  2/16   12%    (era 1/11)
  pior repetição entre cortes ...        18%     (igual)
  blocos engolidos ..............         1      (igual)
  entregues 16 · adiados 6 · o Acervo diz que cabem 32
```

Medida igual na máquina do editor e na minha — o número é reproduzível, dá para
usar como referência comum.

**Cuidado ao ler `abre junto com o assunto`:** ele é contado sobre os blocos
alcançados. Continuam sendo 2 aberturas certas; o que mudou é que agora são 9
blocos em vez de 5. Nenhum número absoluto caiu. Alcançar um bloco e abrir mal
é melhor que não alcançar — antes esses quatro blocos não davam corte nenhum.

## A fila de ideias

Ordem de tamanho do ganho. Uma de cada vez, sempre com medição antes e depois.

### RESOLVIDO — os quinze minutos que não rendiam corte nenhum

Ficava aqui a ideia 1. Está feita, e o diagnóstico que estava escrito nela
**estava errado**. Fica registrado porque a forma do erro se repete.

Estava escrito que "o desequilíbrio nasce na geração de candidatos" e que "a
peneira de entrevista não é a culpada". As duas frases eram falsas. Medindo
etapa por etapa, no material que tem gabarito:

```
saída crua do NLP           blocos 1-4: 13    blocos 5-10: 26
_align_to_interview_turns   blocos 1-4:  0    blocos 5-10: 25   <-- aqui
```

A geração de candidatos era **equilibrada**. A peneira de entrevista descartava
13 de 13. Causa: `first_address_to_guest` só reconhecia o nome abrindo a fala
(`Renan, ...`) ou fechando a pergunta (`..., Renan?`). A âncora usa a terceira
forma — `Também agradeço, Renan, por aceitar` — e ela faltava. Sem ela, a
entrega da palavra era lida aos **671 s**, e tudo antes disso virava "estúdio se
apresentando".

Uma vírgula no lugar de um ponto de interrogação: 5/10 → 9/10.

**A lição, que vale para a próxima:** aquele diagnóstico não foi medido, foi
deduzido de contagens já filtradas. Contagem depois da peneira não diz nada
sobre o que entrou nela. Instrumente etapa por etapa antes de escrever "não é
aqui" — a frase "já apurado, para não refazer" custou tempo justamente por
estar errada e parecer resolvida.

### 1. O Furia é quase cego para virada de assunto  ← A RAIZ, MEDIDA EM 07/09

**Era 1 das 9. Agora são 3.** Medido em 07/09, `antes-viradas`/`depois-viradas`.

A causa era um teto mecânico, não calibração: `min_sentences` fazia dois
trabalhos — decidir se havia material para segmentar, e servir de **distância
mínima entre duas viradas**. O segundo uso era um proxy ruim:

```
4 dos 10 blocos do Acervo têm menos de 32 frases; o menor tem 11
```

Com trinta e duas frases de distância obrigatória, esses quatro eram
**impossíveis de achar por construção**. A regra de verdade sempre foi em
segundos e já existia — `min_duration_s`, 15 s, o piso do próprio Acervo.
Trocado o proxy pela regra: 1/9 → 3/9, e a régua do Acervo **não se mexeu**
(9/10, 2/16, 18%, 1 engolido). Travado por teste.

Ainda faltam 6 das 9. Maior pedaço que o Furia enxerga: 357 s, onde o Acervo
marca três assuntos.

```
  ACERVO      o mais próximo que o Furia viu
   168,5   ->    50,8   (117,6s de erro)
   353,4   ->   348,8   (  4,6s)  ACHOU
   584,8   ->   584,8   (  0,0s)  quase — some no _build_sentences
   618,4   ->   584,8   ( 33,6s)
   894,3   ->   834,3   ( 60,0s)
  1116,0   ->  1144,8   ( 28,8s)
  1484,0   ->  1462,3   ( 21,7s)
  1765,2   ->  1742,3   ( 22,9s)
  1871,2   ->  1742,3   (128,9s)
```

**Isto é a raiz de quase tudo o que sobrou na fila**, e é a resposta à pergunta
do editor sobre por que não dá 10 de 10:

- `atravessa dois assuntos` (2 em 16) não se conserta aparando cauda — tentei,
  medi, e a apara **nunca dispara**, porque o Furia não vê a fronteira. Os dois
  cortes que atravessam estão, na leitura dele, no meio de um pedaço só.
- num vídeo do Acervo isso fica escondido: os blocos revisados cobrem a falha.
- **na live de ontem não cobre nada** — e é lá que ele trabalha.

Alvo: `viradas de assunto achadas` subir de 1/9, com
`python scripts/regua_assuntos.py` antes e depois. A régua do Acervo
(`regua.py`) continua sendo o juiz de que o corte melhorou de verdade.

**Cuidado que vale mais que a ideia:** não usar a borda do Acervo para cortar e
depois medir contra a borda do Acervo. O gabarito não pode ser a entrada — o
número subiria sem o corte melhorar.

### 2. Abrir onde o assunto começa — ARQUIVADA, ele decidiu em 07/09

**Não perseguir este número.** Ele decidiu:

> "Não precisa ser na melhor frase do Renan, APENAS se o que ele falar no corte
> tiver sentido completo, e se for uma pergunta curta do repórter não tem
> problema mostrar"

O alvo é **sentido completo**, não a borda. Otimizar `abre junto com o assunto`
levaria o motor para o lado errado: um corte que abre 40 s dentro do assunto e
se sustenta é bom; um que abre na borda e fica pela metade é ruim, e aquele
número não distingue os dois. Já saiu da meta da régua e virou referência.

Sentido completo não se mede de dentro — o Furia se dá 14/16 e 16/16. Quem sabe
é ele, pelo caderno de vereditos. A frente principal passou a ser encher o
caderno; ver `PLANO.md`.

O que a medição achou, guardado porque explica por que a ideia morreu:

Distância entre o começo de cada bloco e o corte mais próximo:

```
bloco  1   +13,4s      bloco  6   +67,1s
bloco  2   -49,9s      bloco  7   +21,8s
bloco  3   -80,2s      bloco  8    +0,0s   no lugar
bloco  4   +81,5s      bloco  9   -22,9s
bloco  5   +47,9s      bloco 10    +0,0s   no lugar
```

Não são bordas mal aparadas — são **treze a oitenta segundos**. Nenhum conserto
de fronteira move oitenta segundos, e o recuo é limitado por construção. O
seletor não erra a borda: ele escolhe **outro lugar** do assunto, o momento
mais forte em vez do momento de abertura.

Isso é decisão editorial, não defeito técnico: um corte que abre na pergunta do
jornalista ganha contexto e perde ritmo. Só ele decide qual quer, e os
vereditos dele são o que responde. **Não mexer antes disso.**

### 3. Os cortes do Furia são mais curtos que os publicados

Medido em 07/09 com a régua nova: os publicados vão de 52 s a 127 s (meio 92 s);
o Furia entrega de 16 s a 79 s (meio 52 s). **O mais curto do Furia tem 16 s; o
mais curto que a equipe publicou tem 52 s.**

Evidência de fora, não opinião. Antes de mexer em duração mínima: medir o efeito
nas outras réguas, porque encurtar o teto foi decisão medida um dia e pode ter
outro motivo. Uma mudança, antes e depois.

### 4. A emenda das janelas, quando o Ollama está instalado

`_select_with_llm` pica a transcrição em janelas de 25 blocos **sem
sobreposição** (`range(0, n, 25)` e `blocks[i:i+25]`). Um bom momento que cai
bem na emenda entre a janela 1 e a 2 é partido e pode se perder.

Os cortadores abertos resolvem isso com janelas sobrepostas — é a única técnica
deles que o Furia não tem.

Vale só quando `ai_backend` acha o Ollama; sem ele o caminho é o NLP, que não
pica. Por isso está em terceiro: pode não afetar a máquina dele. **Conferir
primeiro se o Ollama está instalado lá** antes de gastar uma rodada nisto.

## Linhas mortas — não tentar de novo sem ideia nova

Registrar aqui o que já foi tentado três vezes sem mover o número.

### Portar `fronteira_assunto` da `furia-sync-portable` — MORTA na primeira

Medido em 07/09, `antes-fronteira` e `depois-fronteira`: **número idêntico em
todas as colunas**. O motivo, apurado em vez de suposto:

```
o sinal dispara em                      39 das 382 frases
dessas, as listas de _opens_a_thought
já rejeitavam                           39
o que a pesquisa acrescenta              0
```

A pesquisa foi validada contra 400 trechos julgados por gente (anáfora órfã
100%, conectivo dependente 87,5%) e continua correta. Ela só não acrescenta
nada AQUI, porque as listas que o `clip_selector` já tinha cobrem o mesmo
terreno. Desfeito na hora; o módulo não ficou no repositório.

Não tentar de novo sem material em que as duas discordem.

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
