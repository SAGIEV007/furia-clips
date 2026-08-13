# Central visual de revisão e correção do fallback Whisper

| Campo | Valor |
| --- | --- |
| Data | 13 de agosto de 2026 |
| Branch | `manus/rebuild-opus-parity` |

## Problema operacional observado

Quando a análise multimodal Gemini retornou HTTP 503, o Furia Clips acionou corretamente o fallback local. Entretanto, em instalações nas quais `openai-whisper` é carregado em vez de `faster-whisper`, a chamada padrão tentou computação `float16` em CPU e falhou com a mensagem `Requested float16 compute type, but the target device or backend do not support efficient float16 computation.`

A correção fixa `fp16=False` para o fallback `openai-whisper` em CPU e mantém `fp16=True` somente quando o dispositivo detectado é CUDA. O caminho principal `faster-whisper` já usava `int8` em CPU e `float16` em CUDA.

## Evolução visual implementada

A área de resultados recebeu uma Central de Revisão com contagem de candidatos, pendências, aprovados, itens que exigem confirmação de contexto, rejeitados, progresso da fila e filtros de revisão. Cada card também passou a exibir uma jornada editorial visual — entrada, ideia e fecho — além da decisão de enquadramento, com distinção entre reframe 9:16 seguro, quadro original preservado e enquadramento a revisar.

O console recebeu um fluxo visual com as fases Fonte, Transcrição, Contexto, Ranking e Cortes. As mensagens existentes continuam disponíveis no console técnico, mas agora também atualizam estados visuais para que análises longas possam ser acompanhadas sem interpretar logs detalhados.

## Persistência do feedback

O fluxo de corte rápido cria automaticamente um projeto local quando nenhum `project_id` é enviado. Os clips renderizados são persistidos no banco e devolvem `clip_id` ao frontend. Assim, os botões **Aprovar**, **Contexto** e **Rejeitar** alimentam o histórico editorial e não dependem apenas do estado visual da sessão atual.

O novo estado `needs_review` representa um candidato potencialmente útil cuja publicação exige confirmação de contexto, especialmente em acusações, números, perguntas incompletas, sobreposição de vozes ou enquadramento ambíguo.

## Validação

Foram adicionados testes para `fp16=False` em CPU, preservação de `fp16=True` em CUDA e persistência de feedback `needs_review`. Também foram executados testes de cancelamento e verificações de sintaxe Python/JavaScript.
