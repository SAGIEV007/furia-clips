---
name: medir-o-corte
description: Como medir se o Furia está cortando melhor ou pior, usando o Acervo como régua. Use antes e depois de qualquer mudança no motor de corte, e sempre que alguém disser que algo "melhorou".
---

# Medir o corte

Nada no motor de corte muda sem passar por aqui. "Ficou melhor" sem número é
opinião, e opinião de máquina sobre o trabalho da própria máquina não vale nada.

## A régua

```bash
python scripts/regua.py                    # ler na tela
python scripts/regua.py --json             # para o agente ler
python scripts/regua.py --salvar antes-X   # guarda no histórico
```

Ela compara os cortes que o Furia produziu com os **blocos do Acervo** — o
corpus do CHUB, supervisionado por gente. Por isso vale: a resposta certa não foi
escrita pelo programa que está sendo medido.

## Ler o resultado

O script separa três blocos na tela. Só os dois primeiros são meta:

```
  FRONTEIRA (vs. acervo)                       <- META
    abre junto com o bloco ....... 41%            subir
    fecha junto com o bloco ...... 33%            subir

  AUTO-SUFICIENCIA (julgamento do acervo)      <- META
    herda bloco que se sustenta .. 68%            subir
    cai em bloco dependente ...... 22%            baixar

  FLAGS EDITORIAIS (julgamento do Furia)       <- DIAGNÓSTICO, não meta
    contexto completo ............ 91%            NÃO perseguir
    fecho completo ............... 84%            NÃO perseguir
    abre no meio da frase ......... 4%            NÃO perseguir
```

**Por que a terceira família não é meta:** ali o Furia está dizendo o que ele
acha do próprio trabalho. Dá para fazer "contexto completo" chegar a 100% num
minuto — é só afrouxar a regra que decide isso. O corte não melhora; o programa
só passa a se elogiar mais. Os números de fora não se deixam enganar assim.

Use a terceira família para **entender** o que aconteceu ("o número de fora
subiu e o `abre no meio da frase` desabou junto — faz sentido"). Nunca como
prova.

## O erro que invalida a medição

- **Material diferente antes e depois.** Não é comparação, é coincidência.
- **Duas mudanças de uma vez.** Se o número mexeu, qual das duas foi?
- **Régua quebrada.** Se `scripts/regua.py` falhar, **não continue**: sem régua,
  cada rodada seguinte é chute com aparência de método. (Ela lê o gabarito do
  próprio repositório justamente para não depender de pasta temporária, que é o
  que quebra a régua da outra branch.)

## Quando o número não mexe

Não é fracasso — é informação, desde que fique registrada. Três tentativas sem
movimento numa mesma linha e aquela linha morre; escreva no `ESTADO.md` o que
foi tentado, para ninguém (nem você amanhã) repetir.

## Quando um sobe e outro desce

Pare. Isso é uma escolha editorial, não técnica: está trocando um defeito por
outro. Desfaça, e leve a pergunta para o editor com os dois números na mão.
