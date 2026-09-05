---
name: conferir-antes-de-entregar
description: Antes de dizer que uma tarefa está pronta, provar que está — mostrando o comando e a saída inteira, nunca um resumo. Use ao terminar qualquer tarefa, ao responder "rodei os testes", "medi", "está passando", ou qualquer frase que afirme um resultado.
---

# Conferir antes de entregar

Esta skill existe por causa de um caso real, e vale a pena saber qual.

O editor pediu a bateria de testes. O bot respondeu:

```
19 passed in 0.12s
```

A bateria tem **1196** testes. Dezenove é o tamanho de um arquivo só. O bot não
mentiu — ele rodou alguma coisa e ela passou. Mas a resposta fez o editor
acreditar que nada estava quebrado, quando 1177 testes nem foram olhados.

**Isso é pior que não fazer a tarefa.** Não fazer deixa o problema onde estava.
Fazer pela metade e dizer "passou" cria uma certeza falsa, e é em cima de
certeza falsa que se toma a próxima decisão errada.

## As três perguntas, antes de escrever "pronto"

1. **Rodei o que me pediram, ou uma parte?** Se pediram a bateria, é da raiz do
   repositório e sem apontar arquivo. Se pediram a régua, é a régua inteira.
2. **O número faz sentido no tamanho da coisa?** Um projeto com mais de mil
   testes não termina em 0,12 s. Uma medição de um vídeo de meia hora não sai
   instantânea. Quando o número parecer barato demais, ele provavelmente é.
3. **Estou entregando a saída ou a minha leitura dela?** A leitura pode estar
   errada. A saída, não.

## O que entregar

**O comando, e a saída inteira.** Copiada, não resumida, não interpretada, não
"limpa".

```
$ python -m pytest -q
1210 passed, 2 xfailed in 94.46s
```

Se a saída for grande, entregue o começo e o fim — nunca o meio editado por
você. Se ela tiver erro, entregue o erro **inteiro**, mesmo que ele seja feio e
mesmo que você ache que sabe a causa. Quem lê decide o que é relevante.

## O que nunca fazer

- **Resumir número.** "Passou tudo" não é resultado; `1210 passed` é.
- **Arrumar a saída.** Já aconteceu de um agente "normalizar" um arquivo de
  rastro e apagar exatamente os horários que provavam o que se queria provar.
- **Dizer "deve estar funcionando".** Ou você rodou, ou não rodou.
- **Trocar a tarefa por uma menor sem avisar.** Se a bateria inteira não roda
  na sua máquina, isso é a notícia — não rode um pedaço e chame de bateria.

## Quando não deu

Dizer que não deu é uma resposta completa e útil. Estas três linhas valem mais
que qualquer tentativa de disfarçar:

```
Não consegui: <o comando>
O erro, inteiro: <cole>
Onde eu parei: <a última coisa que funcionou>
```

Uma sessão que descobre que um caminho não funciona é uma sessão útil. Uma
sessão que diz "funcionou" sem ter funcionado estraga todas as seguintes.
