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
| Material de comparação | mais 4 fixtures `acervo_*.json`: 2 entrevistas inteiras e 2 lives. **Medir sempre em mais de uma** — a sabatina é edição de melhores momentos e sozinha engana. |
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

**Conferido em três materiais, não em um** (a primeira medição foi só na
sabatina, e isso não bastava):

```
material              achadas          certeiras (anti-chute)
                    antes  depois       antes    depois
inteligência_1607    0/4     2/4         0/7      2/22
live_ceara           0/4     0/4         0/1      0/1
sabatina_band        1/9     3/9         1/7      3/20
```

A precisão **não caiu** — é isso que separa a melhora do chute. Se eu tivesse
só proposto mais fronteiras, ela desabaria.

### CORREÇÃO (mesmo dia, com material novo do Garimpo)

**Eu disse que "o Furia é quase cego para virada de assunto". Isso era da
FONTE, não do programa.** A sabatina do gabarito é um "MELHORES MOMENTOS" — a
edição tirou as perguntas do jornalista. Medir só nela me deu uma conclusão
geral a partir de um caso particular.

Trazidas duas entrevistas inteiras do Acervo, com as perguntas no lugar:

```
material              formato             coesão            turno do jornalista
sabatina_band         melhores momentos   3/9  de 20 prop    2/9  de  9 prop
bYi5Xhrv5ps           entrevista CNN      6/8  de 23 prop    7/8  de 14 prop
p5ZRVXBpBYk           conversa 68 min    10/14 de 50 prop    3/14 de 10 prop
live_ceara            live                0/4  de  0 prop    1/4  de  2 prop
inteligencia_1607     live                2/4  de 22 prop    0/4  de  1 prop
```

**Numa entrevista de verdade a leitura própria acha 71% a 75% das viradas.**
Não é cegueira; é uma fonte editada que engana a medição.

### Os dois sinais se revezam, e nenhum ganha sempre

- **Entrevista CNN:** o turno do jornalista ganha — 7/8 propondo só 14 (metade
  das propostas certeiras), contra 6/8 propondo 23.
- **Conversa de 68 min:** a coesão ganha — 10/14 contra 3/14.
- **Live:** os dois fracassam, e **é o formato dele.**

Isso mata a ideia de trocar um sinal pelo outro. O caminho é usar os dois e
deixar a fonte decidir qual pesa mais — com medição, não com palpite.

### O que continua ruim, e é muito

- **Só 9% a 15% das fronteiras propostas são reais.** O sinal (coesão lexical
  numa janela de 6 frases) é fraco para este material.
- **6 das 9 viradas nem aparecem como candidatas** — não perdem disputa, a curva
  não desce ali. Afrouxar o limiar só cria fronteira falsa; medido.
- ~~A live do Ceará vira UM pedaço só~~ **RESOLVIDO em 07/09.** Era o limite
  ficando negativo (ver abaixo). Foi de **0/4 para 4/4**.
- ~~A precisão continua baixa em tudo~~ **MELHOROU em 07/09, de 18% para 40%**,
  em três passos medidos um a um (abaixo). Continua sendo o número mais baixo
  do quadro e o alvo da frente seguinte.

### O dia inteiro numa tabela

```
                                        achadas          certeiras     propostas
como amanheceu                          25/39   64%      26/143  18%      143
+ porta da troca de voz                 22/39   56%      22/74   30%       74
+ idf e plural na curva de coesão       26/39   67%      26/73   36%       73
+ piso do pedaço em 30 s (era 15 s)     25/39   64%      25/63   40%       63
```

**Mesmo alcance do começo do dia, com 63 fronteiras propostas no lugar de 143.**
A régua principal não mudou em nenhum dos três passos: 9/10 assuntos, 2/16
atravessa, 18% de repetição, 1 engolido.

### RESOLVIDO em parte — a porta da troca de voz levou a precisão de 18% a 30%

A regra de escolha não era o problema. Ordenar os candidatos por **vale mais
fundo** — a medida clássica do TextTiling, `_profundidade_do_vale` — em vez de
coesão mais baixa acertou praticamente o mesmo: 7/39 com 23% contra 25/39 com
18%. Ou seja, a profundidade quase não separa vale verdadeiro de falso.

O que separa estava no arquivo o tempo todo:

```
34 das 39 viradas de assunto (87%) caem a menos de 15 s de uma troca de locutor
```

A troca sozinha não serve de fronteira — são 395 trocas para 39 viradas — mas
serve de **porta**: só é candidato o vale que cai em cima de uma. Medido nas
cinco fontes:

```
                              achadas          certeiras
antes                         25/39   64%      26/143   18%
depois (porta de 5 s)         22/39   56%      22/74    30%
```

Custa oito pontos de alcance e devolve doze de precisão. É a troca certa para
quem edita: fronteira errada vira corte jogado fora; fronteira perdida vira só
um bloco mais longo, que o seletor ainda corta por dentro.

