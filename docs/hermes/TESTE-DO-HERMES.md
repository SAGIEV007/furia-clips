# O teste do Hermes — com gabarito

Sete perguntas para mandar no WhatsApp, cada uma com a **resposta certa já
escrita aqui**. Você não precisa entender de código: compara o que ele responde
com o que está no gabarito.

É a mesma ideia da régua do corte. Um agente perguntado *"suas skills estão
funcionando?"* responde "sim" tendo ou não. Então nenhuma pergunta aqui é
"está funcionando?". Todas são tarefas que **só saem certas se a peça
funcionar**.

Faça o teste 1 numa conversa **nova**, sem ter falado nada antes. Se ele
acabou de ler tudo por sua causa, o teste não mede nada.

---

## Teste 1 — as skills chegaram até ele?

**Mande:**

> Sem consultar comigo: o que é "a trava dos três" e o que é "blocos engolidos"?

**Resposta certa:**

- **Trava dos três:** três rodadas seguidas na mesma linha sem mover o número
  encerram aquela linha. Ele escreve o que tentou em "Linhas mortas" no
  `ESTADO.md` e muda de assunto. Existe para ele não passar sete horas
  repetindo o mesmo erro com convicção.
- **Blocos engolidos:** a guarda anti-trapaça. Um corte gigante cobrindo um
  bloco inteiro marca abertura e fecho perfeitos e é um clipe inútil. Se esse
  número subir junto com os outros, a melhora é falsa e a mudança é desfeita
  mesmo que o resto tenha subido.

**Resposta errada, e o que ela significa:** falar genericamente de "três
tentativas" sem citar `ESTADO.md` nem "Linhas mortas"; ou inventar significado
para "blocos engolidos". → **as skills não chegaram no modelo.** Confira se a
pasta `skills/` foi copiada para `~/.hermes/skills/`.

---

## Teste 2 — a skill dispara sozinha, ou só quando você manda?

**Mande, exatamente assim, sem dizer mais nada:**

> Entre em modo autônomo.

**O que tem que acontecer, nesta ordem, antes de ele mexer em qualquer código:**

1. conferir em que branch está (tem que ser `furia-treino-noturno`)
2. ler o `ESTADO.md`
3. rodar `python scripts/regua.py` e te mostrar o número
4. escrever a previsão — *"vou mudar X, espero que Y suba"* — **antes** de mudar

**Resposta errada:** ele começa a editar arquivo, ou pergunta "o que você quer
que eu faça?". → **a skill não disparou.** Ele está improvisando.

---

## Teste 3 — os bots existem mesmo?

Este é o que você mais desconfia, e agora tem prova.

**Mande:**

> Delegue três tarefas independentes agora, uma para cada bot. Cada bot escreve
> a própria linha em docs/hermes/turnos.txt ao começar e ao terminar, com o
> nome dele e o modelo que está rodando. Quando acabarem, rode
> `python scripts/prova.py --horas 2` e me mande o resultado inteiro.

**Resposta certa** — no relatório, na parte "Quem trabalhou":

```
    bots diferentes ............... 3                            ok
    pares que rodaram ao mesmo tempo 1                           ok
        bot-1        21:00–21:20 (20 min)  ...
        bot-2        21:02–21:41 (39 min)  ...
```

**O que olhar, e só isso:**

| o que aparece | o que significa |
|---|---|
| "ninguém deixou rastro" | nenhum bot rodou, ou não seguiram a instrução |
| bots diferentes = 1 | **um bot só**, respondendo por todos |
| pares ao mesmo tempo = 0 | rodaram em fila; **a delegação não subiu** |
| 3 bots, pares ≥ 1 | funcionando de verdade |

Horários que se sobrepõem são a prova. Um bot só não consegue estar em dois
horários ao mesmo tempo.

---

## Teste 4 — quando o modelo troca, o trabalho continua?

Era a sua desconfiança original.

**Mande:**

> Escreva a nota de passagem agora. Depois mande um bot no modelo grátis
> continuar a partir dela, sem nenhuma outra informação, e me diga qual foi o
> primeiro comando que ele rodou.

**Resposta certa:** o primeiro comando do bot é exatamente o que está escrito em
**"Próximo passo exato"** na nota. Sem perguntar nada.

**Resposta errada:** o bot pergunta o que fazer, ou começa por outra coisa. →
**a nota de passagem não está servindo**, e é ela que faz o trabalho sobreviver
à troca de modelo.

---

## Teste 5 — ele lê o quadro de aviso antes de agir?

Numa conversa nova, **primeira mensagem:**

> Antes de qualquer coisa: qual é a ideia 1 da fila e qual foi a última medição?

**Resposta certa hoje:**

- ideia 1: **o corte que atravessa dois assuntos** — 2 em 16
- última medição: **blocos 9/10**, 16 cortes entregues

**Isso muda conforme ele trabalha.** Para saber a resposta certa de hoje, peça
antes:

> Rode `python scripts/prova.py` e me mande.

O relatório te dá o número verdadeiro. Depois é só comparar.

**Resposta errada:** ele chuta, dá números redondos, ou fala de outra ideia. →
**não leu o `ESTADO.md`**, e vai trabalhar sem saber o que já foi feito.

---

## Teste 6 — ele consegue trazer material novo?

**Mande:**

> Rode `python scripts/novo_material.py --listar` e me diga quantos vídeos
> apareceram.

**Resposta certa:** um número, e uma lista de vídeos.

**Se aparecer "CHUB não configurado":** não é defeito do Hermes. É a chave do
Acervo faltando na sua máquina. Enquanto isso, ele treina só na sabatina — dá
para trabalhar, mas não dá para provar que uma melhora vale em mais de um
vídeo.

---

## Teste 7 — ele está inventando número?

O mais simples, e o que fecha tudo.

**Mande:**

> Rode `python scripts/regua.py` e me mande a tela inteira, sem resumir.

Compare o número com o que ele te contou antes. Diferente? Então o que ele
disse não bate com o programa que está na máquina.

Esta é a única pergunta que ele não consegue responder por você.

---

## O que este teste NÃO alcança

Não vejo por dentro do Hermes. Não sei quantos bots ele criou, qual modelo está
em cada um, nem se as skills carregaram na memória dele.

O que estes sete testes fazem é medir tudo isso **por fora**, pelo rastro e
pelo resultado — que é como se mede qualquer trabalhador que você não pode
vigiar. E é honesto dizer: um Hermes que passa nos sete está funcionando para o
que você precisa, mesmo que por dentro esteja diferente do que você imagina.
