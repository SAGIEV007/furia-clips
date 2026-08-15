# Versionamento do Furia Clips

## Objetivo

O Furia Clips usa uma versão editorial e técnica persistente para que qualquer log enviado ao agente identifique exatamente qual comportamento estava em execução. A versão pública atual é mantida no arquivo [`VERSION`](../VERSION) e é exposta pela aplicação, pelo console e pela API de configurações.

A versão inicial deste contrato é **1.0**.

## Regra de incremento

A versão deve ser atualizada quando uma mudança alterar o comportamento que o usuário observa, o ranking, a seleção de contexto, a geração de headlines, os formatos de saída, a renderização, o console, a persistência, a estabilidade ou o contrato de continuidade.

| Tipo de mudança | Exemplo | Incremento recomendado |
| --- | --- | --- |
| Correção interna sem mudança editorial ou operacional observável | refatoração segura, tipagem, teste adicional | revisão GitHub; manter versão quando apropriado |
| Correção de bug ou melhoria compatível | contexto anafórico, diagnóstico de `count: 0`, validação FFprobe | segundo componente: `1.1`, `1.2` |
| Nova capacidade editorial ou alteração relevante do ranking | novo gate, novo modelo de headline, novo formato | segundo componente ou próxima versão acordada |
| Mudança incompatível de dados, API ou fluxo | migração, alteração de contrato, remoção de preset | major: `2.0` |

Enquanto o projeto estiver na fase inicial, use `1.x` para evoluções compatíveis e não pule versões sem registrar a razão. O hash curto do Git continua sendo a revisão técnica complementar, não substitui a versão pública.

## Onde a versão deve aparecer

A aplicação deve carregar `VERSION` como fonte única e expor a versão e a revisão Git em `/api/settings`, no cabeçalho da interface, em todos os eventos de progresso do Socket.IO, em atualizações de job e no pacote de diagnóstico sanitizado. Mensagens persistentes de log devem manter `program_version` e `program_revision` como campos estruturados.

A primeira linha útil de cada sessão de processamento deve identificar a versão, a revisão, o `job_id`, o `project_id`, a origem da mídia e a data/hora. O texto humano pode ser prefixado por `[Versão 1.0 · abc1234]`, mas consumidores automáticos devem usar os campos estruturados.

## Processo de release

Antes de publicar uma mudança:

1. reproduza o comportamento atual e registre a hipótese;
2. altere o arquivo `VERSION` quando a mudança for observável;
3. atualize `CHANGELOG.md` ou o relatório de continuidade da rodada;
4. atualize os testes da identidade de runtime;
5. rode a suíte, o smoke test e a validação audiovisual disponível;
6. faça `git diff --check` e verifique que nenhum segredo, cookie, vídeo grande ou banco local foi adicionado;
7. faça commit com a versão no resumo ou no corpo, por exemplo `feat: improve context gates (1.1)`;
8. publique a branch no GitHub e registre o hash em [`docs/continuity/PROJECT_STATE.md`](continuity/PROJECT_STATE.md).

Nunca altere a versão apenas para mascarar um erro. A versão precisa representar uma mudança real e reproduzível.
