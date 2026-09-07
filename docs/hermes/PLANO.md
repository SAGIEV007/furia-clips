# O plano do Furia, de 07/09 em diante

Escrito depois de uma decisão sua que reorganizou tudo:

> *"Não precisa ser na melhor frase do Renan, APENAS se o que ele falar no corte
> tiver sentido completo, e se for uma pergunta curta do repórter não tem
> problema mostrar."*

## O que essa frase mudou

Eu vinha perseguindo o número errado. A régua tinha `abre junto com o assunto`
como meta — quantos cortes começam exatamente na borda do bloco. Você acabou de
dizer que isso não importa.

E não é detalhe: se o motor fosse otimizado para aquele número, ele iria para o
**lado errado**. Um corte que abre quarenta segundos dentro do assunto e tem
sentido completo é bom. Um que abre exatamente na borda e fica pela metade é
ruim. Aquele número não distingue os dois.

Já corrigido: saiu da meta, virou referência.

## O alvo, agora com nome

**Sentido completo.** Um corte em que o que o Renan fala se sustenta sozinho.

E aqui está o problema mais importante deste documento: **o Furia já diz que faz
isso.** Ele marca "contexto completo" em 14 de 16 e "fecho completo" em 16 de
16. Se esses números valessem, não haveria nada a consertar.

Eles não valem — porque é o programa se avaliando. A única pessoa que sabe se um
corte tem sentido completo é você. Isso não é limitação temporária: é o formato
do problema. Nenhuma medição interna vai resolver.

**Consequência para o plano inteiro:** o caminho principal daqui para frente não
é uma ideia técnica minha. É o seu julgamento entrando no motor.

---

## As três frentes, em ordem de tamanho do ganho

### 1. Encher o caderno — é a frente principal

Hoje: **zero** vereditos. O sistema de aprendizado está pronto, testado e
ligado, e não tem o que comer.

O que fazer: usar o Furia normalmente e **apertar Aprovar ou Rejeitar em todo
corte**, escolhendo o motivo na lista. Nada além disso.

| marco | o que destrava |
|---|---|
| 8 do mesmo defeito | o primeiro peso do motor se move sozinho |
| ~30 vereditos | dá para ver o seu padrão em vez de casos isolados |
| 10 aprovados + 10 rejeitados | destrava os dois testes parados de headline |

**Por que isto vem antes de tudo:** cada uma das outras frentes precisa saber o
que "bom" quer dizer para você. Sem o caderno, eu continuo consertando o que
**eu** acho que está errado — e hoje mesmo isso me custou uma tentativa inteira.

### 2. O corte que atravessa dois assuntos — 2 em 16

Esta continua valendo mesmo sem o caderno, porque um corte que pisa em dois
assuntos **não pode** ter sentido completo. É medível de fora, é objetivo, e
está diretamente a serviço do seu alvo.

O caso concreto: o corte de 1742,3 a 1773,4 pisa no bloco 8 (prefeitos e
reeleição) e no bloco 9 (privatizações).

A pista: o Furia lê a sabatina em **8** blocos temáticos próprios; o Acervo
marca **10**. A travessia acontece onde as duas leituras discordam. Comparar as
duas divisões e ver onde se afastam.

Alvo: `atravessa dois assuntos` chegar a 0/16.

### 3. Régua para as lives recentes

Hoje só a sabatina e mais dois vídeos do Acervo têm gabarito. A live de ontem
não tem nenhum — e é nela que você trabalha.

O conserto já está pronto e depende de você anotar, por vídeo, uns cinco cortes
seus:

```
~/FuriaClipsData/cortes_do_editor/setembro.txt
2026-09-07 14:02 | ID_DO_VIDEO | 754 | 812 | a headline que você usou
```

Depois:

```bash
python scripts/aprender.py --gabarito ID_DO_VIDEO
python scripts/regua.py --material tests/fixtures/editor_ID_DO_VIDEO.json
```

**Cinco cortes seus dão régua a um vídeo que nenhum catálogo cobre.** É a coisa
de maior alavancagem que existe hoje, e é a única que ainda pede digitação.

---

## O que a pesquisa dos geradores de shorts acrescentou (07/09)

Ele mandou vídeos e pediu para eu pesquisar os geradores famosos do GitHub.
Duas categorias, e só uma interessa:

**Os "faceless" — DarkPlanner, AutoShorts.ai, Syllaby, Sendshort.** Geram vídeo
do ZERO: roteiro de IA, voz sintética, imagem de banco. Não cortam vídeo de
ninguém. Categoria errada para o Renan.

