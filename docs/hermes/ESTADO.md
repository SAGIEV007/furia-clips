# ESTADO — o quadro de aviso

> Este arquivo é lido **antes de qualquer ação**, por qualquer modelo. Ele é a
> memória curta compartilhada. Uma página. Se passar de uma página, alguma coisa
> aqui virou história e devia ter ido para o cofre.
>
> Quem termina uma tarefa atualiza este arquivo. Sem exceção.

---

## Onde o trabalho acontece

| | | |
|---|---|---|
| Branch do trabalho autônomo | `furia-treino-noturno` | 
| Branch que o editor baixa | `claude/repo-access-commits-imgjmk` — **não tocar sem ele olhando** | 
| Outra linha em andamento | `furia-sync-portable` — outro agente trabalha lá; não mexer sem combinar | 

## A régua

| | | |
|---|---|---|
| Régua do assunto | `python scripts/regua.py [--material <arquivo>]` | 
| Régua do editor | `python scripts/regua_vereditos.py` | 
| Material novo | `python scripts/novo_material.py --sortear` (traz do Acervo, com gabarito) | 
| Gabarito padrão | `tests/fixtures/acervo_sabatina_band.json` — versionado no repositório | 
| Verdade de fora | 10 blocos do Acervo (CHUB), supervisionados por gente | 
| Números que contam | `blocos alcançados`, `abre junto com o assunto`, `atravessa dois assuntos`, `pior repetição` | 
| Números que **não** são meta | tudo sob "diagnóstico — o Furia se avaliando" | 
| Histórico | `docs/hermes/medicoes.txt` (use `--salvar <rótulo>`) | 

Rodam sem instalar nada e sem depender de pasta temporária. A régua da outra
branch (`bench_contexto.py`, em `furia-sync-portable`) lê o gabarito de
`AppData/Local/Temp/` — pasta temporária some, e régua que some no meio da noite
é pior que régua nenhuma, porque o trabalho continua e passa a medir nada. Esta
lê do próprio repositório.

**Material novo tem que vir do Acervo, não do YouTube solto.** Sem gabarito não
há como saber se o corte ficou bom. São 5.391 blocos revisados por gente
disponíveis — cada vídeo de lá já vem com a resposta.

## Última medição

```
2026-09-03  pós-fix-15min  (sabatina da Band, 1923s)
  blocos do Acervo alcançados ...  9/10   90%
  abre junto com o assunto ......  2/9    22%   (dos blocos alcançados)
  atravessa dois assuntos .......  2/16    12%
  pior repetição entre cortes ...        18%
  blocos engolidos por um corte .          1
  entregues 16 · adiados 5 · o Acervo diz que cabem 32
```

Medida igual na máquina do editor e na minha — o número é reproduzível, dá para
usar como referência comum.

**O que ela já ensina:** os primeiros quinze minutos foram consertados
(`first_address_to_guest` reconhece nome entre vírgulas; travessia de bloco
também foi isolada). O desequilíbrio por geração de candidatos estava errado:
a contagem por etapa mostrava que `_align_to_interview_turns` matava 13 de 13
candidatos dos blocos 1-4. Corrigido, com teste que trava.

Agora o ronco está em **ideia 1 da fila atual**: o corte que atravessa dois assuntos.

## A fila de ideias

Ordem de tamanho do ganho. Uma de cada vez, sempre com medição antes e depois.

### 1. O corte que atravessa dois assuntos ← COMEÇAR POR AQUI

2 em 16 hoje. O caso concreto: o corte 1742,3–1773,4 pisa no bloco 8
(prefeitos/reeleição) e no bloco 9 (privatizações) — dois assuntos colados num
clipe só.

O Furia lê a fonte em **8** blocos temáticos próprios; o Acervo marca **10**. A
travessia acontece onde as duas leituras discordam. Comparar as duas divisões e
ver onde elas se afastam.

Alvo: `atravessa dois assuntos` chegar a 0/16.

### 2. Abrir onde o assunto começa

2 de 9 hoje. Quando o Furia entra num assunto, ele começa no lugar certo em 22%
das vezes.

Existe pesquisa pronta para isso na branch `furia-sync-portable`:
`modules/fronteira_assunto.py` — recuo até a fronteira do assunto, com validação
contra 400 trechos de gabarito humano (anáfora órfã: 100% de precisão;
conectivo dependente: 87,5%). **Portar e medir**, não reescrever do zero.

Alvo: `abre junto com o assunto` subir de 22%.

## Linhas mortas — não tentar de novo sem ideia nova

Registrar aqui o que já foi tentado três vezes sem mover o número.

- **Ideia 0: os primeiros quinze minutos não rendiam corte.** Tentativas de
  consertar por geração de candidatos, peneira de entrevista e portão não
  moveram o número. A causa real estava em `_align_to_interview_turns`, não
  na geração. **Corrigido** em `2026-09-03`: `first_address_to_guest`
  reconhece nome entre vírgulas; teste adicionado trava o comportamento.

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
- Os primeiros quinze minutos não rendiam corte: `first_address_to_guest`
  reconhece nome entre vírgulas; `_align_to_interview_turns` não matava mais
  candidatos dos blocos 1-4. **Teste adicionado.**
