# Norte do Furia Clips

Este é o documento de direção. Ele é longo apenas onde ser curto custaria uma
decisão errada.

O projeto já teve 120 KB de prompts de continuidade, escritos porque cada sessão
de IA perdia a memória e a seguinte precisava ser reconstruída do zero. Quarenta
e quatro por cento dos commits daquela fase eram só documentação. Uma sessão
nova gastava metade do fôlego lendo sobre si mesma antes de tocar em qualquer
coisa, e três capacidades foram construídas, medidas, documentadas e nunca
ligadas a nada — porque o contexto acabava antes.

A regra que substitui aquele volume não é "seja curto". É **cada linha aqui muda
uma decisão**. Se uma frase não muda o que alguém faria amanhã, ela sai.

---

## Índice

1. [O que a ferramenta é](#1-o-que-a-ferramenta-é)
2. [As quatro etapas](#2-as-quatro-etapas)
3. [Autonomia](#3-autonomia)
4. [Invariantes editoriais](#4-invariantes-editoriais)
5. [A régua: o que conta como medir](#5-a-régua-o-que-conta-como-medir)
6. [Como trabalhar](#6-como-trabalhar)
7. [O que só o editor pode fazer](#7-o-que-só-o-editor-pode-fazer)
8. [Como o Furia aprende](#8-como-o-furia-aprende)
9. [A headline](#9-a-headline)
10. [Onde o conhecimento mora, e como ele viaja](#10-onde-o-conhecimento-mora-e-como-ele-viaja)
11. [Etapa 4, desenhada](#11-etapa-4-desenhada)
12. [Design](#12-design)
13. [Os blocos precisam ser úteis](#13-os-blocos-precisam-ser-úteis-não-só-existir)
14. [Onde estamos](#14-onde-estamos)

---

## 1. O que a ferramenta é

Um cortador **especialista** em Renan Santos, MBL e Partido Missão. Não é um
cortador genérico apontado para um tema: é uma ferramenta que conhece essas
pessoas, esse vocabulário, esse público e o que já funcionou nessas contas.

O trabalho real do editor é escolher, de duas horas de material, os três minutos
que valem. Tudo o mais é consequência disso.

**Meta:** sair de 10 cortes por dia feitos à mão para 20–30 por dia, sem perder
qualidade editorial. Velocidade que custa credibilidade não serve.

**O que a ferramenta não é.** Não é um concorrente do OpusClip e não deve tentar
ser. As ferramentas comerciais geram trinta cortes sabendo que sete de cada dez
serão descartados — é uma decisão de projeto legítima para quem vende volume. O
Furia é o oposto por necessidade: um corte que atribui uma fala a quem não a
disse não custa um corte, custa a conta. Precisão sobre quantidade não é uma
limitação a superar; é a identidade.

---

## 2. As quatro etapas

Não se pula etapa. Automatizar um corte ruim só multiplica o corte ruim.

**Etapa 1 — Cortar decente.** As bordas caem onde a conversa tem costura, a
legenda sai com os nomes certos, e o caminho de qualidade não desaba para o
fallback. *Critério de saída: numa fonte longa e real, a maioria dos cortes é
aproveitável sem retrabalho de borda.*

**Etapa 2 — Especializar.** Entender o argumento, gerar headline com contexto,
medir energia e reação, aproveitar o que o Campaign Hub sabe.

E, antes de tudo isso, **saber quem fala — antes de escolher o que cortar.** A
leitura da fonte hoje conhece só o texto: sabe o que foi dito e não faz ideia de
quem disse. Passar o reconhecimento de voz sobre a fonte inteira antes da seleção
produz uma linha do tempo de locutor, e ela resolve três coisas de uma vez: o
enquadramento passa a ter em quem focar, o trecho de terceiro é reconhecido antes
de virar candidato, e **a troca de voz vira costura** — uma fronteira melhor que a
detecção por forma de tratamento no texto, que funcionou numa sabatina e achou só
catorze costuras em setenta e três minutos de coletiva. Voz não depende de
vocabulário: funciona em live, debate, podcast e coletiva igualmente.

*Critério de saída: o Furia acerta a headline com frequência suficiente para o
editor editar em vez de reescrever.*

**Etapa 3 — Automatizar.** Enquadramento, silêncio, composição e legenda saem
prontos. O editor entra para escolher e para inserir imagem e música.
*Critério de saída: uma fonte de duas horas vira material publicável com
intervenção só nas escolhas.*

**Etapa 4 — Orquestrar.** A live acaba, o material chega cortado, validado e
entregue sem ninguém abrir o programa.

**Sobre pular para a etapa 4 cedo.** Existe pressão externa para priorizar o
caminho sem interface, porque "agente-first" virou critério de avaliação de
mercado. A pressão está tecnicamente certa e estrategicamente errada para este
projeto no momento: um comando de linha que produz corte ruim automatiza corte
ruim mais rápido. O caminho sem interface entra quando a etapa 1 fechar — com uma
exceção barata descrita na seção 11.

---

## 3. Autonomia

Total. Decidir, construir, medir, testar, comitar, publicar — sem pedir licença
para trabalho técnico.

Perguntar só em três casos:

1. a decisão é **editorial** e pertence ao editor;
2. depende de **dado que só ele tem** (a voz, os pares de treino, a grafia de um
   nome, o que é bom e o que não é);
3. a ação é **irreversível ou sai da máquina dele**.

Discordar quando houver motivo, e dizer o motivo. Se ele reafirmar, é decisão
dele e o trabalho segue completo.

---

## 4. Invariantes editoriais

Não são burocracia. Cada uma é cicatriz de um erro que já aconteceu neste
projeto e custou corte ruim.

- **Portões antes do score.** Emoção e palavra viral não compensam falha de
  estrutura: contexto ausente, começo no meio da frase, pergunta sem resposta,
  final truncado.
- **O áudio é a verdade para citação.** Legenda automática é navegação. Aspas só
  para o que foi realmente dito.
- **Não atribuir fala por palpite.** "Não sei" é resposta legítima e é a que
  protege o editor.
- **Descartar fala real é pior que manter um candidato fraco.** Um corte fraco se
  ignora; um trecho bom descartado não volta.
- **Um argumento cortado antes da conclusão pode virar o oposto do que foi dito.**
- **Nenhum dado de fora aprova um corte sozinho.** Métrica histórica, papel de
  entidade, bloco do Acervo e prior estatístico informam. Nenhum deles compensa
  um portão de contexto, transcrição, locutor ou evidência.
- **O portão antes de publicar encolhe, mas não some.** Ele é calibrado, não
  binário, e encolhe na exata proporção do trabalho de especialização:

  - **Verde** — tudo que dá para medir fechou: voz confirmada, borda em costura,
    pergunta respondida, nomes conferidos, headline sustentada pela transcrição,
    nada sensível. Aprovação em lote, olhando só as headlines.
  - **Âmbar** — alguma medição não fechou, e o motivo específico vem junto:
    "o áudio não confirma o locutor", "termina 2s antes da conclusão".
  - **Vermelho** — alegação factual forte, terceiro falando, tema sensível.

  Com a especialização feita, o verde vira a maioria e a revisão de trinta cortes
  leva trinta segundos. O que o portão continua cobrindo não é incompetência da
  ferramenta: é informação que não está no vídeo. Uma notícia de duas horas atrás
  muda o que uma frase significa, e nenhum treino sobre o material alcança isso.
  O custo dos dois erros é assimétrico — perder um corte bom custa um corte;
  publicar um que inverte o sentido de uma fala custa a conta.

---

## 5. A régua: o que conta como medir

Esta seção existe por causa de um episódio específico e ela é a mais importante
do documento para quem trabalha aqui.

Na versão 5.0 eu quebrei o caminho principal do corte. O perfil de energia é uma
lista de dicionários; eu escrevi código que o tratava como lista de números. **A
ferramenta ficou dois dias sem cortar.** A suíte de testes continuou verde o
tempo todo, porque o meu fixture usava o formato que eu imaginei em vez do
formato que a produção produz.

Disso saem quatro regras que não se negociam:

**Contar teste não é medir.** "480 testes passando" descreve quanto teste foi
escrito, não se o programa funciona. Um número que sobe sozinho a cada commit não
é sinal de saúde — é sinal de atividade. Quando o número de testes for citado
como evidência de qualidade, a frase está errada, venha de quem vier.

**Nenhum ciclo fecha sem exportar um MP4 de verdade.** Rodar a suíte é o piso, não
o teto. O ciclo fecha quando um arquivo existe no disco, com áudio, com legenda,
e alguém o abriu.

**O fixture tem que vir da produção.** Todo dado de teste que representa saída de
outro módulo é capturado de uma execução real, nunca escrito à mão a partir do
que o formato "deveria" ser. Foi exatamente a diferença entre os dois que
escondeu a quebra.

**Medida em fonte única é hipótese, não resultado.** Recall e precision medidos
num vídeo só descrevem aquele vídeo. Podem ser publicados, mas com a fonte
nomeada junto, sempre. E o número que eu produzi não vira verificado por ter
passado pelo relatório de outra pessoa — a origem continua sendo eu.

---

## 6. Como trabalhar

**Cada entrega:** hipótese → medir o estado atual → menor mudança que a testa →
medir de novo → teste que trava a regressão → export real → commit que conta o
porquê.

**Antes de cada entrega:** varredura de órfãos. Módulo importado sem ninguém
chamar, função pública sem chamador, dado calculado e descartado, elemento
removido do HTML com ouvinte pendurado, classe de CSS que nenhum código atribui.
Foi assim que o léxico ficou três versões sem estar ligado a nada, e foi assim
que o cursor de onça e o som ficaram inalcançáveis depois de eu anunciá-los.

**Ao consertar:** distinguir sintoma de causa. Os cortes de 180 segundos exatos
eram sintoma; a causa era a transcrição inteira indo numa requisição só e
estourando o tempo.

**Ao encontrar silêncio:** silêncio é defeito. Quando uma etapa devolve zero
resultados, ela diz o que faltou, em uma frase, na tela. "Nenhum bloco" sem
motivo já custou um relatório inteiro de investigação para descobrir que a fonte
tinha 15 frases e o mínimo eram 64.

**Documentação:** só quando muda comportamento, e dentro do commit. Nada de
relatório de ciclo, prompt de transferência ou registro de estado.

---

## 7. O que só o editor pode fazer

- Amostra limpa da voz do Renan.
- Pares de treino: o vídeo de origem, os trechos aprovados **e os rejeitados**,
  com o porquê em três palavras. Exemplo positivo sozinho não ensina fronteira.
- Grafia canônica de nome novo.
- O veredito sobre corte bom e corte ruim.
- Baixar os MP4 já publicados e largar numa pasta. O Furia não alcança o
  Instagram; a partir do arquivo local, o resto ele extrai sozinho.
- As headlines que ele mesmo escreveu, em texto. Uma lista de trinta headlines
  aprovadas vale mais para o gerador do que qualquer regra que eu deduza.

---

## 8. Como o Furia aprende

Ele não treina no sentido de gerar um modelo próprio. Ele **calibra** a partir de
decisões que já existem.

### 8.1 O que "aprender" significa aqui, e o que não significa

É preciso separar duas coisas que costumam ser confundidas, inclusive em
relatórios externos sobre este projeto.

**O que já existe** é um filtro estatístico: 517 vídeos do Acervo destilados em
priors que ajudam a reconhecer não-conteúdo — vinheta, saudação, ruído,
encerramento. Isso funciona e pesa decisões. **Não é aprender o gosto do editor.**

**O que não existe ainda** é qualquer coisa que capture a preferência dele. Zero.
Chamar o filtro de "aprendizado real funcionando" é confortável e falso.

**E o que é honestamente alcançável** com o volume de exemplos que ele consegue
produzir — dezenas, não milhares — é calibração de parâmetro, não treino de
modelo. Com vinte pares dá para aprender: de quanto ele costuma recuar a borda de
entrada, qual proporção ele escolhe por tipo de conteúdo, onde ele põe a legenda,
que duração ele prefere, que temas ele descarta. Não dá para aprender "o que é um
bom corte" em abstrato. Prometer o segundo produz uma ferramenta que erra com
confiança, que é o pior resultado possível.

### 8.2 A correção que muda o desenho: o corte final não é contínuo

O editor descreveu o próprio método:

> *"às vezes eu posso pegar uma parte do vídeo que está no final e literalmente
> colocar no segundo zero como hook."*

Isso invalida uma premissa que estava embutida em todo o desenho de aprendizado —
o meu e o de fora. Comparar "o corte do Furia" com "o corte final do editor"
medindo o deslocamento das bordas **só faz sentido se o corte final for um
intervalo contínuo da fonte.** Quando ele reordena, a comparação por tempo produz
um deslocamento enorme e sem significado, e o Furia "aprende" uma preferência de
borda que ninguém tem.

**A correção:** o comparador alinha por **conteúdo**, não por tempo. Cada frase do
corte final é casada com a frase de origem por impressão digital de áudio e por
texto. O resultado deixa de ser um número e passa a ser um mapa: quais trechos
sobreviveram, em que ordem foram montados, o que foi cortado do meio.

E o que esse mapa revela é mais valioso do que a borda: **quando uma frase que
estava aos 42 minutos vai para o segundo zero, aquilo é o gancho.** É o gesto
editorial que separa um corte que segura o espectador de um que não segura, e é
exatamente o que o Furia hoje não sabe procurar. Aprender a reconhecer que tipo de
frase o editor promove a gancho vale mais do que todas as outras calibrações
juntas.

### 8.3 As fontes, em ordem de quanto custam ao editor

**a) O ida e volta do CapCut — custo zero.**

O editor exporta um corte, edita no CapCut e reimporta no Furia para legendar.
Esse caminho de volta já está no fluxo. O Furia guarda a impressão digital do
áudio no que exportou e compara com o que voltou — pelo mapa de conteúdo descrito
acima, não pela diferença de duração.

É o melhor sinal disponível porque não custa um minuto: sai do trabalho normal,
sem formulário, sem o editor precisar lembrar de anotar nada.

O que ele **não** mede: alinhamento de texto, altura de faixa, tamanho de
headline. Quando o vídeo volta ele tem imagem, música e arte por cima —
visualmente é outro vídeo. O áudio ainda casa; a imagem não.

**b) Os MP4 já publicados — custo de baixar e largar numa pasta.**

De um corte publicado o Furia extrai a headline queimada por leitura de texto na
imagem, o estilo da legenda, as proporções da faixa medidas em pixels, e a fala
do trecho por transcrição.

Os dois últimos juntos formam o par que falta hoje: **isto foi dito → esta
headline foi escrita.** Dezenas ou centenas de exemplos reais, em vez de padrões
deduzidos de capturas de tela.

De brinde, as proporções exatas da arte saem medidas em vez de perguntadas, e
sai a resposta para uma pergunta que hoje é chute: 1:1, 3:4 ou 9:16, e em função
de quê.

Leitura de texto em fonte estilizada erra às vezes. O que sair duvidoso é marcado
como duvidoso, nunca apresentado como certo.

**c) Aprovado e reprovado, com motivo — custo de um arrastar.**

Cada corte exportado leva um arquivo irmão com a origem, os tempos, a transcrição
e os sinais da decisão; mover o vídeo de pasta vira o veredito, e o irmão carrega
o significado.

**O motivo é o que transforma isso em aprendizado.** Sem ele, "reprovado" é um bit
e o Furia não sabe se o problema foi a borda, o tema, a duração ou o locutor. O
desenho do motivo tem três camadas, e a ordem importa:

1. **Motivos de catálogo** — uma lista curta de causas que o sistema já sabe
   medir: *cortou cedo demais*, *cortou tarde demais*, *não é o Renan falando*,
   *tema fraco*, *já publicamos isso*, *sem gancho*. Cada uma tem um parâmetro
   correspondente do outro lado. Escolher da lista é um clique e produz
   calibração imediata, sem ninguém interpretar nada.
2. **Motivo escrito livre** — guardado em texto, junto do corte. Não vira
   parâmetro sozinho; vira material de leitura quando um padrão se repetir.
3. **A tradução do texto em regra** — hoje passa por mim; depois pode passar por
   um modelo local. Essa é a única parte do laço que ainda precisa de gente, e o
   editor já sabe disso e aceitou.

**O que nenhuma das três alcança** é o erro por omissão: o corte bom que o Furia
nunca propôs. Para isso ele registra o que ficou em segundo e terceiro lugar, e
o editor olha a lista de vez em quando — padrão de cegueira aparece rápido assim.

### 8.4 Assistir e ser corrigido

O editor descreveu um quarto modo, mais ambicioso: o Furia assiste a um corte já
aprovado, escreve o que entendeu, e ele aprova, corrige ou reprova aquele
entendimento.

Vale registrar porque é a forma mais eficiente de usar o tempo dele — corrigir um
texto de três linhas é mais rápido que preencher um formulário — e porque tem uma
armadilha específica: **o entendimento tem que ser verificável.** "Este corte fala
sobre segurança pública" não é corrigível de forma útil. "Este corte começa na
pergunta do jornalista aos 12:04, a tese aparece aos 12:19, e fecha na conclusão
aos 12:41" é. O Furia descreve o que mediu, não o que achou. Correção sobre
medida vira parâmetro; correção sobre impressão vira nada.

---

## 9. A headline

O editor nomeou isto como gargalo diário, e é a parte da ferramenta com a maior
distância entre o que está prometido e o que está construído.

### 9.1 O estado real, sem eufemismo

O `headline_studio.py` não gera headline. Ele é uma cadeia de condições fixas
extraídas de um vídeo específico sobre criptomoedas:

```python
if "caminho arcaico" in folded:
    candidates.append("BRASIL ESCOLHEU O CAMINHO ARCAICO")
if "reserva de valor" in folded and topic == "cripto":
    candidates.append("CRIPTOS SÃO O FUTURO DA RESERVA DE VALOR")
```

Para qualquer fonte nova ele cai no genérico — `"A VERDADE INCÔMODA SOBRE
{TEMA}"`. A rota de feedback existe e funciona; o que ela realimenta não existe.
Substituir isto é trabalho de construção, não de ajuste.

O formato "fake tweet" sai: o editor pediu para descartá-lo e ele continua no
módulo, na interface e no seletor de formato.

### 9.2 A forma, tirada de uma headline aprovada

Do exemplo que o editor produziu e aprovou:

> **VERGONHA!**
> **RENAN SANTOS DETONA: "Janja com louvor evangélico pra fingir que gosta de crente"**

Três partes, e cada uma tem uma função distinta:

| parte | exemplo | função | de onde sai |
|---|---|---|---|
| **estampa** | `VERGONHA!` | dá a emoção antes da leitura | do tom medido do trecho |
| **atribuição** | `RENAN SANTOS DETONA:` | diz quem fala e com que força | do veredito de locutor |
| **citação** | `"Janja com louvor..."` | é o conteúdo, e é literal | da transcrição, verbatim |

A parte difícil já está resolvida: a citação **tem que ser literal**, e o
invariante do áudio como verdade mais o timestamp por segmento já garantem isso.
O que falta é a montagem — escolher qual frase do trecho vira citação, qual verbo
de atribuição cabe naquele tom, e qual estampa a força do trecho justifica.

**A citação nunca é parafraseada.** Se a frase mais forte não couber no limite de
caracteres, corta-se pelo fim com reticências, ou escolhe-se outra frase. Nunca
se reescreve o que ele disse para caber.

**A atribuição segue o veredito de locutor.** Verbo forte com nome próprio só
quando o áudio confirmou. Sem confirmação, a headline sai sem atribuição ou não
sai — nunca com atribuição chutada.

### 9.3 O que o desempenho real mostra

Medido no Campaign Hub sobre 983 publicações do `@renansantosmbl` no Instagram em
2026, olhando a primeira linha da legenda:

| tamanho da primeira linha | publicações | mediana de views |
|---|---|---|
| até 30 caracteres | 372 | 610.087 |
| 31–45 | 301 | 592.147 |
| 46–60 | 173 | 510.237 |
| 61 ou mais | 137 | 393.104 |

Monotônico, dentro de um único ano, com amostra grande: **da faixa mais curta para
a mais longa a mediana cai 36%.** Curto vence.

Na comparação por quartil de views, três outros sinais aparecem, todos na mesma
direção:

- **pergunta** — 24% das legendas do quartil mais visto terminam em interrogação,
  contra 18% do menos visto;
- **primeira pessoa** (`eu`, `vou`, `fui`, `nosso`, `vamos`) — 11% contra 7%;
- **caixa alta** — 8% no quartil mais visto contra 23% no menos visto. Dentro de
  2026, publicações com palavra em caixa alta na primeira linha tiveram média de
  668 mil views contra 776 mil das sem. Em 2025 a diferença foi maior: 186 mil
  contra 301 mil.

**Três ressalvas, e elas não são formalidade.** Primeira: isto é a legenda do
Instagram, não a headline queimada na arte — a arte é em caixa alta por design e
esses números não a contradizem. Segunda: correlação não é causa; views dependem
de assunto, momento e algoritmo muito mais do que de tipografia. Terceira: são
padrões de uma conta, não leis.

O que eles autorizam, então, é **preferência, nunca portão**: entre duas headlines
igualmente fiéis ao que foi dito, o gerador prefere a mais curta, aceita bem a que
termina em pergunta e não grita por padrão no texto da legenda. Nenhuma headline é
rejeitada por ter 62 caracteres.

### 9.4 Como se sabe que ficou bom

O critério é o do editor e é simples: **ele edita em vez de reescrever.** Enquanto
a maioria das headlines geradas for jogada fora e escrita do zero, a etapa 2 não
fechou, independentemente do que qualquer métrica interna diga.

---

## 10. Onde o conhecimento mora, e como ele viaja

O editor atualiza substituindo a pasta do programa inteira, e usa dois notebooks.
As duas coisas afetam o mesmo problema.

**O que já está resolvido.** Tudo que ele produz vive em `~/FuriaClipsData`, fora
do checkout: banco de decisões, projetos, transcrições, calibração, acervo, a voz
cadastrada. Substituir a pasta do GitHub não toca nisso. Foi decisão deliberada
de quem construiu, e o comentário no `config.py` diz o porquê.

**O que estava quebrado e foi corrigido.** Os cortes exportados nasciam em
`workspace/exports`, dentro da pasta do programa. Sumiam a cada atualização — e
levariam junto o arquivo irmão de cada corte, que é o que torna o aprendizado por
aprovação possível. `PERSISTENT_EXPORTS_DIR` já existia, já era criado, e nada
escrevia nele. Agora escreve.

**O que falta: sincronizar as duas máquinas.** O desenho:

- **O canal é um repositório privado só de dados**, separado do código. Não é o
  repositório do programa: código e evidência têm ciclos diferentes, e misturar
  os dois faz cada atualização de código carregar megabytes de decisão.
- **Ao abrir, o Furia tenta buscar.** Conseguiu, funde. Não conseguiu — sem
  internet, sem credencial, o que for — roda com o que tem local e diz isso na
  interface, sem travar nada.
- **A fusão é por registro, nunca por sobrescrita.** As duas máquinas geram
  decisões em paralelo; o último a subir não pode apagar o trabalho do outro.
  Cada decisão tem identidade própria e as duas listas se juntam.
- **Enviar é explícito e também automático ao fechar.** Botão para quando a
  internet voltar, e envio ao encerrar o dia para o caso de ele esquecer.
- **Aprovar ou rejeitar um corte já entra na fila de envio**, sem etapa extra.
- **Vídeo não sobe.** Só a decisão, os tempos, a transcrição e a calibração. O
  arquivo pesado fica na máquina; o que ensina é leve.
- **Chave de API nunca sobe.** Ela mora fora do checkout e fora do canal.

### Onde entram o Campaign Hub, os blocos e o site de cortes

São três nomes para dois papéis, e vale separar.

**O Campaign Hub é memória de desempenho.** Ele sabe quem são as pessoas, que
papel cada uma cumpre no material, e o que rendeu view nas contas. Só existe na
sessão do agente, nunca na máquina do editor — então o Furia offline jamais o
consulta ao vivo. O caminho real é: o agente consulta, gera um arquivo, comita, o
editor puxa. Foi assim que as 337 entidades com papel chegaram, e foi assim que
os números da seção 9.3 chegaram. "Atualização constante" aqui significa "toda vez
que conversarmos", e é honesto dizer isso em vez de prometer um fluxo que não
existe.

O que ainda dá para trazer de lá, e ainda não veio:

- **as legendas que renderam**, como exemplos de forma para o gerador de headline;
- **o papel de cada entidade** já está no Furia, mas não está sendo usado para
  sugerir imagem de apoio — "Janja citada, papel adversário, tom de confronto"
  é informação suficiente para propor uma imagem de arquivo, e é texto, não pixel;
- **o que já foi publicado**, para o Furia avisar quando um trecho repete um corte
  que já saiu.

**Os blocos do Acervo são leitura revisada por pessoa.** Quando existem para uma
fonte, ganham de qualquer heurística: alguém checou as bordas e escreveu o
título. Hoje entram por importação manual de um arquivo por vídeo. Devem passar a
viajar pelo mesmo canal de sincronismo, para valerem nos dois notebooks sem o
editor importar duas vezes.

**O site de cortes da Missão é a frente do Campaign Hub.** Não é uma terceira
fonte: o que ele mostra são os mesmos blocos. O que o Furia pode aproveitar dele
é a busca — achar, por palavra, todos os vídeos do acervo que falam de um assunto,
e trazer os blocos correspondentes. Isso é conveniência de pauta, não de corte, e
por isso vem depois do resto.

---

## 11. Etapa 4, desenhada

O editor descreveu duas pastas: uma para o que aprova, outra para o que rejeita.
O gesto é ótimo — arrastar um arquivo é o feedback de menor atrito que existe.

**O furo:** um MP4 final não diz de onde veio nem por que foi rejeitado. Analisar
o arquivo pronto ensina quase nada.

**A correção:** todo corte exportado sai com um arquivo irmão que carrega a
origem, os tempos, a transcrição do trecho, os sinais que entraram na decisão e
o que foi descartado no caminho. Aí mover o vídeo para uma pasta **é** o
feedback, e o arquivo irmão carrega o significado.

O laço fica assim:

1. a live termina e é baixada;
2. o Furia processa sem interface;
3. os cortes saem com o arquivo irmão;
4. uma revisão automática confere forma — duração, áudio, legenda, enquadramento,
   nome escrito errado — e devolve o que falhar, com limite de tentativas;
5. o que passa vai para a pasta de revisão e avisa no WhatsApp;
6. o editor arrasta para **aprovado** ou **reprovado**, e escolhe um motivo da
   lista curta se quiser;
7. o n8n lê as duas pastas e devolve os arquivos irmãos como calibração.

**Restrições reais:** o Furia roda no notebook pessoal onde o editor edita, então
o trabalho automático não pode disputar a máquina com ele — processamento pesado
espera ou cede prioridade. E o notebook dorme: o que a etapa 4 alcança é
"processar quando a máquina estiver ligada", não "vigiar 24 horas". Se um dia
houver máquina dedicada, o mesmo desenho serve sem mudança.

**A exceção que entra antes.** Duas coisas da etapa 4 custam pouco e servem ao
editor hoje, então não esperam:

- **entrada por arquivo local na rota de ingestão.** Hoje `/api/source/import`
  exige URL pública, e ele baixa MP4 do Instagram à mão. É fricção diária, e a
  correção é pequena.
- **cookies do navegador para o download público.** O anti-bot do YouTube não vai
  embora; usar a sessão do navegador logado é o que existe de remédio.

---

## 12. Design

O CHUB foi cedido pelo chefe do editor, e o site é frio e mal acabado. O Furia
precisa causar a impressão contrária — inclusive antes de estar pronto. Aparência
não é enfeite aqui: é o que faz alguém confiar numa ferramenta que ainda erra, e é
o que faz o editor querer abri-la de manhã.

Isto é item de primeira classe do projeto, não acabamento para o fim.

### 12.1 O diagnóstico honesto

O editor foi direto e estava certo:

> *"toda a experiência visual e incrível de um site lindo não existe 😕"*

Duas vezes eu anunciei reformulação visual e entreguei **organização**: escala
tipográfica, espaçamentos consistentes, uma barra de execução, cores nomeadas.
Nada disso é errado e nada disso é o que ele pediu. Organização evita irritação;
não produz encanto. A diferença é a distância entre uma planilha bem formatada e
algo que dá vontade de mostrar para alguém.

O que está errado hoje, nomeado:

- **O tempo de espera é vazio.** O editor espera minutos e recebe texto rolando
  num console. É o momento mais longo da experiência e o menos desenhado.
- **A tela conta tudo e não comunica nada.** Excesso de informação simultânea,
  sem hierarquia que diga onde olhar.
- **Nada acontece entre um estado e outro.** Painéis trocam de conteúdo de forma
  abrupta; o editor não entende o que mudou nem por quê.
- **A barra lateral tem controles que ele nunca usou.** Ocupam espaço e sugerem
  complexidade que não existe.
- **Não há um único momento memorável.** Nenhuma tela que ele mostraria a alguém.

### 12.2 A ideia central: a linha do tempo é a protagonista

Um dashboard genérico com cartõezinhos não vai encantar ninguém, e copiar
tendência de dashboard premiado produz uma tela bonita e anônima. O que torna esta
ferramenta específica é que ela tem **um objeto próprio**: duas horas de fala
transformadas em conhecimento.

Então a tela é organizada ao redor de **uma faixa horizontal que é a fonte
inteira**, do primeiro ao último segundo. Tudo o mais orbita.

- **Enquanto o Furia trabalha, a faixa preenche.** Não é uma porcentagem
  abstrata: é o vídeo sendo ouvido da esquerda para a direita, e o editor vê
  exatamente onde a ferramenta está. Uma barra de 62% não diz nada; uma faixa
  preenchida até um terço com blocos já aparecendo diz tudo.
- **Os blocos temáticos nascem sobre ela**, cada um com sua cor de veredito —
  verde, âmbar, vermelho — e seu título. Aparecem conforme são descobertos, não
  todos de uma vez no fim.
- **Os candidatos aparecem como marcas embaixo**, na posição exata de onde saíram.
  A relação entre "o Furia entendeu a fonte assim" e "por isso propôs estes
  cortes" fica visível de uma olhada, sem ninguém explicar.
- **Clicar num bloco abre-o no lugar**, com a proposta de corte, o motivo e o
  texto. Arrastar a borda move o corte e o texto acompanha em tempo real.
- **Passar o mouse sobre um candidato mostra o quadro daquele instante.**

Isso é ao mesmo tempo o elemento mais bonito e o mais informativo da tela, e não
existe em nenhuma ferramenta concorrente — porque nenhuma delas tenta mostrar o
que entendeu antes de cortar.

### 12.3 Os três momentos que carregam a impressão inteira

Design de ferramenta não se distribui por igual. Três momentos definem a
percepção; o resto precisa apenas não atrapalhar.

**Momento 1 — a chegada.** Os primeiros dois segundos, antes de qualquer clique.
O que se vê: o nome, o estado da máquina em uma linha honesta (motor local pronto,
voz cadastrada ou não, quantos cortes hoje), e um único caminho óbvio para
começar. Nada de painel de configuração, nada de oito controles. Se ele voltou no
meio de um trabalho, o trabalho está ali, retomável, sem procurar.

**Momento 2 — a espera.** O mais longo e o mais negligenciado. Uma fonte de duas
horas leva mais de uma hora para transcrever numa máquina sem placa de vídeo. Isso
não é consertável por design — mas a experiência de esperar é.

A espera deixa de ser um console e passa a ser **narração do que está sendo
descoberto**:

- etapas nomeadas em português direto — *baixando · ouvindo · entendendo ·
  escolhendo · cortando* — com a atual em destaque e as anteriores marcadas;
- barra determinística com porcentagem e **tempo restante recalculado**, nunca uma
  barra parada que parece travada;
- e, acima de tudo, **o achado**: "23 minutos ouvidos", "quarto bloco: emendas
  parlamentares", "primeiro candidato: 1:12:40". A faixa preenchendo com blocos
  aparecendo é a barra de progresso mais informativa possível.

Uma espera que mostra descoberta deixa de ser espera e vira acompanhamento.

**Momento 3 — a entrega.** Os cortes chegam. Aqui vale o único gesto de reveal do
programa: os cartões assentam em sequência rápida — não um por um lentamente, mas
uma cascata de 400 ms no total — cada um já com sua headline, sua duração e sua
cor de veredito. É a recompensa do tempo esperado e é o momento que ele mostraria
para alguém.

Cada cartão é **o corte, não uma linha de tabela**: quadro representativo, a
headline em tamanho de leitura, duração, veredito com palavra, e a frase que
justifica. Aprovar, reprovar e ajustar a borda estão ali, sem abrir outra tela.

### 12.4 O sistema visual

**Um acento só.** Uma cor saturada contra uma paleta dessaturada, reservada para a
ação principal e para a marca. O dourado da Missão é esse acento. Quando ele
aparece em título, ícone, borda e botão ao mesmo tempo, nada é destaque — foi o
que fazia a tela parecer amadora. O vermelho fica reservado para confronto e erro;
nunca decora.

**O dourado como sistema, não como cor solta.** Tudo deriva de um punhado de
variáveis: fundo, superfície, tinta, tinta apagada, acento, acento apagado, os
três de veredito. Foco de teclado em dourado. Borda de seleção de corte em
dourado. Estado ativo em dourado apagado. Se uma cor aparece escrita direto num
componente, é defeito.

**Hierarquia por tamanho, não por cor.** O que mais importa é o maior elemento da
tela. Três níveis e só três: título, unidade, apoio. Colorir tudo para diferenciar
é o atalho que produz poluição.

**Contraste calibrado para sessão longa.** Preto puro sobre monitor grande lê como
buraco e cansa; branco puro sobre preto vibra. O fundo tem traço quente — quase
preto com um resto de marrom, não `#000` — e o texto fica levemente abaixo do
branco puro. Isso sustenta horas de trabalho e, de quebra, é o que os bons
produtos escuros de 2026 fazem.

**Movimento curto e uniforme.** Uma duração e uma curva para toda a interface.
Durações diferentes por componente fazem a tela parecer montada por pessoas
diferentes. Nada acima de 200 ms em elemento que o editor usa toda hora — a
exceção é a cascata de entrega, que é um momento e não uma interação.

**Densidade é escolha, não acidente.** Cada tela mostra o que serve à decisão
daquele instante. O que é diagnóstico vive atrás de um "ver detalhes". A
reclamação de "excesso de informação desnecessária" se resolve tirando, não
reorganizando.

**Estado sempre visível.** Carregando, vazio, erro e sucesso são estados de
projeto, não improviso. Um painel em branco enquanto pensa parece travado. Um
painel vazio sem explicação parece quebrado — e às vezes está, como no caso dos
zero blocos sem motivo.

### 12.5 As assinaturas

**Cursor de onça:** sim, mas contextual e desligável. Um cursor personalizado
ligado o tempo todo atrapalha — atrasa em relação ao ponteiro do sistema, some
sobre campo de texto e cansa em jornada longa. Ligado **enquanto o editor arrasta
na linha do tempo ou reposiciona a borda de um corte**, ele vira assinatura em vez
de obstáculo, e some quando não serve.

**Som:** desligado por padrão, um único toque curto ao terminar processo longo, e
um botão para calar. Ferramenta que apita sem permissão é desinstalada.

**Ambos precisam estar alcançáveis.** Já foram anunciados uma vez apontando para
classes de CSS que nenhum código atribuía. A varredura de órfãos da seção 6 existe
por causa disso.

**Não fica:** animação de entrada em cada bloco, brilho pulsante decorativo,
sombra colorida, mais de um acento, ícone que não é clicável. Cada um parece
impressionante na primeira vez e irrita na centésima.

### 12.6 Acessibilidade não é opcional

`prefers-reduced-motion` respeitado — e respeitado de verdade, incluindo a cascata
de entrega. Foco de teclado visível em todo elemento interativo. Contraste mínimo
cumprido. E **nenhuma informação transmitida só por cor**: verde, âmbar e vermelho
sempre acompanhados de palavra.

### 12.7 Como se sabe que ficou bom

Duas perguntas, e nenhuma delas é sobre CSS:

1. **O editor entende, sem ler o console, o que a ferramenta está fazendo agora e
   quanto falta?**
2. **Existe pelo menos uma tela que ele mostraria para outra pessoa?**

Enquanto a resposta à segunda for não, esta seção não fechou — por mais tokens,
escalas e espaçamentos que existam no CSS.

---

## 13. Os blocos precisam ser úteis, não só existir

O sistema de blocos, a leitura da fonte e o contexto já funcionam. Falta o que
transforma isso em ferramenta: **o bloco tem que sugerir o corte.**

Clicar num bloco deve responder, ali mesmo:

- **de onde até onde cortar**, com a borda já caindo numa costura da conversa;
- **por que ali** — a pergunta que abre, a tese, a frase que fecha;
- **quem fala**, e com que confiança;
- **o que enfraquece** — termina antes da conclusão, alguém de fora fala no meio,
  nome citado que a legenda pode ter errado;
- **quanto vale**, comparado ao resto da fonte.

E o editor deve poder ajustar a borda arrastando, com o texto acompanhando, sem
sair da tela.

**A precisão do contexto é a condição de tudo isso.** Um bloco que sugere um corte
errado é pior que um bloco que não sugere nada: ensina a desconfiar da sugestão e
o editor volta a percorrer o vídeo inteiro à mão. Por isso a sugestão só aparece
quando as medições fecham, e quando não fecham o bloco diz o que faltou em vez de
chutar.

---

## 14. Onde estamos

Etapa 1, quase no fim, e com uma dívida recente: a quebra da 5.0 mostrou que
"quase no fim" estava sendo medido por suíte verde em vez de corte real.

**O que existe e foi verificado rodando:** costuras da conversa, blocos da fonte,
correção de nome com 337 entidades vindas do Campaign Hub, reconhecimento de voz
por áudio, energia alimentando a decisão, guarda contra duas ações ao mesmo tempo,
supressão de candidatos irmãos, descarte de não-conteúdo, teto no alongamento de
pergunta.

**A borda do corte, medida em duas fontes reais (6.3).** Na sabatina do SBT
completa, 602 segmentos: 15 cortes, nenhum abrindo no meio da fala, nenhum
fechando em conjunção pendurada, nenhum dentro da apresentação do estúdio. Na
entrevista do Metrópoles, sobre as 455 linhas de legenda que a corrida do editor
gravou: cortes abrindo no meio da fala caíram de 5 em 8 para 1 em 10.

A causa raiz não estava na seleção e vale registrar, porque ela vai reaparecer em
outra forma: **uma linha de legenda não é uma frase.** O YouTube quebra a linha
onde ela encheu, então o ponto final cai no meio dela, e o construtor de sentenças
só fechava uma sentença quando o texto acumulado terminava em ponto. Toda sentença
da fonte nascia com o rabo da anterior pendurada, e isso envenenava tudo o que lê
sentença: a costura da conversa, a detecção de turno, o texto do corte e as duas
bordas. Onde houver um passe que dependa de fronteira de frase, a primeira
pergunta é se a fronteira é real.

**O que não existe ainda:** gerador de headline de verdade, composição com
headline e faixa, enquadramento guiado por voz, corte de silêncio ligado ao fluxo,
sincronismo entre as duas máquinas, caminho sem interface, entrada por arquivo
local, aprendizado com o gosto do editor, e a experiência visual da seção 12.

**Dívidas conhecidas, todas contornáveis pelo editor hoje.** Estão aqui para não
serem redescobertas, não para interromper o item 1:

- **A tela não sai de "Processando" quando o job falha.** O editor apertou parar
  três vezes depois de o trabalho já ter morrido no erro. Não é o cancelamento que
  trava; é o estado da tela que não acompanha o fim do job.
- **O download público é recusado com HTTP 403.** É o item 4 abaixo, e o editor
  baixa por fora enquanto isso.
- **O Whisper local morre em `cublas64_12.dll` em vez de voltar para a CPU.**
  Escolher CUDA e não achar a biblioteca tem de degradar, não abortar.
- **A voz cadastrada não decidiu nada.** Numa fonte inteira: zero cortes com a voz
  reconhecida, zero com outra voz, oito sem decisão pelo áudio. Ou ela decide, ou
  para de ser pedida — cadastrar custa um passo do editor e devolveu nada.
- **O log promete mais do que o resultado faz.** "Escutando e observando a fonte
  para validar o cenário, tom e participantes" descreve um envio que, quando
  funciona, apenas *anota* cortes já escolhidos, com confiança limitada enquanto a
  identidade da fonte não é validada — ele não escolhe corte nenhum. Em três
  corridas seguidas ele caiu em 503 e custou de quatro a seis minutos cada. Um log
  que promete mais do que entrega é a mesma doença do relatório de ciclo.
- **Som e notificação ao terminar não existem como item.** Uma fonte de duas horas
  transcreve por mais de uma hora; o editor sai da máquina e não tem como saber
  que acabou. Entra na seção 12, junto da espera.

**A ordem de trabalho**, e a justificativa de cada posição:

1. **Qualidade do corte na fonte real** — é a razão de existir da ferramenta, e é
   o que a quebra da 5.0 deixou por confirmar. As bordas fecharam na 6.3 nas duas
   fontes medidas; o que continua aberto é o julgamento que nenhuma medida minha
   alcança — se o raciocínio terminou. Isso só o editor decide, e é por isso que o
   item 3 sustenta este item.
2. **Gerador de headline** — gargalo diário declarado pelo editor; a parte difícil
   (citação literal) já está resolvida.
3. **Aprovar, reprovar e o motivo** — é o que faz 1 e 2 melhorarem sem mim.
4. **Entrada por arquivo local e cookies do download** — barato, serve hoje.
5. **Silêncio virar mensagem** — todo zero explica seu motivo.
6. **A experiência da seção 12** — começando pela espera e pela linha do tempo.
7. **Caminho sem interface, n8n, rosto, diarização** — a etapa 4, depois que a 1
   fechar de verdade.
