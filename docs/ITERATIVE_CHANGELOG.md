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
