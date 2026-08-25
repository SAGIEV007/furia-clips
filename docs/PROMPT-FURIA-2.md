# FURIA 2 — prompt de construção

> Cole isto inteiro numa conversa nova. Ele foi escrito no fim de uma sessão
> longa, e carrega o que custou caro para ser descoberto — para que nada disso
> precise ser aprendido de novo.

---

## 1. Quem vai usar

Sou **editor de vídeo, não programador**. Faço cortes do Renan Santos / MBL /
Partido Missão. Duas coisas que mudam como você fala comigo:

- **Nunca use linguagem técnica.** Nome de arquivo, nome de função, "regex",
  "specificity", "endpoint" — nada disso me diz nada. Fale do que a tela faz.
- **Eu só consigo verificar por print e por texto do console.** Não sei ler
  código. Se você disser "está funcionando", eu não tenho como conferir. Então
  a prova é sempre uma foto da tela ou uma linha de registro que eu possa
  copiar e colar de volta.

Trabalho no Windows, numa tela de **1366 × 768**. O programa **abre com dois
cliques** e **funciona sem internet**.

---

## 2. O que estamos fazendo

Construir o **Furia 2** do zero, numa pasta nova, ao lado do Furia atual.

O Furia atual continua funcionando e eu sigo cortando com ele. O novo nasce ao
lado e eu só troco quando ele estiver melhor. **Nada que eu uso hoje pode
quebrar durante a construção.**

O que o programa faz: entra uma live de 1 a 2 horas do Renan (ou de um debate,
entrevista, podcast), e saem 10 a 30 cortes verticais prontos para publicar,
ranqueados, com o começo e o fim nos lugares certos.

---

## 3. As quatro decisões já tomadas

| | |
|---|---|
| **O que fica** | O motor de cortes inteiro + as três peças de interface que já provaram valor (ver §4). Todo o resto da interface morre. |
| **Onde vive** | Pasta nova. Os dois programas rodam lado a lado. |
| **Como abre** | **Janela de programa de verdade**, sem navegador — ícone na barra de tarefas, sem barra de endereço, sem abas. Python por dentro (pywebview ou equivalente), então o motor não muda. |
| **Cadência** | **Tela por tela.** Você entrega UMA tela, manda o print, eu aprovo ou mando refazer, e só então você segue. Nunca mais uma rodada inteira na direção errada. |

---

## 4. O que carrega do Furia 1

### Carrega inteiro — não reescreva, não "melhore de passagem"

O motor tem **27.427 linhas e 891 testes passando**. Cada decisão dele foi
medida contra material real. Portar é copiar os módulos e ligar na interface
nova.

- **Seleção, ranqueamento e corte** — `clip_selector.py`, `editorial_ranker.py`,
  `video_cutter.py`, `transcriber.py`, `transcript_parser.py`
- **Contexto editorial** — `editorial_context.py`, `editorial_block.py`,
  `editorial_chapters.py`, `interview_turns.py`, `political_profile.py`
- **CHUB** (memória de desempenho da campanha) — `campaign_hub*.py`,
  `chub_client.py`, `espelho_chub.py`, `acervo_library.py`
- **Enquadramento e mídia** — `face_tracker.py`, `layout_planner.py`,
  `media_validation.py`, `render_presets.py`, `source_*.py`
- **Headlines** — `headline_*.py`
- **A suíte de testes inteira.** Ela é o que impede o motor de regredir.

### Carrega, mas pode ser redesenhado por fora

Estas três funcionam e foram medidas. A lógica fica; a aparência é sua.

1. **O mapa da fonte** — a live inteira como uma régua, cada corte no ponto de
   onde saiu, os descartados numa pista abaixo, os vãos marcados com a duração.
   Clicar num bloco leva o player até ali. É o que responde "estou perdendo
   cortes?" sem abrir arquivo nenhum.
2. **A onda de ajustar entrada e saída** — arrastar alças sobre a forma de onda
   do áudio, com a fala aparecendo ao passar o mouse. Substituiu dois campos de
   número em segundos absolutos que eu não conseguia usar.
3. **A entrega corte a corte** — os cortes aparecem na tela conforme ficam
   prontos, em vez de todos no fim. Numa live de 2 horas eu esperava a
   trigésima renderização para ver a primeira.

### Morre tudo