**Os cortadores — Opus Clip, Klap, e os clones abertos** (o maior é o
`AI-Youtube-Shorts-Generator`, 4,8 mil estrelas). Esses fazem o que o Furia faz.

Comparado item por item, **eles não têm nada que o Furia não tenha**:

| | eles | Furia |
|---|---|---|
| word timestamps do Whisper | sim | sim, ligado por padrão |
| corte vertical seguindo o rosto | sim | `face_tracker` + `layout_planner`, ligados |
| legenda queimada | sim | `caption_lexicon`, ligado |
| dedup por sobreposição | >50% | mais apertado |
| régua de fora | **não** | Acervo do CHUB |
| aprende com o editor | **não** | caderno de vereditos |
| sabe quem está falando | **não** | Renan vs jornalista |

E como eles escolhem o corte: mandam a transcrição para um LLM e perguntam
"quais são os momentos virais". Isso é uma opinião sem como conferir — é
exatamente o problema que a régua existe para resolver. Além disso mandaria a
fala do Renan para um terceiro, o que a regra de dados proíbe.

**O único achado técnico aproveitável** é a técnica, não a ferramenta: eles
picam vídeo longo em janelas **com sobreposição**, para não perder um momento
que cai bem na emenda. O Furia pica em janelas de 25 blocos **sem
sobreposição** (`_select_with_llm`, linha ~1565). Vale só quando o Ollama está
instalado — sem ele o caminho é o NLP, que não pica. Anotado na fila.

Conclusão para o planejamento: **não muda nada.** O plano continua sendo encher
o caderno, porque o que separa o Furia dessas ferramentas já é a régua e o
aprendizado — e as duas coisas estão esperando o julgamento dele, não código
novo.

## A pergunta dele que mudou o plano (07/09, mais tarde)

> *"os padrões do chub não são o suficiente? (...) até um vídeo que nem estava
> no chub pode ser interpretado e transformado em blocos através de sumarização
> (...) além de eu enviar cortes prontos (...) através dos cortes do Renan que
> já estão no Instagram"*

Três pontos. Ele acertou em dois, e o terceiro eu testei e achei o obstáculo.

### 1. "Interpretar um vídeo que não está no CHUB em blocos" — o Furia JÁ FAZ

E a prova estava na própria régua, escrita e não lida: **o Furia lê a sabatina
em 8 blocos temáticos próprios; o Acervo marca 10.** Ele nunca precisou do CHUB
para segmentar — `editorial_block.py` e `editorial_chapters.py` fazem isso na
live de ontem igual.

Eu tinha tratado a ideia 1 (`atravessa dois assuntos`) como "consertar 2 de 16".
**Errado, e o erro é de tamanho.** Aqueles 8 contra 10 são a medida de quão bem
a leitura própria do Furia substitui o CHUB num vídeo que o CHUB nunca viu. É a
mesma coisa que o problema da live recente, e dá para medir hoje.

A ideia 1 sobe de importância por causa da pergunta dele.

### 2. Os cortes publicados no Instagram — a maior fonte disponível

Testado de ponta a ponta com dados reais, e o resultado tem duas metades.

**O que NÃO funciona: recuperar o começo e o fim no vídeo longo.**

Peguei o corte mais visto (9,1 M) e procurei o texto dele na sabatina. Não bate.
Procurei no Acervo: **78 blocos, em pelo menos quatro vídeos diferentes**, com o
mesmo argumento e palavras diferentes a cada vez. O Renan repete as teses dele.

A busca acha o **argumento**, não a **gravação**. Alinhar automático atribuiria o
corte ao vídeo errado, e gabarito com hora errada é pior que gabarito nenhum —
ensinaria o motor a cortar no lugar errado com confiança.

**O que funciona, e é muito: a FORMA do corte publicado, que não precisa de
alinhamento nenhum.** Medido em três dos mais vistos:

| | duração | como abre | como fecha |
|---|---|---|---|
| 9,1 M "Que Brasil vou pegar" | ~92 s | **pergunta do repórter, 1,5 s** | conclusão fechada |
| 5,9 M "propaganda do PT" | ~127 s | cena + tese em 7 s | assinatura |
| 5,8 M "Lula há 30 anos" | ~52 s | tese direta | frase de soco |

Três coisas que isso já mostra, e nenhuma delas é palpite meu:

