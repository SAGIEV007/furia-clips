# O Furia trabalhando sozinho

Como fazer o Hermes cuidar, testar e melhorar o Furia sem supervisão, a qualquer
hora — sem andar em círculos e sem o programa amanhecer quebrado.

O ciclo tem quatro partes:

```
   1. TRAZER MATERIAL   ->  2. MEDIR E CORRIGIR
          ^                        |
          |                        v
   4. RELATAR          <-  3. APRENDER COM O EDITOR
```

## O que tem aqui

| arquivo | o que é |
|---|---|
| `CARTA.md` | As ordens permanentes. Qualquer modelo lê antes de agir. |
| `ESTADO.md` | O quadro de aviso. Uma página, sempre atual, lida antes de tudo. |
| `skills/modo-autonomo.md` | O ciclo inteiro: trazer material, medir, corrigir, aprender, relatar. |
| `skills/medir-o-corte.md` | Como saber se melhorou de verdade. |
| `skills/nota-de-passagem.md` | O bilhete que faz o trabalho continuar quando o modelo troca. |
| `skills/caderno-de-vereditos.md` | Anotar "serviu / serviu com ressalva / não serviu" pelo WhatsApp sem interromper o que está rodando. |
| `skills/conferir-antes-de-entregar.md` | Provar que a tarefa foi feita antes de dizer que foi. Nasceu de um bot que rodou 19 testes de 1196 e respondeu "passou". |
| `O-TIME.md` | Quantos bots, quais papéis, e por que dois bastam. |
| `TESTE-DO-HERMES.md` | Sete perguntas com gabarito, para julgar o Hermes sem ler código. |
| `FRASES-PRONTAS.md` | O que mandar no WhatsApp, palavra por palavra. |

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

**O programa que você baixa nunca é tocado sem você olhando.** O trabalho
autônomo acontece só na `furia-treino-noturno`.

**Nada fica de pé sem provar.** Cada mudança é medida contra os blocos do
Acervo — verdade de fora, supervisionada por gente. Se o número não sobe, a
mudança é desfeita na hora, e o motivo fica escrito. É isso que separa sete
horas de treino de sete horas de uma máquina se achando ótima.

## As ferramentas

```bash
python scripts/novo_material.py --sortear     # traz material novo COM gabarito
python scripts/regua.py --material <arquivo>  # mede contra o Acervo
python scripts/regua_vereditos.py             # mede contra o julgamento do editor
```

**Por que não baixar vídeo qualquer:** sem gabarito não há como saber se o corte
ficou bom, e um agente medindo o próprio trabalho passa a noite produzindo
confiança errada. O Acervo entrega transcrição e blocos revisados por gente
juntos — cada vídeo de lá já é um exercício com a resposta no fim do livro. São
5.391 blocos disponíveis.

A régua roda sem instalar nada. O gabarito — 10 blocos do Acervo da sabatina da Band —
está versionado em `tests/fixtures/acervo_sabatina_band.json`, então a régua não
depende de pasta temporária nem do estado da máquina.

Linha de base medida em 03/09, na sabatina da Band: **5 dos 10 blocos
alcançados**, e **zero cortes nos primeiros quinze minutos** — onde o Acervo diz
que cabem 16. O Furia, sobre si mesmo, marcou "contexto completo" em 10 de 11.
Essa distância entre os dois números é o motivo de a régua existir.