### RESOLVIDO — a palavra que aparece em tudo pesava igual à que aparece em três

A curva de coesão contava palavra por palavra, com uma lista de stopwords
escrita à mão. A lista acerta o óbvio ("que", "para") e erra o que só é óbvio
dentro do material: numa entrevista sobre o Brasil, "brasil" está em toda frase
e não separa nada.

O `idf` mede isso em vez de adivinhar — cada palavra pesa pelo inverso de em
quantas frases ela aparece, calculado dentro do próprio vídeo. Junto com juntar
plural ao singular (só plural, só em palavra de seis letras ou mais):

```
antes    22/39 achadas 56%   22/74 certeiras 30%
depois   26/39 achadas 67%   26/73 certeiras 36%
```

As duas colunas subiram e nenhuma das cinco fontes piorou. A lista de stopwords
continua valendo — tirá-la custou cinco pontos de alcance.

### RESOLVIDO — o piso de 15 s era um número errado escrito com confiança

Estava no código que "os blocos do Acervo vão de 15 s a uns 12 minutos". A
primeira metade não se sustenta. Contados os 44 blocos das cinco fontes:

```
menor 34 s · décimo percentil 78 s · mediana 220 s · maior 644 s
blocos abaixo de 30 s: NENHUM
```

O piso de 15 s abria espaço para "assunto" de meio minuto que o Acervo nunca
produz, e cada um era fronteira falsa. Com 30 s — logo abaixo do menor bloco já
visto, com folga — a precisão foi de 36% para 40%.

### E ISSO RESPONDE A PERGUNTA DELE SOBRE O CHUB, COM NÚMERO

> "o fúria não deveria estar SEMPRE usando o chub? mesmo de régua?"

Sim, e agora dá para dizer por quê. As marcas de troca de voz vêm do CHUB
(`speakerChange`) ou de arquivo de legenda com `>>`. O Whisper rodando na
máquina **não produz nenhuma**. Medido, com as marcas apagadas de propósito
para simular o vídeo transcrito na máquina:

```
com marca do arquivo (CHUB/legenda) .... 22/39  56%  |  22/74   30%
sem marca nenhuma (Whisper local) ...... 24/39  62%  |  25/133  19%
```

Sem CHUB o programa não fica quebrado — fica com a precisão de antes. **O CHUB
vale 11 pontos de precisão**, e essa é a resposta medida à pergunta.

### RESOLVIDO — o limite que ficava negativo, e a live virava um bloco só

`média − desvio` supõe que a coesão varia pouco em torno da média. Numa
entrevista vale. Numa live o Renan fala sozinho por horas, a curva tem muitos
pontos de coesão zero, **o desvio fica maior que a média e o limite vira
negativo**:

```
material            média  desvio   limite
live_ceara          0,093  0,100   −0,007   <- nada podia passar, nunca
entrevista CNN      0,116  0,080   +0,036
sabatina            0,127  0,084   +0,042
```

Coesão não é negativa, então nenhum ponto passava: as duas horas viravam UM
bloco. Não era sinal fraco — era uma conta que quebra em material longo e
monológico. Terceiro defeito mecânico da mesma família achado hoje.

O conserto é um piso no décimo percentil da própria curva — alcançável por
definição, sem número mágico. Medido nas cinco fontes:

```
                     ANTES              DEPOIS
live_ceara           0/4    0%          4/4   100%
bYi5Xhrv5ps          6/8   75%          6/8    75%   idêntico
inteligencia_1607    2/4   50%          2/4    50%   idêntico
p5ZRVXBpBYk         10/14  71%         10/14   71%   idêntico
sabatina_band        3/9   33%          3/9    33%   idêntico
```

A régua do Acervo também não se mexeu (9/10, 2/16, 18%, 1 engolido). Travado
por teste: sem o piso, a live volta a 0/4 sem nenhum erro aparecer na tela.
- **O turno do jornalista salva numa entrevista e não salva numa live.** Medido:
  7/8 na CNN, 0/4 na live da inteligência. Era hipótese; agora é número.

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

### O silêncio longo entre frases — MORTA, o dado não existe

Estava no prompt que o Google sugeriu ao editor: "pausas longas indicam virada
de assunto". Medido nas cinco fontes:

```
silêncio >= 0,5 s entre o fim de uma frase e o começo da próxima:  0 ocorrências
```

Zero, em todas. As transcrições do Acervo são contíguas — o fim de cada frase é
o começo da seguinte, por construção. Não é sinal fraco: **o dado não está no
arquivo.** Só volta a valer se algum dia entrar detecção de silêncio no áudio,
que é outra máquina de medir.

### Deduzir a troca de voz do texto quando não há diarização — MORTA

