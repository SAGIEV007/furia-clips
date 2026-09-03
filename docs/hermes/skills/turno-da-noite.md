---
name: turno-da-noite
description: O laço de treino do Furia enquanto o editor dorme. Use quando pedirem para treinar, melhorar, calibrar ou trabalhar no Furia sem supervisão. Cada rodada mede antes, muda uma coisa, mede depois, e desfaz o que não melhorou.
---

# Turno da noite

Leia `docs/hermes/CARTA.md` antes. Ela manda mais que esta skill.

## Antes de começar (uma vez por turno)

1. `git branch --show-current` → tem que ser `furia-treino-noturno`.
   Se não for: `git checkout furia-treino-noturno`. Se não existir, crie a
   partir da branch atual do editor e avise no `ESTADO.md`.
2. Leia `docs/hermes/ESTADO.md` inteiro. É uma página.
3. Confira que a régua roda: `python scripts/regua.py`.
   **Se ela não rodar, o turno acabou aqui.** Escreva no `ESTADO.md` o erro
   exato e pare. Um turno sem régua é um turno cego, e turno cego só produz
   confiança errada.
4. Monte a lista de material da noite: fontes diferentes, na ordem em que serão
   usadas. A mesma fonte não repete enquanto houver outra na lista.

## A rodada (repetir a noite toda)

### 1 — Medir o "antes"

Rode a régua no material da vez. Anote os três números de fora:

```
abre junto com o bloco:    __%
fecha junto com o bloco:   __%
cai em bloco dependente:   __%   (menor é melhor)
```

### 2 — Escolher UMA coisa

Da fila de ideias do `ESTADO.md`. Se a fila estiver vazia e o modelo no comando
for o grátis: **não invente direção nova** — vá para as tarefas de pesquisa
(seção final) e registre que a fila acabou.

Escreva, antes de mexer: *"vou mudar X porque acho que Y, e espero que o número
Z suba."* Previsão escrita antes é o que separa experimento de tentativa.

### 3 — Mudar

Uma alteração. Pequena. Se precisar de duas para funcionar, é uma ideia só —
mas registre que foram duas peças, porque se der certo você vai querer saber
qual delas carregou.

### 4 — Medir o "depois"

Mesma régua, **mesmo material**. Comparar medição de materiais diferentes não
compara nada.

### 5 — Decidir, sem dó

| resultado | o que fazer |
|---|---|
| o número que você previu subiu | guarda. Anota quanto. |
| empatou | **desfaz** (`git checkout -- <arquivos>`). Anota que empatou. |
| piorou | **desfaz**. Anota o que piorou e quanto. |
| subiu um e derrubou outro | **desfaz** e leva para a fila como pergunta para o editor. Trocar um defeito por outro é decisão dele, não sua. |

### 6 — Anotar

Sempre, mesmo quando desfez. No `ESTADO.md`, e com commit se algo ficou:

```
git commit -m "<o que mudou>

antes:  abre 41% / fecha 33% / dependente 22%
depois: abre 47% / fecha 33% / dependente 19%

<por que isso aconteceu, na sua leitura>"
```

### 7 — A trava dos três

Se três rodadas seguidas na mesma linha de ataque não moveram nada: encerre
aquela linha. Escreva em "Linhas mortas" no `ESTADO.md` o que foi tentado. Vá
para outro assunto.

---

## Quando a fila esvazia (ou o modelo pago acabou)

Trabalho que qualquer modelo pode fazer sem decidir nada sobre corte:

- Rodar a bateria de testes inteira e catalogar o que quebrou.
- Procurar no cofre se a ideia da vez já foi tentada antes.
- Pesquisar ferramenta ou técnica de corte e resumir em meia página, com fonte.
- Procurar skill nova que sirva ao projeto, e dizer para que serviria aqui.
- Conferir o cofre: nota velha, nota que contradiz outra, nota que ninguém nunca
  leu. Apontar, não apagar.

Tudo isso vira nota no cofre e uma linha no `ESTADO.md`. Nada disso vira
mudança no motor de corte sem passar pelo laço de medição.

---

## Encerrar o turno

1. `ESTADO.md` atualizado — última medição, fila, linhas mortas, travados.
2. Nota de passagem escrita (`skills/nota-de-passagem.md`).
3. Commits na `furia-treino-noturno` com antes/depois na mensagem.
4. Um resumo de até dez linhas para o editor ler tomando café: o que subiu, o
   que foi descartado, e o que precisa dele.
