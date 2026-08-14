# Política de duração e contexto — Furia Clips

## Princípio editorial

O Furia Clips não deve procurar cortes por uma duração fixa. A regra principal é selecionar o **menor intervalo que preserve hook, contexto e payoff completos** para uma pessoa que não assistiu ao vídeo original.

> Quanto mais curto, melhor — desde que o corte continue excepcionalmente compreensível, autocontido e interessante.

## Preferência de duração

O ranqueador trata **180 segundos** como teto preferencial, não como limite absoluto. A preferência é uma curva suave: cortes muito curtos podem ser excelentes quando contêm uma ideia completa; cortes entre aproximadamente 30 e 60 segundos recebem a maior preferência; cortes mais longos continuam elegíveis quando o argumento exige desenvolvimento.

| Situação | Tratamento editorial |
| --- | --- |
| Até 180 segundos, com contexto e fecho | `curto_preferencial`; priorizar o menor intervalo autossuficiente. |
| Acima de 180 segundos, com hook, argumento e completude fortes | `excecao_contextual`; preservar para revisão porque encurtar pode destruir o sentido. |
| Acima de 180 segundos, sem evidência suficiente de hook ou conclusão | `longo_para_revisao`; não é automaticamente descartado, mas deve ser encurtado se possível. |

O limite técnico do seletor é mais amplo que três minutos para evitar truncamentos artificiais. Ele existe para proteger contra respostas inválidas da IA, não para orientar o tamanho final dos clips.

## Contexto obrigatório

Um corte só é forte quando o espectador entende **quem fala, qual é o assunto, qual é a tese ou pergunta, qual é o desenvolvimento e qual é o fecho**. Em entrevistas e debates, a pergunta deve permanecer quando for necessária para entender a resposta. Pronomes sem antecedente, frases iniciadas no meio, evidências sem explicação e conclusões ausentes reduzem a completude mesmo que o vídeo seja curto.

O hook deve ser avaliado nos primeiros segundos, mas não pode vencer sozinho. Um início chamativo sem contexto ou payoff não deve superar uma abertura menos explosiva que entrega uma ideia concluída. O score, portanto, combina hook, fluxo, valor, estrutura de argumento, completude, clareza, energia e coerência de capítulo.

## Backends

Gemini e Ollama recebem a mesma instrução: não existe faixa obrigatória; devem escolher o menor trecho autossuficiente e só ultrapassar três minutos quando a pergunta, prova, argumento ou conclusão exigirem. O fallback NLP utiliza blocos editoriais menores, interrompe no primeiro encerramento natural quando o mínimo útil já foi atingido e mantém o limite técnico apenas como proteção.

## Explicabilidade no HUD

Cada clip pode exibir `curto_preferencial`, `excecao_contextual` ou `longo_para_revisao`, além do percentual de brevidade. A interface explica que uma exceção longa foi preservada por contexto ou recomenda verificar se o mesmo sentido pode ser mantido em menos tempo.

## Não é uma promessa de viralização

A política melhora a seleção editorial e a eficiência da revisão, mas não garante desempenho de plataforma. Aprovações e rejeições humanas continuam sendo a fonte mais importante para calibrar o programa ao longo do tempo.
