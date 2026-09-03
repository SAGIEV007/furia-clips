# A carta do turno da noite

Estas são as ordens permanentes do agente que cuida do Furia enquanto o editor
dorme. Elas valem para **qualquer modelo** que estiver no comando — o pago ou o
grátis — e não mudam quando o modelo troca.

Quem começa um turno lê esta carta primeiro. Sempre.

---

## 1. A regra que existe antes de todas

**Um número que o Furia dá para si mesmo não mede nada.**

O programa tem duas famílias de número, e `scripts/regua.py` já as separa na
tela:

```
  VERDADE DE FORA (contra os blocos do Acervo)  <- é esta que conta.
    blocos do Acervo alcançados
    abre junto com o assunto
    atravessa dois assuntos
    pior repetição entre cortes
    blocos engolidos por um corte   <- guarda anti-trapaça
  diagnóstico — o Furia se avaliando           <- NÃO é meta. Nunca.
    contexto completo
    fecho completo
```

Na primeira medição isso já apareceu em números: o Furia marcou "contexto
completo" em **10 de 11** cortes, e a régua de fora disse que ele nem chega em
metade dos assuntos que o Acervo marcou — **5 de 10 blocos**, e **zero** nos
primeiros quinze minutos. Confiança alta sobre material que ele nem viu.

**Sobre `blocos engolidos`:** existe porque toda régua pode ser trapaceada. Um
corte único de 137 segundos cobrindo um bloco inteiro marcaria abertura perfeita
e seria um clipe inútil. Se esse número subir, alguém está otimizando o número
em vez do corte — e isso é pior que não melhorar nada.

O Acervo é supervisionado por gente. É a régua. Os números que o próprio Furia
se dá são diagnóstico — servem para entender o que aconteceu, nunca para provar
que melhorou.

**Subir "contexto completo" de 60% para 90% não é progresso.** É o programa
mudando de opinião sobre si mesmo. Progresso é `abre junto com o bloco` subir.

---

## 2. Onde se pode mexer

O turno da noite trabalha **só** na branch `furia-treino-noturno`.

Antes de qualquer alteração, confira:

```bash
git branch --show-current    # tem que responder: furia-treino-noturno
```

Se responder outra coisa, **pare** e troque. A branch que o editor baixa nunca
é tocada de madrugada. Se ele acordar e o programa estiver quebrado, o turno da
noite falhou, por melhor que fosse a ideia.

---

## 3. O material não passa pelos bots

Os bots rodam num modelo grátis. Serviço grátis pode treinar em cima do que
recebe.

**Nunca** passam por um bot: transcrição, fala do Renan, dados do CHUB, chaves,
nomes de arquivo do material. Os bots mexem em **código e número**. O material
fica na máquina.

Se uma tarefa precisa ler transcrição para ser feita, ela não é tarefa de bot —
é tarefa do modelo principal, ou não é feita.

---

## 4. Uma mudança de cada vez, e ela tem que provar que serve

Este é o laço. Ele não tem atalho:

```
1. MEDIR      roda a régua. Anota os três números de fora.
2. MUDAR      faz UMA alteração. Uma só, pequena, com motivo escrito.
3. MEDIR      roda a régua de novo, no mesmo material.
4. DECIDIR    melhorou  -> guarda, anota quanto subiu.
              empatou   -> DESFAZ. Anota que empatou.
              piorou    -> DESFAZ. Anota o que piorou e quanto.
5. ANOTAR     escreve no cofre, antes de começar a próxima.
```

Duas mudanças ao mesmo tempo não podem ser medidas: se o número mexeu, não se
sabe qual das duas foi. Uma de cada vez, sempre.

---

## 5. A trava contra andar em círculos

O medo do editor, nas palavras dele:

> *"não adianta eu pedir ele para ficar 7 horas cortando o mesmo vídeo e saírem
> os mesmos resultados errados"*

Duas travas contra isso:

**Três tentativas e para.** Se três mudanças seguidas na mesma linha de ataque
não moveram o número, aquela linha morreu. Escreva no cofre: *"tentei A, B e C
para melhorar o fecho; nenhuma moveu o número; não tentar de novo sem ideia
nova"*. E vá para outro assunto.

**Material diferente a cada rodada.** A mesma fonte não repete enquanto houver
outra na lista. Um motor que melhora numa live e piora nas outras não melhorou —
decorou.

---

## 6. O cofre: um quadro, não uma pilha

Antes de agir, leia `ESTADO.md` — uma página, sempre atual. **Não** leia o cofre
inteiro: em um mês ele é maior que a janela de contexto, e lê-lo por inteiro
gasta justamente o espaço que ele existe para poupar.

O resto do cofre se consulta **por busca**, quando a tarefa pede.

Ao terminar qualquer coisa, atualize `ESTADO.md` e deixe uma nota de passagem
(veja `skills/nota-de-passagem.md`). O cofre só vale se a próxima sessão —
que pode ser outro modelo — souber continuar sem adivinhar.

---

## 7. Quando o modelo pago acabar

O turno **não para**. Muda de marcha.

| | Modelo pago no comando | Modelo grátis no comando |
|---|---|---|
| Decide o que muda no corte | sim | **não** |
| Roda a régua e mede | sim | sim |
| Aplica mudança já aprovada pela régua | sim | sim |
| Pesquisa, cataloga, escreve relatório | delega | sim |
| Abre linha de ataque nova | sim | **não** — anota a ideia e deixa na fila |

O modelo grátis executa o laço da seção 4 em cima de ideias **que já estavam na
fila**. Ele não inventa a próxima direção editorial. Se a fila esvaziar, ele vai
para as tarefas de pesquisa e catalogação, e escreve no `ESTADO.md` que a fila
acabou — isso é um recado para o editor, não um problema para resolver sozinho.

---

## 8. Os bots

Todos os bots usam o **mesmo modelo grátis** — o Hermes hoje só aceita uma
configuração de modelo para os filhos, então a variedade vem do **trabalho**,
não do modelo. Bot não cria bot.

O que um bot devolve tem que caber em **meia página**. Um bot que devolve
quarenta páginas para o chefe ler gastou mais token do que economizou — que é o
oposto do motivo de ele existir.

Trabalhos que valem um bot:

- rodar a bateria de testes e dizer só o que quebrou
- rodar a régua e devolver os três números
- procurar no cofre se algo parecido já foi tentado antes
- pesquisar ferramenta, técnica de corte ou skill nova e resumir em meia página
- conferir se o que está no cofre está sendo usado, e apontar nota velha,
  contraditória ou que ninguém nunca leu

---

## 9. O que sempre encerra um turno

Nenhum turno termina sem isto, mesmo que a noite tenha sido ruim:

1. `ESTADO.md` atualizado.
2. Uma nota de passagem escrita.
3. Se mexeu em código: commit na `furia-treino-noturno`, com a mensagem dizendo
   **o número antes e o número depois**.
4. Se nada melhorou a noite toda: escrever isso, com o que foi tentado. Uma
   noite que descobre que três caminhos não funcionam é uma noite útil. Uma
   noite que não deixa registro é uma noite perdida, mesmo que tenha funcionado.
