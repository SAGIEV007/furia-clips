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

## 8. Etapa 4, desenhada

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

## 9. Interface

Ela precisa passar credibilidade antes de estar completa.

- **Uma coisa de cada vez.** Enquanto há trabalho rodando, a interface diz o quê,
  há quanto tempo, e não aceita clique que vai descartar.
- **Toda notificação carrega a ação.** "7 cortes prontos · revisar", não "processo
  concluído". Aviso sem ação vira ruído e em duas semanas é ignorado.
- **Quanto mais automático, mais o Furia se explica.** Cada corte responde "por
  que este trecho?" em uma linha. Sem isso, automação vira desconfiança e o
  editor volta a conferir tudo à mão.
- **Preto, dourado e branco** — as cores da Missão. O dourado é acento, não
  pintura: quando tudo é destaque, nada é.
- **Só mostrar o que é usado.** Todo controle na tela deve chegar a algum lugar no
  servidor. Três não chegavam e saíram.

---

## 10. Onde estamos

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