Tentativa de estender a porta ao vídeo transcrito na máquina, usando
`is_interviewer_sentence` (quem faz pergunta é outro locutor) no lugar da marca
do arquivo. Medido:

```
marca do arquivo ........  22/39  56%  |  22/74  30%
marca do texto ..........   7/39  18%  |   7/31  23%
```

Acha poucas marcas — de 1 a 20 num vídeo inteiro, contra 28 a 172 do arquivo —
e o alcance desaba. Não substitui. Só volta a valer com diarização de verdade
rodando na máquina.

### Ordenar por vale mais fundo (profundidade do TextTiling) — MORTA

7/39 achadas com 23% de precisão, contra 25/39 com 18% da ordem por coesão
crua. A função ficou no repositório (`_profundidade_do_vale`) com o número
escrito, para ninguém tentar de novo achando que é ideia nova.

### Forçar uma virada a cada 2–3 minutos — MORTA antes de tentar

Também do prompt do Google. Numa live de 234 minutos isso proporia ~117
fronteiras para achar 4. A conta já diz o resultado; não precisou medir.

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

## RESOLVIDO — o botão dos dois notebooks nunca tinha funcionado

Ele perguntou: *"eu uso dois notebooks (...) o arquivo de resultados de
aprovados e rejeitados não é compartilhado, não sei se é bem utilizado para
treinar e não sei nem se o fúria ou você o usam"*.

Conferido item por item:

| a pergunta dele | a resposta, conferida no código |
|---|---|
| é salvo? | sim — `~/FuriaClipsData/database/editorial_learning.sqlite3` |
| é usado para treinar? | sim, a ligação existe: botão → sqlite → `aprendizado.ajustes()` → `EditorialRanker._peso()` → a nota de cada corte |
| eu uso? | sim, `regua_vereditos.py` — a régua do alvo de verdade |
| muda alguma coisa hoje? | **não**: 0 vereditos, 0 cortes dele, `ajustes()` devolve `{}` |
| vai de um notebook ao outro? | **NÃO IA** — era um defeito, agora consertado |

**O defeito:** `repository_sync._branch()` devolvia `manus/rebuild-opus-parity`,
escrito à mão numa época em que era essa a branch entregue. Ele baixa
`claude/repo-access-commits-...`, e `push_feedback_snapshot` recusa quando as
duas não batem:

```
"O checkout está na branch 'claude/...', não em 'manus/...'."
```

Apertar **"Enviar feedback ao GitHub" sempre deu erro**, desde que o nome da
branch entregue mudou. A prova: `data/editorial_feedback_snapshot.json` nunca
chegou a existir no repositório.

Agora a branch é a que o checkout está usando, seja qual for o nome dela.
`FURIA_GIT_BRANCH` continua mandando mais; o nome fixo virou só reserva para
checkout solto num commit. Três testes travam isso.

**O que vai no arquivo compartilhado** (conferido em `build_feedback_snapshot`):
chave do corte, início, fim, duração, nota, aprovado/rejeitado, motivo,
etiquetas e data. **Nenhuma transcrição, nenhum caminho de arquivo, nenhum
vídeo.** É seguro mesmo num repositório público.

### E o teste que provou, porque ele desconfiou

> "pode testar você mesmo se está funcionando? porque apesar do fúria ter a
>  função de 'se atualizar' isso nunca funcionou então acho difícil"

`tests/test_os_dois_notebooks.py` monta um repositório bare local no lugar do
GitHub, dois checkouts no lugar dos dois notebooks, e roda `push` e `pull` **de
git de verdade**. O que se confere no fim é o banco do segundo notebook, lido
direto — não o que a função disse sobre si mesma.

**Por que os testes que já existiam não pegaram o defeito:**
`tests/test_repository_sync.py` falsifica o `git` com `patch`, e um `git` de
mentira aceita qualquer branch. O esquema do banco também é criado pelo próprio
`init_db`, pela mesma razão: esquema escrito à mão aceita coisa que o de verdade
recusa.

Achou mais um defeito no caminho: **apertar o botão duas vezes criava um commit
vazio.** `push_feedback_snapshot` tem um caminho para "já estava sincronizado"
que nunca era alcançado, porque `generated_at` mudava a cada escrita e o git
sempre via mudança. Agora, se as decisões são as mesmas, o arquivo fica como
está.

### O Furia NÃO tem função de se atualizar sozinho — nunca teve

Ele disse que "a função de se atualizar nunca funcionou". Conferido: **ela não
existe.** A rota `/api/repository/sync` aceita três ações — `check`,
`push_feedback` e `restore_feedback` — e nenhuma delas baixa versão nova. A tela
só **avisa** se há atualização; quem atualiza é ele, baixando como já faz.

Não é defeito escondido, é função que nunca foi escrita. Se for para existir,
tem que ser decisão dele: um `git pull` automático na máquina de quem edita pode
derrubar trabalho local sem avisar.

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
