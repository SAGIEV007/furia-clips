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
3. Eu ataco `atravessa dois assuntos` enquanto o caderno enche
4. Com 8 vereditos do mesmo defeito, o primeiro peso se move sozinho
5. Com 30, eu reordeno esta fila com o seu padrão na mão em vez do meu palpite