- **Duração publicada: 52 a 127 s.** Vale conferir contra o teto do Furia.
- **Abrir na pergunta curta do repórter é padrão de campeão**, não exceção — o
  mais visto de todos faz isso, com 1,5 s de pergunta. Confirma a regra dele.
- **A legenda do post é uma frase do próprio corte, ou a pergunta que o abre.**
  Isso é evidência de headline, que é justamente um dos dois testes parados.

São **5.339 cortes publicados** com transcrição disponível. É a maior fonte de
"como é um corte pronto do Renan" que existe, ela não exige que ele digite nada,
e é verdade de fora (NORTE §15): quem publicou foi a equipe, não o programa.

### 3. Os cortes que ele mesmo manda — continuam valendo

Esses têm o que os publicados não têm: **ele sabe de qual vídeo e de que hora**.
Cinco por vídeo dão régua de tempo. Os publicados dão régua de forma. As duas
juntas cobrem o que faltava.

## A auditoria do CHUB e o fio solto (07/09, cobrado por ele)

Detalhes em `CHUB-AUDITORIA.md`. O essencial:

**Uma correção minha.** Escrevi que "o Furia lê em 8 blocos, o Acervo marca 10",
e ele leu como "acertou 8 de 10". Não é. `assuntos alcançados` é **9 de 10**,
medido. O "8" é só em quantos pedaços o Furia divide o vídeo — granularidade,
não nota. Nunca medi se aqueles 8 caem nos mesmos lugares. Não repito mais.

**O defeito que a pergunta dele achou.** Ele perguntou se o Furia não deveria
estar SEMPRE usando o CHUB. Deveria, e não estava — por um fio solto, não por
decisão. `find_snapshot_for` procurava o Acervo no disco; `ChubClient.exportar`
sabia buscar. Entre as duas, nada. Sem o arquivo baixado antes à mão, a moagem
seguia cega **mesmo com o vídeo publicado no Acervo e a chave configurada**.
Mesmo formato do erro dos pesos do CHUB: a capacidade existia, a ligação não.
**Consertado** — `buscar_no_acervo_se_faltar` busca na hora da moagem.

**Das 18 ferramentas do CHUB, o Furia usava 2. Agora usa 4.** As outras 14 são
"não" **certo**: desempenho por tema, audiência, dossiê municipal e Livro
Amarelo dizem sobre o que FALAR — pauta, não corte. O Furia não escolhe assunto;
corta o que já foi falado.

## A terceira régua, construída (07/09)

`python scripts/regua_publicados.py`

Ela já achou uma diferença de verdade, medida em três dos mais vistos:

```
  A FORMA DO QUE FOI PUBLICADO  (3 cortes da equipe)
    duração ....................... 52s a 127s   ·   meio: 92s
    abrem em quem não é o Renan ...   1/3
      dessas, abertura curta ......   1      (até 8s — o que você liberou)
    fecham em frase terminada .....   3/3

  O QUE O FURIA ENTREGA  (16 cortes · sabatina)
    duração ....................... 16s a 79s   ·   meio: 52s

    Os cortes do Furia são MAIS CURTOS que os publicados:
    52s contra 92s no meio da faixa.
```

**O corte mais curto do Furia tem 16 s; o mais curto publicado tem 52 s.** Isso
é evidência de fora, não opinião minha, e vai para a fila com medição antes e
depois.

## A raiz, medida no fim do dia 07/09

Ele perguntou se o planejamento já estava todo feito. Não estava: faltava a
parte do motor, que é minha. Fui fazer a ideia 1 e ela virou outra coisa.

**Tentei o conserto óbvio e ele não podia funcionar.** As duas travessias são
sobras pequenas de cauda (5,8 s e 8,3 s). Escrevi a apara, medi: nada mudou —
porque a apara **nunca dispara**. O Furia não vê aquelas fronteiras. Desfeito.

**O que a medição achou é a raiz de quase tudo:**

```
    viradas de assunto achadas ....   1/9     11%
    maior pedaço que o Furia vê ...      357s
    maior bloco do gabarito .......      368s
```

Das nove viradas de assunto da sabatina, **a leitura própria do Furia acha uma**.
Ele enxerga um pedaço de 357 segundos onde o Acervo marca três assuntos.

E é a resposta à pergunta dele sobre o CHUB: **num vídeo catalogado essa falha
fica escondida**, porque os blocos revisados cobrem. **Na live de ontem não há o
que cobrir.** Por isso "usar sempre o CHUB" ajuda e não basta.

Nova régua para isso: `python scripts/regua_assuntos.py`.

