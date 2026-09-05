# O time — quantos bots, quais, e por quê

Minha recomendação, com o motivo de cada escolha. Vale para o Hermes com modelo
grátis rodando o dia inteiro.

## A recomendação em uma linha

**Dois bots no modelo grátis, com papéis fixos, e o chefe (modelo pago) só
decidindo o que muda.**

Nem três, nem seis, nem "o máximo que a máquina aguentar".

## Por que dois, e não muitos

A ideia de muitos bots supõe que o gargalo é **mão de obra**. Não é. O gargalo é
**julgamento** — e julgamento é exatamente o que o modelo pequeno não tem.

O caso que decidiu isto: pedimos a bateria de testes. O bot respondeu
`19 passed in 0.12s`. A bateria tem 1196. Ele não mentiu; rodou um arquivo e
achou que era tudo. Seis bots fazendo isso produzem seis relatórios confiantes e
errados em vez de um, e alguém tem que conferir os seis.

Um bot que trabalha certo vale mais que cinco que precisam ser auditados.

## Os dois papéis, e o que os separa

A divisão não é por assunto. É por **quem consegue conferir o próprio
trabalho**. Todo trabalho de bot tem que ser verificável por um comando, senão
não é trabalho de bot.

### bot-medidor

Roda comandos e devolve a saída inteira. **Nunca edita código.**

```bash
python scripts/regua.py --material <fonte> --salvar antes-<ideia>
python scripts/regua_vereditos.py
python scripts/aprender.py
python -m pytest -q
python scripts/novo_material.py --sortear
```

Por que é seguro: cada tarefa tem uma resposta certa que a máquina produz. Ele
não precisa julgar nada — precisa não resumir.

### bot-escrevente

Cuida da memória. **Nunca decide direção.**

- escreve as linhas de `inicio` e `fim` em `docs/hermes/turnos.txt`
- mantém o `ESTADO.md` numa página
- escreve a nota de passagem no fim de cada sessão
- procura no cofre se a ideia da vez já foi tentada antes

Por que é seguro: escrever o que aconteceu não exige opinião sobre o que devia
acontecer. E é o trabalho que mais some quando ninguém tem a tarefa explícita.

### o chefe (modelo pago)

Faz a única coisa que os outros dois não podem: **decide o que mudar**, escreve
a previsão antes, e decide se guarda ou desfaz.

Isso gasta pouquíssimo do modelo caro — a decisão é uma frase; o trabalho de
rodar, medir e anotar é tudo dos bots. É exatamente o desenho que ele queria:
bots grátis fazendo as horas, chefe pago fazendo as escolhas.

## As skills, e por que estas cinco

| skill | para quem | o que impede |
|---|---|---|
| `modo-autonomo` | chefe | andar em círculos, mudar duas coisas de uma vez |
| `medir-o-corte` | medidor | achar que melhorou sem número |
| `conferir-antes-de-entregar` | medidor | os "19 de 1196" |
| `nota-de-passagem` | escrevente | perder o trabalho quando o modelo troca |
| `caderno-de-vereditos` | chefe | perder o julgamento do editor |

**Não adicione mais skills.** Skill que ninguém segue é pior que skill que não
existe: ela dá a impressão de que a regra está no sistema. Se faltar alguma
coisa, ela vira uma linha no `ESTADO.md` primeiro; só vira skill quando se
repetir três vezes.

## A configuração

```yaml
delegation:
  model: stepfun/step-3.7-flash:free
  provider: nous
  max_concurrent_children: 2
```

Dois, não três. E note uma coisa importante: **todos os bots usam o mesmo
modelo** — escolher modelo por tarefa não existe no Hermes hoje. Então "dois
bots por modelo grátis" nunca foi possível; a variedade vem do papel, não do
modelo. Na prática dá no mesmo.

## "Às vezes ele só para de responder"

Isto não se resolve na configuração, e é honesto dizer por quê: eu não vejo por
dentro do Hermes. O que dá para fazer é tirar o custo do travamento.

**Um agente que trava não avisa que travou.** Ele simplesmente para de escrever.
Por isso a linha de `fim` no `turnos.txt` importa tanto quanto a de `inicio`: o
silêncio depois de um `inicio` sem `fim` é a única coisa que denuncia.

```
    começaram e não terminaram .... bot-medidor
    silêncio desde a última linha . 73 min                     OLHE ISTO
    Isso é o sintoma de travado. Nada se perdeu.
```

E é o "nada se perdeu" que importa. Com o `ESTADO.md` e a nota de passagem no
disco, um travamento custa **um comando**, não uma noite:

> Você travou. Leia `docs/hermes/ESTADO.md` e a última nota de passagem, e
> recomece do "Próximo passo exato".

Um sistema em que travar é barato vale mais que um sistema que promete não
travar.

## O jeito de rodar, do começo ao fim

```
1.  chefe       lê ESTADO.md, escolhe UMA ideia da fila, escreve a previsão
2.  medidor     régua ANTES, com rótulo
3.  chefe       faz a mudança. Uma só.
4.  medidor     régua DEPOIS, mesma fonte, mesmo rótulo
5.  chefe       subiu -> guarda. Não subiu -> desfaz. Sem discussão.
6.  escrevente  ESTADO.md, turnos.txt, nota de passagem
```

Os passos 2, 4 e 6 são a maior parte do relógio e nenhum token do modelo caro.
Os passos 1, 3 e 5 são três frases.

## O que eu NÃO recomendaria

**Um bot "criativo" que propõe ideias de corte.** Direção editorial vinda de
modelo pequeno é opinião barata que custa caro: alguém vai medir, descobrir que
não presta, e a noite foi embora. A fila de ideias sai do editor e do número da
régua.

**Bot que mexe em código sem medição no meio.** É como o programa fica quebrado
de manhã.

**Aumentar o número de bots para "andar mais rápido".** O que anda rápido é o
laço medir-mudar-medir, e ele é sequencial por natureza: não dá para medir o
depois antes de fazer a mudança.
