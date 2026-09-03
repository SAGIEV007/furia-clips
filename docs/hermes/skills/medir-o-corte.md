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

```
  ┌─ VERDADE DE FORA (contra os blocos do Acervo) ─ ESTA É A META ─┐
     blocos do Acervo alcançados ...   5/10     50%   subir
     abre junto com o assunto ......   2/5      40%   subir
     atravessa dois assuntos .......   1/11      9%   baixar
     pior repetição entre cortes ...          18%   baixar
     blocos engolidos por um corte .           1    baixar
  └─────────────────────────────────────────────────────────────────┘

   diagnóstico — o Furia se avaliando. NÃO é meta:
     contexto completo .............  10/11
     fecho completo ................  11/11
```

**Por que a segunda família não é meta:** ali o Furia diz o que ele acha do
próprio trabalho. Dá para fazer "contexto completo" chegar a 100% num minuto —
é só afrouxar a regra que decide isso. O corte não melhora; o programa só passa
a se elogiar mais. Os números de fora não se deixam enganar assim.

**Todo alvo aqui é alcançável.** Uma versão anterior desta régua media "fecha
junto com o bloco" sobre o total de cortes — impossível, porque o Acervo diz que
num bloco cabem até quatro cortes e só o último pode fechar na borda. Alvo
impossível ensina o agente a concluir que tudo falhou, ou a trapacear.

**`blocos engolidos` é a guarda.** Um corte só, cobrindo mais de 70% de um bloco
onde caberiam vários, marca abertura perfeita e é um clipe inútil. Se esse
número subir junto com os outros, a melhora é falsa.

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