**O cuidado que vale mais que a ideia:** não usar a borda do Acervo para cortar
e depois medir contra a borda do Acervo. O gabarito não pode ser a entrada — o
número subiria sem o corte melhorar, e a régua estaria conferindo a própria cola.

## A pesquisa das ferramentas que ele pediu (07/09, fim do dia)

> "quero uma pesquisa aprofundada nas melhores ferramentas possíveis que fazem
>  isso sejam as pagas ou as gratuitas e um planejamento muito bom para fazermos
>  isso com qualidade, mas como não sei programar quero ter certeza disso"

Fui olhar o que as ferramentas famosas fazem, o que a pesquisa acadêmica diz, e
o que dessas duas coisas serve **aqui**, num programa que roda sem internet num
notebook de 1366×768.

### O que as ferramentas pagas realmente fazem

| ferramenta | como decide onde cortar | serve para nós? |
|---|---|---|
| **Opus Clip** | lê fala, imagem, som e emoção juntos; dá uma nota de viralidade de 0 a 100 | **não** — manda o vídeo para o servidor deles |
| **Vizard** | lê a transcrição, mais detecção de cena e de quem está falando | **não** — mesma coisa, e não tem nota |
| **Klap** | corte e legenda bonitos; a escolha do trecho é o ponto mais fraco | não |
| **Descript / Riverside** | o humano corta o texto, o vídeo acompanha | não |

**A conclusão que interessa é uma só, e vale mais que a tabela:** nenhuma delas
inventou um jeito melhor de achar onde o assunto vira. Todas fazem a mesma
coisa — **um modelo de linguagem grande lê a transcrição inteira e diz quais
trechos valem**. A inteligência está no modelo, não no algoritmo.

E isso é exatamente o que **não** dá para fazer aqui, por três motivos que já
estão escritos no projeto: o material do Renan não sai desta máquina, o programa
precisa funcionar sem internet, e modelo de graça treina em cima do que você
manda.

### O que a pesquisa acadêmica diz

O caminho que o Furia usa — medir se as palavras dos dois lados de um ponto se
parecem, e cortar no vale — é o **TextTiling**, de 1997. Ainda é a base de tudo.
O que mudou desde então, e que dá para aproveitar:

1. **Trocar contagem de palavra por peso de palavra rara.** Foi o que fiz hoje
   (o `idf`): +6 pontos de precisão, custo zero.
2. **Trocar a comparação de palavras por comparação de sentido.** É o único
   ganho grande que a literatura documenta — um trabalho de 2021 que fez isso em
   transcrição de reunião mediu **15,5% menos erro**. Explicado abaixo, porque é
   a próxima frente.
3. **Medir a fundura do vale em vez do valor absoluto.** Testei hoje. **Não
   funcionou aqui** — 7 de 39 contra 25 de 39. Está registrado como linha morta.
4. **Usar quem está falando.** A literatura mal menciona; foi o que mais rendeu
   aqui (18% → 30%), porque o material desta casa é entrevista.

### A próxima frente: o Furia comparar SENTIDO, não palavra

Hoje o Furia compara **as palavras** dos dois lados de um ponto. Se antes ele
fala em "reforma tributária" e depois em "imposto de renda", as palavras são
diferentes e o programa acha que o assunto virou — quando não virou. E se ele
fala em "segurança" antes e depois, mas de coisas diferentes, o programa acha
que continua o mesmo.

Comparar **sentido** resolve os dois casos. Isso é feito por um arquivo que
traduz frase em número de um jeito que frases parecidas ficam com números
parecidos. Roda na máquina, sem internet, depois de baixado uma vez.

**O que eu conferi, e é a parte que te dá certeza:**

- O motor que roda esse arquivo (`onnxruntime`) **já está instalado no Furia** —
  veio junto com o Whisper, que é o que transcreve. Não precisa instalar nada
  novo, não precisa de placa de vídeo.
- O arquivo em si tem **cerca de 130 MB**, baixa uma vez e fica.
- Depois de baixado, funciona **sem internet para sempre**.

**O que eu NÃO posso te garantir ainda, e não vou fingir que posso:** o quanto
isso melhora o número. A máquina onde eu trabalho tem o download desse arquivo
bloqueado, então não consegui medir. Os 15,5% são de um trabalho publicado sobre
reunião gravada, não sobre entrevista do Renan.

Por isso a frente é feita **nesta ordem**, e não em outra:

