---
name: modo-autonomo
description: O ciclo completo do Furia trabalhando sozinho, a qualquer hora — traz material novo do Acervo, mede, muda uma coisa, mede de novo, desfaz o que não melhorou, e aprende com os cortes que o editor aprovou. Use quando pedirem para treinar, testar, melhorar, calibrar ou "ficar trabalhando" no Furia sem supervisão.
---

# Modo autônomo

Leia `docs/hermes/CARTA.md` antes. Ela manda mais que esta skill.

Isto não é só para a madrugada. É para qualquer momento em que o editor mandar
trabalhar sozinho — de manhã, à tarde, por três horas ou por sete.

O ciclo tem quatro partes, e a ordem importa:

```
   1. TRAZER MATERIAL   ->  2. MEDIR E CORRIGIR
          ^                        |
          |                        v
   4. RELATAR          <-  3. APRENDER COM O EDITOR
```

---

## O rastro — obrigatório para todo agente, chefe e bots

**Todo agente que começa a trabalhar escreve uma linha, e escreve outra ao
terminar.** Uma linha por evento, em `docs/hermes/turnos.txt`:

```
2026-09-04T02:11:07 | bot-2 | step-3.7-flash:free | inicio | portar fronteira_assunto
2026-09-04T02:49:31 | bot-2 | step-3.7-flash:free | fim    | portado, a régua não mexeu
```

Use o seu nome real e o modelo que você está de fato rodando. Se o modelo
trocar no meio (créditos acabaram), escreva `fim` com o modelo velho e `inicio`
com o novo — é assim que o editor vê a troca acontecer.

Isto não é burocracia. É a única coisa que responde à pergunta dele: *"como vou
saber se os bots estão funcionando?"* O relatório (`python scripts/prova.py`)
conta nomes diferentes e confere se as janelas de tempo se sobrepõem. Três bots
que trabalharam em fila não são três bots — é um bot com três nomes, ou a
delegação não subiu. Sem a linha, o trabalho não aconteceu, mesmo tendo
acontecido.

## Antes de começar (uma vez por sessão)

1. `git branch --show-current` → tem que ser `furia-treino-noturno`.
   Se não for: `git checkout furia-treino-noturno`.
2. Leia `docs/hermes/ESTADO.md` inteiro. É uma página. **Não** leia o cofre todo.
3. Confira que a régua roda: `python scripts/regua.py`.
   **Se ela não rodar, a sessão acabou aqui.** Escreva o erro no `ESTADO.md` e
   pare. Sessão sem régua é sessão cega, e sessão cega só produz confiança
   errada.

---

## 1. Trazer material — e por que não é vídeo qualquer

O editor pediu que você baixasse vídeos sozinho. **Vídeo aleatório do YouTube
não serve para treinar**: sem gabarito, não há como saber se o corte ficou bom, e
você passa a noite se elogiando.

O Acervo do CHUB entrega as duas coisas juntas — a transcrição com tempo **e** os
blocos temáticos revisados por gente. Cada vídeo de lá já é um exercício com a
resposta no fim do livro.

```bash
python scripts/novo_material.py --listar     # o que há
python scripts/novo_material.py --sortear    # traz um que ainda não veio
```

Regras do material:

- **Uma fonte por rodada, e nunca a mesma duas vezes seguidas** enquanto houver
  outra. Um motor que melhora numa live e piora nas outras não melhorou —
  decorou.
- Antes de medir uma mudança, escolha a fonte. Trocar de fonte no meio da
  medição invalida a comparação inteira.
- Vídeo do Acervo com zero cortes possíveis nos blocos é descartado sozinho pelo
  script: onde o curador não viu clipe, não se cobra clipe.

---

## 2. Medir e corrigir — o laço que não tem atalho

```
1. MEDIR      python scripts/regua.py --material <fonte> --salvar antes-<ideia>
2. ESCREVER   "vou mudar X porque acho Y, e espero que o número Z suba"
3. MUDAR      UMA alteração. Uma só.
4. MEDIR      python scripts/regua.py --material <a MESMA fonte> --salvar depois-<ideia>
5. DECIDIR    subiu o número previsto  -> guarda
              empatou                  -> DESFAZ
              piorou                   -> DESFAZ
              subiu um e derrubou outro -> DESFAZ e pergunta ao editor
6. ANOTAR     ESTADO.md, sempre, mesmo quando desfez
```

