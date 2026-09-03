# ESTADO — o quadro de aviso

> Este arquivo é lido **antes de qualquer ação**, por qualquer modelo. Ele é a
> memória curta compartilhada. Uma página. Se passar de uma página, alguma coisa
> aqui virou história e devia ter ido para o cofre.
>
> Quem termina uma tarefa atualiza este arquivo. Sem exceção.

---

## Onde o trabalho acontece

| | |
|---|---|
| Branch do turno da noite | `furia-treino-noturno` |
| Branch que o editor baixa | `claude/repo-access-commits-imgjmk` — **não tocar de madrugada** |
| Outra linha em andamento | `furia-sync-portable` — outro agente trabalha lá; não mexer sem combinar |

## A régua

| | |
|---|---|
| Script | `scripts/bench_contexto.py` |
| Verdade de fora | blocos do Acervo (CHUB), supervisionados por gente |
| Números que contam | `abre junto com o bloco`, `fecha junto com o bloco`, `cai em bloco dependente` |
| Números que **não** são meta | tudo sob "FLAGS EDITORIAIS (julgamento do Furia)" |

**Risco conhecido:** o `bench_contexto.py` aponta para arquivos em pasta
temporária do Windows (`AppData/Local/Temp/...`). Pasta temporária some. Se a
régua parar de rodar, é quase certo que é isso — o gabarito precisa de uma cópia
em lugar fixo antes de o turno da noite depender dele.

## Última medição

```
data:        (preencher na primeira rodada)
material:    (qual fonte)
abre junto com o bloco:      __%
fecha junto com o bloco:     __%
cai em bloco dependente:     __%
```

## Fila de ideias (só o modelo pago acrescenta)

Ideias que já foram julgadas e podem ser executadas por qualquer modelo:

- [ ] (vazio — a primeira leva entra quando o editor e o modelo principal
      decidirem as direções)

## Linhas mortas — não tentar de novo sem ideia nova

Registrar aqui o que já foi tentado três vezes sem mover o número.

- (nada ainda)

## O modelo dos bots

`stepfun/step-3.7-flash:free`, provider `nous`
(`inference-api.nousresearch.com`). Modelo pequeno e rápido.

Isso é seguro no desenho porque **quem decide manter ou desfazer uma mudança é o
número da régua, não a opinião do modelo**. Um modelo pequeno consegue rodar o
laço; ele não precisa julgar corte.

Não achei documentação pública dizendo se o nível grátis da Nous treina em cima
do que recebe. Enquanto não houver, vale a regra conservadora: **transcrição,
fala do Renan, dados do CHUB e chaves não passam por bot.** Bot mexe em código e
número.

## Travado / precisa do editor

- **Faltam exemplos aprovados e rejeitados.** Dez cortes que ele aprovaria e dez
  que rejeitaria. Sem isso, a calibração de headline continua no meu julgamento
  em vez do dele, e dois testes seguem parados.
  → O caderno de vereditos (`skills/caderno-de-vereditos.md`) é o caminho para
  isso: trinta vereditos etiquetados resolvem, e ele os produz revisando pelo
  WhatsApp, que é coisa que já ia fazer de qualquer jeito.
- **A chave do CHUB foi commitada num repositório público.** Ela precisa ser
  trocada por quem opera o CHUB. Apagar do código não resolve: o histórico
  guarda.

## Consertado recentemente (para não reabrir)

- Duas moagens rodando ao mesmo tempo; o botão de parar mirava o trabalho errado.
- A nota passou a descontar quando o corte abre no apresentador (intervalo,
  encerramento, cortesia) em vez de no entrevistado.
- Pergunta de jornalista com mais de 8s é aparada; até 8s fica.
- Portões medidos do CHUB (`+14 / −28 / −18`) entraram na nota.
