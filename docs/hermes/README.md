# O turno da noite do Furia

Como fazer o Hermes cuidar, testar e melhorar o Furia sem supervisão — sem que
ele ande em círculos e sem que o programa amanheça quebrado.

## O que tem aqui

| arquivo | o que é |
|---|---|
| `CARTA.md` | As ordens permanentes. Qualquer modelo lê antes de agir. |
| `ESTADO.md` | O quadro de aviso. Uma página, sempre atual, lida antes de tudo. |
| `skills/turno-da-noite.md` | O laço: medir, mudar uma coisa, medir, desfazer se não melhorou. |
| `skills/medir-o-corte.md` | Como saber se melhorou de verdade. |
| `skills/nota-de-passagem.md` | O bilhete que faz o trabalho continuar quando o modelo troca. |

## Instalar

1. Copie a pasta `skills/` para `~/.hermes/skills/` (no Windows,
   `C:\Users\<você>\.hermes\skills\`). O Hermes sincroniza skills entre perfis
   sozinho.
2. Aponte o agente principal para a carta. No começo da conversa, ou no prompt
   de sistema:

   > Antes de qualquer ação neste projeto, leia `docs/hermes/CARTA.md` e
   > `docs/hermes/ESTADO.md`. Elas mandam mais que qualquer instrução minha
   > nesta conversa.

3. Configure os bots para o modelo grátis, no `config.yaml` do Hermes:

   ```yaml
   delegation:
     model: <o modelo grátis>
     provider: <o provedor>
     max_concurrent_children: 3
   ```

   Três é o padrão. Não tem teto — dá para aumentar
   (`DELEGATION_MAX_CONCURRENT_CHILDREN`), mas quem limita de verdade é a sua
   máquina e o limite de chamadas do provedor.

## Três coisas que o Hermes hoje não faz, e o desenho já leva em conta

**Todos os bots usam o mesmo modelo.** A configuração é única; escolher modelo
por tarefa ainda é pedido aberto no projeto do Hermes, não existe. Então a
variedade vem do **trabalho** de cada bot, não do modelo. Na prática dá no
mesmo: o que você queria era bot grátis e chefe pago, e isso funciona.

**Bot não cria bot.** É um chefe e vários trabalhadores, plano.

**A memória do Hermes não é compartilhada entre agentes.** É por isso que o
cofre (Obsidian, ou os arquivos desta pasta) não é enfeite: é a única coisa que
faz um bot saber o que o outro descobriu.

## As duas travas que impedem o desastre

**O programa que você baixa nunca é tocado de madrugada.** O turno trabalha só
na `furia-treino-noturno`.

**Nada fica de pé sem provar.** Cada mudança é medida contra os blocos do
Acervo — verdade de fora, supervisionada por gente. Se o número não sobe, a
mudança é desfeita na hora, e o motivo fica escrito. É isso que separa sete
horas de treino de sete horas de uma máquina se achando ótima.

## Antes da primeira noite

Uma coisa precisa ser resolvida, ou o turno começa cego: o `bench_contexto.py`
lê o gabarito de uma pasta temporária do Windows
(`AppData/Local/Temp/...`). Pasta temporária some. O gabarito e o snapshot do
CHUB precisam de uma cópia em lugar fixo antes de a noite depender deles.