**`<ideia>` tem que ser a MESMA palavra nos passos 1 e 4.** `antes-vocativo` e
`depois-vocativo`, não `antes-vocativo-preso` e `depois-vocativo-solto`. O
relatório de prestação de contas (`python scripts/prova.py`) casa os dois pelo
nome; nomes diferentes viram "experimento pela metade" e o editor lê isso como
trabalho que mudou código sem conferir. Foi o primeiro defeito que esse
relatório pegou, e ele pegou de mim.

**A regra de ouro do número que sobe e do que desce:** antes de desfazer por
"derrubou outro", olhe se o número que caiu é uma FRAÇÃO cujo debaixo cresceu.
`abre junto com o assunto` foi de 2/5 para 2/9 — as mesmas duas aberturas
certas, em nove assuntos alcançados em vez de cinco. Nada piorou. Um número
absoluto que cai é regressão; uma proporção diluída por crescimento não é.

A previsão escrita **antes** (passo 2) é o que separa experimento de tentativa.
Sem ela, qualquer número que subir vira prova de qualquer coisa.

**A trava dos três:** três rodadas seguidas na mesma linha sem mover o número
encerram a linha. Escreva em "Linhas mortas" no `ESTADO.md` o que foi tentado. Vá
para outro assunto. Isto existe para você não passar sete horas repetindo o mesmo
erro com convicção.

**A guarda anti-trapaça:** se `blocos engolidos` subir junto com os outros
números, a melhora é falsa — alguém está entregando um corte gigante por bloco
para acertar as bordas. Desfaça, mesmo que os outros números tenham subido.

---

## 3. Aprender com os cortes que o editor aprovou

Esta é a parte que ele mais pediu, e a mais valiosa: o Acervo diz **onde o
assunto começa e termina**; o editor diz **o que serve**. Não é a mesma coisa.

```bash
python scripts/regua_vereditos.py
```

O caderno enche sozinho enquanto ele revisa pelo celular (veja
`skills/caderno-de-vereditos.md`). O que procurar ali não é "quantos ele
aprovou" — é **onde a opinião dele discorda do que o motor achou de si mesmo**:

> Cinco cortes que ele marcou com "final cortado" e que o motor tinha marcado
> como "fecho completo" são um erro de calibração com nome e endereço.

Isso vira ideia para a fila — **não vira mudança direta**. Continua valendo:
nada muda no motor sem passar pelo laço da parte 2.

Abaixo de vinte vereditos, leia como pista, não como conclusão: uma etiqueta a
mais muda a ordem inteira.

---

## 4. Relatar — o que sempre encerra uma sessão

Nenhuma sessão termina sem isto, nem a que não deu em nada:

1. `ESTADO.md` atualizado: última medição, fila, linhas mortas, travados.
2. Nota de passagem escrita (`skills/nota-de-passagem.md`).
3. Se mexeu em código: commit na `furia-treino-noturno`, com **o número antes e
   o número depois** na mensagem.
4. Um resumo de até dez linhas para o editor ler tomando café: o que subiu, o
   que foi descartado, e o que precisa dele.

Se nada melhorou a sessão inteira, escreva isso, com o que foi tentado. Uma
sessão que descobre que três caminhos não funcionam é uma sessão útil. Uma
sessão que não deixa registro é uma sessão perdida — mesmo que tenha funcionado.

---

## Quando a fila esvazia

Se a fila de ideias do `ESTADO.md` acabar e você for o **modelo grátis**: não
invente direção editorial nova. Escreva no `ESTADO.md` que a fila acabou — é um
recado para o editor, não um problema para resolver sozinho — e vá para o
trabalho que não decide nada:

- rodar a bateria de testes e catalogar o que quebrou
- trazer material novo do Acervo para as próximas rodadas
- procurar no cofre se a ideia da vez já foi tentada antes
- pesquisar ferramenta, técnica de corte ou skill nova, meia página, com fonte
- conferir o cofre: nota velha, nota que contradiz outra, nota que ninguém leu
