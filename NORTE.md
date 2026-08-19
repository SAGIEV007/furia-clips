# Norte do Furia Clips

Este é o documento de direção. Ele é curto de propósito.

O projeto já teve 120 KB de prompts de continuidade, escritos porque cada sessão
de IA perdia a memória e a seguinte precisava ser reconstruída do zero. Quarenta
e quatro por cento dos commits daquela fase eram só documentação. Uma sessão
nova gastava metade do fôlego lendo sobre si mesma antes de tocar em qualquer
coisa, e três capacidades foram construídas, medidas, documentadas e nunca
ligadas a nada — porque o contexto acabava antes.

Um norte de trinta páginas repetiria exatamente esse erro. Este cabe numa tela.

---

## 1. O que a ferramenta é

Um cortador **especialista** em Renan Santos, MBL e Partido Missão. Não é um
cortador genérico apontado para um tema: é uma ferramenta que conhece essas
pessoas, esse vocabulário, esse público e o que já funcionou nessas contas.

O trabalho real do editor é escolher, de duas horas de material, os três minutos
que valem. Tudo o mais é consequência disso.

**Meta:** sair de 10 cortes por dia feitos à mão para 20–30 por dia, sem perder
qualidade editorial. Velocidade que custa credibilidade não serve.

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

## 4. Invariantes

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

## 5. Como trabalhar

**Cada entrega:** hipótese → medir o estado atual → menor mudança que a testa →
medir de novo → teste que trava a regressão → commit que conta o porquê.

**Antes de cada entrega:** varredura de órfãos. Módulo importado sem ninguém
chamar, função pública sem chamador, dado calculado e descartado, elemento
removido do HTML com ouvinte pendurado. Foi assim que o léxico ficou três
versões sem estar ligado a nada.

**Ao consertar:** distinguir sintoma de causa. Os cortes de 180 segundos exatos
eram sintoma; a causa era a transcrição inteira indo numa requisição só e
estourando o tempo.

**Documentação:** só quando muda comportamento, e dentro do commit. Nada de
relatório de ciclo, prompt de transferência ou registro de estado.

---

## 6. O que só o editor pode fazer

- Amostra limpa da voz do Renan.
- Pares de treino: o vídeo de origem, os trechos aprovados **e os rejeitados**,
  com o porquê em três palavras. Exemplo positivo sozinho não ensina fronteira.
- Grafia canônica de nome novo.
- O veredito sobre corte bom e corte ruim.
- Baixar os MP4 já publicados e largar numa pasta. O Furia não alcança o
  Instagram; a partir do arquivo local, o resto ele extrai sozinho.

---

## 7. Como o Furia aprende

Ele não treina no sentido de gerar um modelo próprio. Ele **calibra** a partir de
decisões que já existem. Três fontes, em ordem de quanto custam ao editor:

**a) O ida e volta do CapCut — custo zero.**

O editor exporta um corte, edita no CapCut e reimporta no Furia para legendar.
Esse caminho de volta já está no fluxo. O Furia guarda a impressão digital do
áudio no que exportou e compara com o que voltou: a duração mudou, e de que lado;
o começo foi aparado; o arquivo nunca voltou.

É aprendizado de **borda**, que é justamente o que mais erra. E é o melhor sinal
disponível porque não custa um minuto: sai do trabalho normal, sem formulário,
sem o editor precisar lembrar de anotar nada.

O que ele **não** mede: alinhamento de texto, altura de faixa, tamanho de
headline. Quando o vídeo volta ele tem imagem, música e arte por cima —
visualmente é outro vídeo. O áudio ainda casa; a imagem não.

**b) Os MP4 já publicados — custo de baixar e largar numa pasta.**

De um corte publicado o Furia extrai a headline queimada por leitura de texto na
imagem, o estilo da legenda, as proporções da faixa medidas em pixels, e a fala
do trecho por transcrição.

Os dois últimos juntos formam o par que falta hoje: **isto foi dito → esta
headline foi escrita.** Dezenas ou centenas de exemplos reais, em vez de padrões
deduzidos de capturas de tela. É o que dá ao gerador o mesmo material que uma
pessoa tem ao escrever uma headline boa: o argumento inteiro e o que se escolheu
destacar dele.

De brinde, as proporções exatas da arte saem medidas em vez de perguntadas.

Leitura de texto em fonte estilizada erra às vezes. O que sair duvidoso é marcado
como duvidoso, nunca apresentado como certo.

**c) Aprovado e reprovado — custo de um arrastar.**

Descrito na etapa 4. Cada corte exportado leva um arquivo irmão com a origem, os
tempos, a transcrição e os sinais da decisão; mover o vídeo de pasta vira o
veredito, e o irmão carrega o significado.

**O que nenhuma das três alcança** é o erro por omissão: o corte bom que o Furia
nunca propôs. Para isso ele registra o que ficou em segundo e terceiro lugar, e
o editor olha a lista de vez em quando — padrão de cegueira aparece rápido assim.

---

