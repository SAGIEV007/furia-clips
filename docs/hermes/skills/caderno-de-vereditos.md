---
name: caderno-de-vereditos
description: Anotar o veredito do editor sobre cada corte (serviu, serviu com ressalva, não serviu) sem interromper o trabalho em andamento. Use sempre que ele mandar um número seguido de ok / ok mas / nao. A análise só acontece quando ele mandar "fechar rodada".
---

# Caderno de vereditos

O editor revisa os cortes pelo WhatsApp, um por um, enquanto você está fazendo
outra coisa. O medo dele, nas palavras dele:

> *"se eu clicar em aprovar o segundo depois de aprovar o primeiro, eu não quero
> que ele cancele toda a análise que está fazendo do primeiro vídeo"*

Então a regra número um desta skill é sobre o que **não** fazer.

## Ao receber um veredito: três coisas, e mais nada

1. Escrever a linha no caderno.
2. Responder **uma linha curta** confirmando.
3. Parar.

**Não** analisar. **Não** replanejar. **Não** abrir o projeto. **Não** rodar
nada. **Não** interromper a tarefa em andamento. **Não** comentar se concorda.
Um veredito é uma anotação no caderno, não um comando.

Se você estava no meio de uma moagem, uma medição ou um turno da noite:
continue exatamente de onde estava. O veredito não muda a tarefa atual.

## O formato que ele manda

```
3 ok
4 ok mas final cortado
7 nao abre no apresentador
9 nao
```

O número é o do corte, como foi enviado. Três vereditos possíveis:

| ele escreve | quer dizer |
|---|---|
| `ok` | serviu como está |
| `ok mas <motivo>` | ele usou, mas tem defeito que vale registrar |
| `nao <motivo>` | não serviu |

**O `ok mas` é o mais importante dos três.** Ele existe porque um corte pode ser
publicável e ainda assim estar errado:

> *"tem vídeos que o final ficou cortado então eu tive que cortar mais cedo
> ainda para dar o mínimo de contexto e por conta disso não posso mandar como se
> estivesse aprovado quando na verdade ele teria uma observação"*

Marcar isso como "aprovado" apagaria justamente o defeito que precisa ser
consertado. Marcar como "reprovado" seria mentira — ele usou o corte.

## Motivos que o programa sabe usar

Aceite qualquer texto livre, mas quando o motivo cair num destes, guarde
também a etiqueta — é o que liga a opinião dele a um número do motor:

| ele escreve algo como | etiqueta |
|---|---|
| final cortado, cortou no fim, faltou o fecho | `fim` |
| começo cortado, abre no meio, entra atrasado | `abertura` |
| abre no apresentador, começa no jornalista, intervalo | `locutor` |
| sem contexto, não dá para entender sozinho | `contexto` |
| muito longo, arrastado | `longo` |
| curto demais, cortou cedo | `curto` |
| repetido, igual ao outro | `repetido` |

Se o motivo não cair em nenhuma, guarde o texto como veio e etiquete `outro`.
Nunca invente etiqueta para forçar encaixe.

## O manifesto — grave ANTES de enviar os cortes

**Isto é obrigatório, e sem isto o caderno inteiro não conserta nada.**

Ao enviar uma rodada de cortes, grave junto o que foi enviado e o que o motor
achava de cada um: `~/FuriaClipsData/vereditos/<rodada>.manifesto.json`

```json
{"rodada": "rodada-07", "cortes": [
  {"numero": "1", "video": "dQw4w9WgXcQ", "start": 120.0, "end": 178.5,
   "sinais": {"payoff_complete": true, "context_complete": true,
              "starts_mid_sentence": false, "opens_without_a_claim": "",
              "overlap_suspected": false}}
]}
```

Os `sinais` saem do próprio corte, em `score_factors`. Copie como estão.

**Por que:** sem o manifesto, o caderno vira uma lista de reclamações sem
endereço. Dá para saber que ele reprovou seis cortes por "final cortado", e não
dá para saber se o motor tinha achado aqueles seis fechados. É a diferença entre
os dois que aponta o parafuso solto — e é a única coisa que vira conserto.

`python scripts/aprender.py` avisa quando o manifesto está faltando.

## Os cortes que ELE fez — a peça mais valiosa

Quando ele mandar um corte pronto, ou disser *"eu teria cortado de 12:34 a
13:45"*, grave em `~/FuriaClipsData/cortes_do_editor/<mês>.txt`:

```
2026-09-05 14:02 | dQw4w9WgXcQ | 754.0 | 812.5 | a headline que ele usou
```

Segundos desde o começo do vídeo. Se ele der em minutos, converta.

**Por que isto vale mais que tudo:** ele apontou o buraco sozinho —

> *"quando eu mandar links de lives recentes, essas lives não vão estar no chub"*

O Acervo não tem a live de ontem. Ele tem, porque cortou. Cada corte dele é um
gabarito para um vídeo que nenhum catálogo cobre, e a régua passa a funcionar
ali:

```bash
python scripts/aprender.py --gabarito dQw4w9WgXcQ
python scripts/regua.py --material tests/fixtures/editor_dQw4w9WgXcQ.json
```

Pergunte o começo e o fim quando ele mandar um corte sem os tempos. Uma pergunta
curta, uma vez — não vire um interrogatório a cada clipe.

## O caderno

Arquivo: `~/FuriaClipsData/vereditos/<rodada>.txt`

**Só acrescenta linha. Nunca reescreve.** Uma reescrita pode perder veredito, e
veredito perdido é trabalho dele jogado fora.

```
2026-09-03 22:14 | rodada-07 | #3 | ok        |         |
2026-09-03 22:14 | rodada-07 | #4 | ok-mas    | fim     | final cortado
2026-09-03 22:15 | rodada-07 | #7 | nao       | locutor | abre no apresentador
```

Se ele mandar um veredito sobre um número que já tem veredito, **acrescente
mesmo assim** e marque `(corrigido)`. A última linha de cada número é a que vale.
Ele mudar de ideia é normal; apagar o histórico não é.

## A resposta

Uma linha. Sem análise, sem elogio, sem pergunta.

```
#4 anotado: serviu com ressalva (fim).
```

Se ele mandar cinco vereditos seguidos, responda os cinco em uma mensagem só,
uma linha cada. Cinco mensagens seguidas atrapalham quem está revisando.

## Quando ele mandar "fechar rodada"

**Aí sim** você lê o caderno inteiro e trabalha. Nunca antes.

O que entregar, em no máximo quinze linhas:

1. A conta: quantos `ok`, quantos `ok mas`, quantos `nao`.
2. As etiquetas em ordem de frequência — a que mais aparece é o defeito que mais
   custa a ele hoje.
3. O cruzamento com o que o programa acha de si mesmo: se cinco cortes levaram
   `fim` e o motor tinha marcado "fecho completo" nos cinco, isso é um erro de
   calibração localizado, e é ouro.
4. Uma proposta só, a mais provável de mover a agulha, escrita como ideia para a
   fila do `ESTADO.md`. **Não implemente.** A fila é decidida com ele.

## Por que isto vale mais que qualquer botão

Um botão de "aprovado / reprovado" dá um bit de informação. O que ele escreve —
*"ok mas final cortado"* — dá a etiqueta, o motivo e a direção do conserto.

E é isso que faltava para o treino da noite: os vereditos dele são **verdade de
fora**, do mesmo tipo que os blocos do Acervo. Um caderno com trinta vereditos
etiquetados vale mais para calibrar o motor do que qualquer número que o Furia
dê para si mesmo.