`style.css` (5.161 linhas), `atelie.css`, `mesa.css`, `app.js` (5.400 linhas),
o template inteiro, os cinco ambientes, todos os painéis. **Não porte nada
disso, nem "como referência".** Foi exatamente o hábito de reaproveitar que
falhou quatro vezes.

---

## 5. O desenho

### O que eu quero

Mandei estas referências:

- **cipher.tv** — precisão, profundidade, "o espaço entre precisão e possibilidade"
- **poolsuite.net** — retrô, um sistema operacional falso inteiro (PoolOS 3.0),
  temas trocáveis, cursor virando taça de martíni, som
- Uma pasta do Arc com sites variados e um artigo de dashboards

**Olhe os links antes de desenhar.** Se a rede do seu ambiente bloquear algum,
me diga na hora em vez de inferir pelo nome — foi o que aconteceu antes e o
resultado saiu genérico.

O que as duas referências têm em comum não é estilo. É **compromisso**: cada uma
escolheu um mundo e foi até o fim. Poolsuite não é "um player com tema retrô",
é um objeto de 1985.

E as duas são **divertidas**. Eu quero que o Furia encante, não só que fique
bonito. Brinquedo dentro da ficção: um cursor que é um bicho, temas que trocam
o mundo inteiro, som que reage, uma abertura que parece ligar um equipamento.
Nada disso serve para nada, e é tudo isso que faz voltar.

### Autonomia total na cor

**Nunca disse nada sobre âmbar, dourado, ou qualquer cor.** Escolha do zero.
Se você se pegar usando uma cor porque "já era a do Furia", pare — é vício, não
decisão.

### Os dashboards

Precisam ser **magníficos, responsáveis, bonitos e úteis**. Útil quer dizer:
me dão a resposta, não o dado. "news-peg · 1,40× a mediana" me obriga a
traduzir sozinho toda vez; "Abra o próximo corte com news-peg" já é a decisão.

E precisam mostrar a **evidência junto com o número**. Exemplo real da minha
conta:

```
news-peg            1,40×   47 exemplos
contraste-regional  1,19×    4 exemplos
```

Numa lista de barras os dois parecem primos. Não são — o segundo é quatro
posts. Um dashboard que esconde isso está mentindo com elegância.

---

## 6. Por que quatro tentativas falharam — leia antes de desenhar

Isto não é desabafo, é a especificação do erro.

Nas quatro vezes o assistente trocou arquitetura, cor e espaçamento **e manteve
o vocabulário visual por baixo** — cartão cinza, ícone genérico, painel de
formulário. O resultado sempre pareceu o mesmo site melhorado, porque era.

Os sintomas exatos, para você reconhecer se estiver repetindo:

- Camadas de folha de estilo nova por cima da antiga, com `!important` brigando.
  Sinal: precisar de `!important` para fazer algo aparecer.
- Estilizar só as telas que foram fotografadas. Na última rodada, todo o
  desenho foi escopado nos painéis principais e a gaveta de Ajustes, os modais
  e a paleta de comandos ficaram **exatamente iguais aos de antes**. Eu abri e
  vi na hora.
- Trocar a pintura de um painel e chamar de dashboard novo, sem mexer no que
  ele mostra nem em como arruma.

**A regra que evita os três:** o programa novo não herda nenhuma folha de
estilo. Se um componente não foi desenhado por você, ele não existe na tela.

---

## 7. O que já foi medido — não redescubra

Cada item abaixo custou uma rodada. São fatos, não opiniões.

### Sobre os cortes

- **A peneira de sobreposição deve perguntar quanto o candidato ACRESCENTA, não
  quanto ele repete.** A regra antiga (`sobreposição > 30% → morre`) matava duas
  situações opostas: um candidato inteiro dentro de um corte entregue (não é
  perda — o corte longo contém a fala) e um que só encostava na borda trazendo
  material próprio (perda de verdade). Medido em 21 descartes reais: 12 do
  primeiro tipo, 9 do segundo.
- **O piso é de proporção, nunca absoluto.** Um piso absoluto de 30s matava
  candidatos de 30s que só compartilhavam 6s. A conta certa é: quanto DESTE
  candidato já foi entregue. Abaixo de 40% de novidade, morre.
