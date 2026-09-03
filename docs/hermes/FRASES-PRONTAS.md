# As frases prontas

O que mandar no WhatsApp, palavra por palavra. Sem inventar comando.

Elas são curtas **porque** as instruções longas já estão no disco: a carta, o
quadro de aviso e as skills. Você diz o quê; elas dizem o como.

---

## Para ele trabalhar sozinho

> **Entre em modo autônomo e fique nele até eu mandar parar.**

É só isso. Não mande vídeo, não mande link.

A skill `modo-autonomo` faz o resto: ele traz material do Acervo com gabarito,
mede, muda uma coisa, mede de novo, desfaz o que não melhorou e escreve no
quadro. De madrugada ou às três da tarde, o comando é o mesmo.

Se quiser marcar hora:

> **Entre em modo autônomo agora e trabalhe até as 7h. Me mande o resumo quando
> parar.**

## Para saber se ele fez mesmo

> **Rode `python scripts/prova.py` e me mande o resultado inteiro.**

Esse relatório não pergunta nada a ele. Lê os rastros: quantas medições
existem, quais experimentos fecharam antes-e-depois, quantos commits saíram, se
o quadro de aviso foi escrito, se ele mexeu onde não devia.

**Peça de novo depois de umas horas.** Duas fotos do mesmo relatório em momentos
diferentes contam mais que uma.

## Para conferir que ele não está te contando história

O relatório termina com um número. Peça o mesmo número por outro caminho:

> **Rode `python scripts/regua.py` e me mande a tela inteira.**

Se der diferente do que ele disse, alguma coisa não bate. Essa é a única
pergunta que ele não consegue responder por você.

## Para ele cortar um vídeo seu

> **Aplique no vídeo [link] e me mande os cortes.**

Isto é **produção**, não treino. Não ensina nada ao programa — ele corta com o
que já sabe. Serve para você ter o clipe.

## Para ele aprender com o que você aprovou

> **Rode `python scripts/regua_vereditos.py` e me diga onde meu julgamento
> discordou do que o programa achou de si mesmo.**

Só faz sentido depois que o caderno tiver uns vinte vereditos. Você os produz
revisando pelo celular, que é coisa que já ia fazer.

## Quando você achar que ele travou

> **Me diga, em cinco linhas: em que ideia você está, qual foi a última medição
> com nome e número, e o que você mudou desde então.**

Se ele não souber responder isso, ele não está trabalhando — está conversando.

---

## O que NÃO funciona, e por quê

### "Toma esse link e aplica tudo no Furia"

Não. "Tudo" não é uma instrução; é um convite para ele inventar o que fazer e
achar que acertou. Diga a ideia, uma de cada vez, ou mande entrar em modo
autônomo e deixe a fila do quadro decidir a ordem.

### "Roda a madrugada nesse vídeo aqui" (vídeo qualquer do YouTube)

Não ensina nada. Sem gabarito não existe resposta certa, e um agente medindo o
próprio trabalho passa a noite inteira produzindo confiança errada — que é
exatamente o que você descreveu quando disse que não adianta ele ficar sete
horas no mesmo vídeo saindo os mesmos resultados errados.

Ele precisa de material **com a resposta no fim do livro**. É o Acervo, e é por
isso que o comando de treino não leva vídeo nenhum.

### "Esse vídeo aqui é meu, treina nele"

Só serve se o vídeo já estiver no Acervo. Para descobrir:

> **Rode `python scripts/novo_material.py --listar` e me diga se [o vídeo] está
> na lista.**

Se estiver, ele traz o gabarito e treina. Se não estiver, dá para cortar (é
produção), mas não dá para treinar.

---

## O que nenhum relatório vê

Quantos bots do Hermes rodaram, e qual modelo estava em cada um. Isso é de
dentro do Hermes; o programa não enxerga.

E não faz falta. Quem decide se uma mudança fica é o número da régua, não o
modelo que a propôs. Bot que não trabalhou aparece na prestação de contas como
**experimento que não mediu** — que é a única coisa que importa saber.
