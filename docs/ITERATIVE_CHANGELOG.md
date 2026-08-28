# Furia Studio — changelog iterativo

Este arquivo registra somente mudanças de código, testes, documentação e decisões sanitizadas. Mídia, transcripts, bancos, caches, logs brutos, URLs privadas e credenciais ficam fora do repositório.

## Ciclo 2026-08-28 — início da calibração ampliada

### Estado

O plano completo da próxima evolução foi criado. A execução será feita em ciclos delimitados: inventário, hipótese, implementação, testes, validação audiovisual, registro e publicação na branch dedicada. O ciclo não executará tarefas infinitamente sem supervisão e não iniciará nova rodada quando houver falha não compreendida.

### Inventário sanitizado

Foram identificadas duas fontes adicionais privadas de alta definição, ambas com áudio, além da entrevista crítica já validada. Também existem referências humanas associadas às fontes adicionais e à entrevista crítica. A matriz detalhada permanece fora do GitHub; somente métricas agregadas e conclusões editoriais poderão ser versionadas.

### Regras preservadas

O Furia 1 continua sendo o motor canônico. Gemini permanece evidência multimodal opcional, com orçamento, cancelamento e fallback local. Chub permanece snapshot local, read-only, descritivo e sem seleção automática por clip. A branch default não será modificada.

### Próxima ação

Processar cada fonte adicional localmente, sem Gemini inicialmente, comparar com suas referências humanas e selecionar amostras de maior risco para revisão audiovisual. Nenhuma regra será criada a partir de timestamp específico; toda alteração deverá ter hipótese generalizável e teste de regressão.

## Ciclo 2026-08-28 — rodada A/B e correção de transcript

A fonte adicional A foi processada com Whisper local e concluiu com 20 clips renderizados. Quatro amostras audiovisuais foram revisadas: três apresentaram estrutura editorial aproveitável e uma recebeu alerta de fechamento abrupto, sem transformar a avaliação audiovisual em decisão automática.

A fonte adicional B foi processada em rodadas controladas. O primeiro resultado de 2 clips revelou desalinhamento da transcrição: o arquivo Tactiq usava horário absoluto de gravação em linhas separadas do texto. Após normalização temporária em blocos, o Furia 1 produziu 9 clips, igualando a contagem da referência humana. A correção foi generalizada no parser: blocos Tactiq explícitos são preferidos a timestamps embutidos, e um relógio absoluto só é deslocado quando excede claramente a duração do vídeo. A rota integrada foi validada novamente com o arquivo original e produziu 9 clips.

Foram adicionados testes para relógio absoluto, timestamps relativos em vídeos longos e parsing de blocos Tactiq. As métricas de IoU permanecem descritivas e não substituem QA editorial. Gemini não participou destas seleções e Chub não alterou score ou pool canônico.

### Próxima ação

Executar a suíte focalizada e completa, revisar o diff, publicar esta correção na branch dedicada e então iniciar o próximo ciclo de desempenho/UX com hipótese, teste e rollback seguro.
