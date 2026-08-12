# Roadmap de reconstrução do Furia Clips

## Estratégia

A reconstrução será incremental. O sistema atual será preservado como referência até que cada substituição tenha teste equivalente. A ordem prioriza primeiro aquilo que pode fazer o vídeo errado, perder trabalho ou expor a máquina; depois, a qualidade editorial; por fim, os recursos de escala e publicação.

## Fases

| Fase | Entrega | Critério de conclusão | Dependências |
| --- | --- | --- | --- |
| P0-A | Baseline e fixtures | Testes reproduzíveis, vídeos sintéticos e relatório inicial | Nenhuma |
| P0-B | Timeline canônica | Teste prova conversão correta após remoção de silêncio | P0-A |
| P0-C | Segurança de arquivos e segredos | Traversal bloqueado, chaves mascaradas e bind local | P0-A |
| P0-D | Jobs persistidos | Job ID, estados, progresso, cancelamento e recuperação | P0-A |
| P1-A | Candidatos editoriais | Limites de palavra, contexto, duração adaptativa e diversidade | P0-B, P0-D |
| P1-B | Score explicável | Fatores, confiança, penalidades e ranking determinístico | P1-A |
| P1-C | Reframe e captions | Layout por cena, crop suavizado, safe areas e legenda sincronizada | P0-B |
| P1-D | Revisão humana | Aprovação, rejeição, ajuste de tempo e rerender sem retranscrição | P1-A, P1-C |
| P2-A | Presets de marca | Canal, fonte, cores, logo, layout e plataforma persistidos | P1-C, P1-D |
| P2-B | Processamento em lote | Fila de múltiplos vídeos, retomada e relatório por lote | P0-D, P2-A |
| P2-C | Feedback | Aprovação/ajustes armazenados e relatórios de calibração | P1-D |
| P3-A | Integrações opcionais | API local, fontes online, publicação e notificações opt-in | P2-B |
| P3-B | Recursos multimídia avançados | B-roll, voz, áudio e upscaling opcionais | P2-B |

## Ordem de implementação

A primeira unidade de código será a camada de timeline e qualidade de mídia, porque todo o restante depende de timestamps confiáveis. A segunda será o job orchestrator, porque a aplicação precisa ser recuperável antes de receber automação em lote. A terceira será segurança e configuração. Depois serão reconstruídos os candidatos, o ranking, o reframe, as legendas e a revisão.

A implementação não deve adicionar uma API online obrigatória. A compatibilidade com a experiência do OpusClip será buscada principalmente por meio do fluxo de usuário: prompt para encontrar momentos, resultados comparáveis, revisão rápida, presets, exportação em lote e feedback.

## Portões de qualidade

Nenhuma fase pode ser marcada como concluída quando houver falha P0 aberta. Um vídeo não pode ser considerado pronto somente porque o arquivo existe: ele precisa conter áudio e vídeo válidos, ter duração dentro da tolerância, resolução compatível com o preset, legendas sincronizadas quando habilitadas, caminho seguro e relatório de validação.

## Resultado de produto esperado

Ao final de P1, o Furia Clips deve ser confiável para um vídeo por vez: encontrar, explicar, revisar e renderizar clips. Ao final de P2, deve reduzir substancialmente o trabalho diário do usuário por meio de presets, lotes e histórico. P3 fica reservado para integrações e recursos caros que não são necessários para validar o núcleo do produto.