- **95% dos cortes que a campanha publica têm 32 segundos ou mais** (medido em
  4.109 cortes reais no CHUB: percentil 5 em 32s no Facebook, 36s no Instagram,
  46s no TikTok; mediana entre 91s e 123s).
- **A pergunta da repórter vazando na borda NÃO custa cortes.** Foi medido e
  confirmado; não gaste rodada nisso.
- **Cinco categorias gramaticais denunciam uma abertura ruim**, e o detector
  antigo não pegava nenhuma: "agora" na primeira palavra, oração gerundiva
  ("Somando tudo..."), advérbio aditivo na primeira oração ("também",
  "inclusive", "aliás"), dêitico no fim da primeira oração ("...organizados
  aí"), e fragmento de até três palavras terminado em "?".
- **Um fim ruim também é uma frase bem-formada.** "Se sustenta sozinha" não
  separa nada nesse lado. O que separa é a marca de anúncio: enumeração
  pendurada ("segundo ponto:"), "uma vez", "teve um/uma".
- **Alargar o REPARO de borda é seguro; alargar o PORTÃO reduz cortes.** Reparo
  move a borda; portão adia o candidato. Nunca confunda os dois.

### Sobre entregar

- **Persistir no banco ANTES de avisar a tela.** Um cartão que chega sem
  registro não pode ser ajustado nem aprovado.
- **O cartão entregue tem de ser o mesmo objeto que a lista final traz.** Monte
  em um lugar só, senão os dois divergem na primeira alteração.
- **Um aviso que falha não pode derrubar o corte.** O arquivo já está no disco.

### O NORTE

Um número que a ferramenta produz sobre material que a própria ferramenta gerou
**não mede nada**. Só referência externa vale: o CHUB, o Acervo, a minha
avaliação. Se você se pegar reportando "o Furia acertou 87%", pare.

---

## 8. Como falhas acontecem neste projeto

O padrão que mais me custou tempo: **caminhos que falham em silêncio**.

- O botão de fechar a prévia apontava para um elemento apagado duas versões
  antes. `getElementById` devolvia nada, a guarda engolia, e o clique terminava
  sem erro nenhum. Eu reportei três vezes.
- O "salvar ajuste" gravava os valores originais em vez dos arrastados. O
  servidor respondia sucesso, o histórico registrava o corte igual ao que já
  era, e nada avisava.
- 34 regras de cor dependiam de um nome de atributo que o tema não usava mais.
  Nunca disparavam. O teste passava porque procurava o texto no arquivo.

**A conclusão:** nenhuma leitura de código pega isso. Teste no navegador de
verdade, clicando de verdade. E um teste que só sabe dizer "a linha existe no
arquivo" não sabe dizer se ela faz alguma coisa.

---

## 9. Como quero trabalhar

1. **Uma tela por vez.** Entregue uma, mande o print, espere eu aprovar.
2. **Print sempre.** Não descreva o que ficou bonito; me mostre.
3. **Meça antes de afirmar.** Se disser "cabe na tela", meça a largura. Se disser
   "melhorou o corte", rode contra material real e mostre os números.
4. **Me diga quando errar.** Prefiro "isto quebrou e eu consertei" a descobrir
   sozinho três rodadas depois.
5. **Nunca remova algo que eu pedi sem falar.** Se a decisão de desenho custar
   uma função que eu pedi antes, diga na hora e me deixe escolher.
6. **Não me mande abrir pasta nem digitar comando.** Se eu preciso de um
   arquivo, faça um botão.

---

## 10. Duas coisas pendentes do Furia 1

- **A chave do CHUB precisa ser trocada** por quem opera o CHUB. Ela foi parar
  num repositório público e apagar não resolve — o histórico guarda. No Furia 2
  ela nunca pode entrar em arquivo versionado.
- **A legendagem deu erro** e nunca foi investigada. Baixa prioridade.

---

## 11. Como começar

Não comece codando. Comece assim:

1. Abra as referências e me diga o que viu — e o que não conseguiu abrir.
2. Proponha **o conceito**: que mundo o Furia 2 habita, em duas ou três frases,
   e por que ele aguenta oito horas de uso por dia.
3. Proponha **a paleta**, escolhida do zero, com a razão de cada cor.
4. Proponha **a organização das telas** — quais são, em que ordem, e por quê.
5. Desenhe **UMA tela** no acabamento final e me mande o print.

Só depois que eu aprovar essa tela, siga para as outras.