1. Eu escrevo o código e um **botão** na tela: "baixar a leitura de sentido".
2. Você aperta o botão uma vez, na sua máquina.
3. Você roda `python scripts/regua_assuntos.py` antes e depois.
4. **Se o número não subir, a gente desliga o botão e apaga o arquivo.** Fica
   registrado como linha morta, igual às outras quatro de hoje.

Nada disso muda o Furia enquanto o número não subir na sua máquina. É a mesma
regra do dia inteiro: só entra o que a régua aprova.

## O que NÃO vou fazer, e por quê

**Não vou perseguir `abre junto com o assunto`.** Você decidiu; o número saiu da
meta.

**Não vou mexer em nada com menos de 8 casos.** Com três reprovações o motor
passa a perseguir o seu último clipe rejeitado em vez do seu padrão, e você o
veria piorar justamente por estar "aprendendo".

**Não vou inventar ideia editorial nova enquanto o caderno estiver vazio.** Hoje
tentei portar uma pesquisa validada em 400 trechos, medi, e ela mudou
**exatamente zero** — porque o programa já cobria aquele terreno. Uma tentativa
inteira consumida por eu ter suposto onde estava o defeito em vez de perguntar a
você. Com o caderno cheio, esse tipo de aposta cega acaba.

**Não vou ligar bot grátis nisso agora.** Você tirou o Hermes por ora e está
certo: o gargalo é julgamento, e essa parte é sua.

---

## O que já está pronto e funcionando

| ferramenta | serve para | precisa de quê |
|---|---|---|
| botões Aprovar/Rejeitar | ensinar o motor | só apertar |
| `aprender.py` | ver o que seu julgamento corrigiu | nada |
| `aprender.py --onde` | achar os arquivos, e a dica dos dois notebooks | nada |
| `aprender.py --regua` | saber se um vídeo tem gabarito, e de quem | nada |
| `aprender.py --gabarito <id>` | seus cortes viram régua | anotar 5 cortes |
| `regua.py` | medir contra o Acervo | nada |
| `regua_vereditos.py` | medir contra o seu julgamento | o caderno |
| Enviar/Restaurar feedback | os dois notebooks | nada |

O que já foi consertado e não se reabre: as duas moagens simultâneas; o botão de
parar mirando o trabalho errado; a nota descontando quando o corte abre no
apresentador; a pergunta longa aparada (**a curta, até 8 s, entra — como você
pediu**); os pesos medidos do CHUB entrando na nota; a peneira de entrevista que
descartava os primeiros onze minutos.

## O que continua travado em você

- **A chave do CHUB** foi commitada num repositório público. Só quem opera o
  CHUB pode trocá-la — apagar do código não resolve, o histórico guarda.
- **Legendas e headline** não entram no aprendizado até o caderno ter exemplos.

## A ordem, se for para escolher uma coisa por vez

1. Revisar uma live com os botões — **começa hoje, custa nada**
2. Anotar cinco cortes seus daquela live
3. Eu monto o botão da leitura de sentido; **você mede na sua máquina** e ele só
   fica se o número subir
4. Com 8 vereditos do mesmo defeito, o primeiro peso se move sozinho
5. Com 30, eu reordeno esta fila com o seu padrão na mão em vez do meu palpite

**Por que a 1 continua na frente da 3, mesmo a 3 sendo a mais interessante:** o
que a régua mede é se o Furia acha a virada de assunto. O que ela **não** mede é
se o corte tem sentido completo — e isso é a coisa que você mais pediu, desde o
começo. Nenhum número que o Furia dá sobre si mesmo prova isso. Só o caderno.

## Onde o CHUB entrou de vez (07/09)

Ele perguntou três vezes, de jeitos diferentes:

> "o fúria não deveria estar SEMPRE usando o chub? mesmo de régua?"

Agora tem resposta com número, e não é opinião. As marcas de quem está falando —
que hoje valem 11 pontos de precisão — vêm do CHUB ou de arquivo de legenda. O
Whisper rodando na máquina **não produz nenhuma**:

```
vídeo com as marcas (CHUB) ......  22/39 achadas 56%  |  22/74   certeiras 30%
vídeo sem as marcas (só Whisper)   24/39 achadas 62%  |  25/133  certeiras 19%
```

Sem CHUB o programa não quebra — volta a errar mais. **Com CHUB ele erra
menos.** É por isso que vale sempre buscar o vídeo no Acervo antes de moer, e é
por isso que `buscar_no_acervo_se_faltar` foi ligado ao botão de moer.