## 8. Onde o conhecimento mora, e como ele viaja

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
editor puxa. Foi assim que as 337 entidades com papel chegaram. "Atualização
constante" aqui significa "toda vez que conversarmos", e é honesto dizer isso em
vez de prometer um fluxo que não existe.

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

**A regra que vale para os três:** nenhum campo vindo de fora aprova um corte
sozinho, e nenhuma métrica histórica compensa um portão de contexto, transcrição,
locutor ou evidência. Eles informam; quem decide é a leitura do trecho.

---

## 9. Etapa 4, desenhada

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
2. o Furia processa sem interface — é isto que torna o n8n possível, e por isso
   o caminho sem tela é pré-requisito da etapa 3, não da 4;
3. os cortes saem com o arquivo irmão;
4. uma revisão automática confere forma — duração, áudio, legenda, enquadramento,
   nome escrito errado — e devolve o que falhar, com limite de tentativas;
5. o que passa vai para a pasta de revisão e avisa no WhatsApp;
6. o editor arrasta para **aprovado** ou **reprovado**;
7. o n8n lê as duas pastas e devolve os arquivos irmãos como calibração.

**Restrições reais:** o Furia roda no notebook pessoal onde o editor edita, então
o trabalho automático não pode disputar a máquina com ele — processamento pesado
espera ou cede prioridade. E o notebook dorme: o que a etapa 4 alcança é
"processar quando a máquina estiver ligada", não "vigiar 24 horas". Se um dia
houver máquina dedicada, o mesmo desenho serve sem mudança.

---

## 10. Design e experiência de uso

O CHUB foi cedido pelo chefe do editor, e o site é frio e mal acabado. O Furia
precisa causar a impressão contrária — inclusive antes de estar pronto. Aparência
não é enfeite aqui: é o que faz alguém confiar numa ferramenta que ainda erra.

Isto é item de primeira classe do projeto, não acabamento para o fim.

### Os princípios, e por que cada um

Levantados de como as boas interfaces escuras de 2026 são construídas, e
filtrados pelo que serve a alguém que passa horas na tela.

**Um acento só.** Uma cor saturada contra uma paleta dessaturada, reservada para
a ação principal e para a marca. O dourado da Missão é esse acento. Quando ele
aparece em título, ícone, borda e botão ao mesmo tempo, nada é destaque — foi o
que fazia a tela parecer amadora.

**Hierarquia por tamanho, não por cor.** O que mais importa é o maior elemento da
tela. Métrica secundária, gráfico e tabela descem em tamanho e peso. Colorir tudo
para diferenciar é o atalho que produz poluição.

**Contraste calibrado para sessão longa.** Preto puro sobre monitor grande lê como
buraco e cansa; branco puro sobre preto vibra. Fundos com traço quente e texto
levemente abaixo do branco puro sustentam horas de trabalho.

**Movimento curto e uniforme.** Uma duração e uma curva para toda a interface.
Durações diferentes por componente fazem a tela parecer montada por pessoas
diferentes. Nada acima de 200 ms em elemento que o editor usa toda hora.

**Estado sempre visível.** Carregando, vazio, erro e sucesso são estados de
projeto, não improviso. Um painel que fica em branco enquanto pensa parece
travado.

### O que fica e o que não fica

**Fica:** resposta ao passar o mouse em tudo que é clicável; foco visível para
teclado; barra de rolagem discreta; transição suave entre as áreas; som curto e
opcional no fim de um processo longo; notificação que carrega a ação.

**Cursor de onça:** sim, mas contextual. Um cursor personalizado ligado o tempo
todo atrapalha — atrasa em relação ao ponteiro do sistema, some sobre campo de
texto e cansa em jornada longa. Ligado **enquanto o editor arrasta na linha do
tempo ou reposiciona a borda de um corte**, ele vira assinatura em vez de
obstáculo, e some quando não serve.

**Não fica:** animação de entrada em cada bloco, brilho pulsante decorativo,
sombra colorida, mais de um acento. Cada um desses parece impressionante na
primeira vez e irrita na centésima.

**Som:** desligado por padrão, um único toque curto ao terminar processo longo, e
um botão para calar. Ferramenta que apita sem permissão é desinstalada.

### Acessibilidade não é opcional

`prefers-reduced-motion` respeitado, foco de teclado visível, contraste mínimo
cumprido, e nenhuma informação transmitida só por cor — verde, âmbar e vermelho
sempre acompanhados de palavra.

---

## 11. Os blocos precisam ser úteis, não só existir

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

## 12. Onde estamos

Etapa 1, quase no fim. Falta confirmar em fonte real que as bordas melhoraram e
que o caminho de qualidade parou de desabar.

O que já existe e funciona: costuras da conversa, blocos da fonte, correção de
nome com 337 entidades vindas do Campaign Hub, reconhecimento de voz por áudio,
energia alimentando a decisão, leitura de cena que termina em vídeo longo,
guarda contra duas ações ao mesmo tempo.

O que não existe ainda: composição com headline e faixa, enquadramento guiado por
voz, corte de silêncio ligado ao fluxo, sincronismo entre as duas máquinas,
caminho sem interface, e o gerador de headline com a qualidade que o editor
aprovou à mão.
