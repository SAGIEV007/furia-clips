# Desenho do ciclo 38 — MCP/Chub útil para recall de fontes longas

## Decisão

A pesquisa confirmou que o Furia **ainda não implementou tudo o que é viável**. A fundação offline-first, snapshots, guidance, gates e benchmark existe, mas a integração remota do MCP ainda é apenas um mecanismo externo de aquisição; o job local não consulta o MCP e o Chub não fecha o ciclo com aprovação humana do Furia.

A próxima mudança escolhida é uma hipótese única e de baixo risco:

> Se uma seed temporal do Campaign Hub não encontrar sobreposição na timeline local porque o arquivo processado é um recorte, bloco exportado ou cópia com offset diferente, o Furia deve tentar ancorá-la pelo texto do highlight/seed na transcrição local, com limiar conservador, registrar `text_anchor` como método de alinhamento e marcar revisão obrigatória. Assim o Chub aumenta recall sem fingir que timestamps incompatíveis são confiáveis.

Essa mudança é preferível a aumentar pesos de hook/ratio, pois o benchmark existente mostrou que o Chub melhora descoberta genérica, mas o filtro Renan-first pode remover seeds sem evidência positiva de fala. O problema imediato é localizar a mesma unidade na timeline local, não deixar métricas históricas dominarem o ranking.

## Arquitetura proposta

| Camada | Responsabilidade | Regra |
| --- | --- | --- |
| MCP remoto | Busca read-only, pauta, blocos, transcript windows, métricas e frescor | Nunca é chamado a cada candidato do job |
| Export/sync | Produz snapshot autorizado, paginado, sanitizado e versionado | Timeout, allowlist, hash, cursor, status e fallback para última versão |
| Memória local | Mantém sources, blocks, highlights, sentences, risks, priors e manifest | Job usa uma versão estável e não mutável |
| Guidance | Converte highlights/blocos em seeds temporais e semânticas | Preserva conta, fonte, tier, risco, locutor e versão |
| Alinhamento | Tenta timeline medida; se incompatível, usa texto com limiar conservador | `text_anchor` nunca vira prova de locutor nem aprovação |
| Expansão local | Recupera antecedente, pergunta, tese, evidência e payoff | A transcrição efetiva do corte continua sendo a local |
| Benchmark | Compara recall, IoU, erro de borda, contexto, payoff e revisão | Nenhum aumento de score é publicado sem before/after |

## O que o MCP pode fazer de útil neste caso

O MCP é valioso como fronteira padronizada para expor ao agente as fontes do Chub, não como um “modelo que treina sozinho” dentro do Furia. As tools atuais permitem consultar contas separadas, blocos QA-gated, highlights, pauta, transcrição paginada, métricas e frescor. A resposta real do Acervo inclui `renanSpeaking`, `triggerQuestion`, `selfContainedRank`, `densityRank`, riscos, versões de labeler, timestamps, `audioCheckRanges` e proveniência. Isso é suficiente para criar seeds explicáveis e um contexto compacto.

O MCP também pode futuramente fornecer resources versionados ou notificações de mudança para um botão “Atualizar memória”. Mesmo assim, o runtime de corte deve permanecer offline-first: a atualização instala uma memória local atômica, mostra o manifesto e só afeta jobs seguintes.

## O que não deve ser feito agora

Não chamar o MCP para cada candidato, não enviar a live inteira ou a transcrição completa ao modelo remoto, não usar `views`, `ratio`, hook ou `selfContainedRank` como aprovação automática, não misturar contas e plataformas, não tratar `speakerChange` como identidade e não embutir token/cookie no repositório.

Também não implementar ainda WhatsApp, smartwatch, pesquisa de notícias, publicação automática, download remoto por range ou um modelo pairwise. Essas funções só têm valor depois de a recuperação e a avaliação editorial estarem mensuradas.

## Métricas de aceitação

O teste deve comparar a mesma fonte/benchmark antes e depois. A melhoria só é considerada útil se aumentar `covered_count`/recall de referências com `measurement_reliable=true`, sem aumentar seeds ancoradas incorretamente, falsos Renan ou candidatos que falham em contexto/payoff. Cada seed recuperada por texto deve conservar os timestamps originais, o intervalo local e o método de alinhamento.

## Evidências que fundamentam a decisão

O servidor Chub reportou 34.579 highlights, fontes contínuas de lives no canal owner do Renan e transcrição paginada com proveniência e avisos de conferência. A pauta retornou candidatos com perguntas, highlights e ranks, mas o banco tinha zero outcomes de pauta no momento da pesquisa; portanto não há base para calibrar peso de confirmação de corte ainda.

O MCP oficial define `tools` para execução, `resources` para contexto read-only e notificações/paginação/cache para atualização. Isso sustenta o desenho de sincronização separada e memória local congelada.

## Estado

Este documento é o desenho técnico do ciclo 38. A implementação deve ocorrer somente após regressões específicas para alinhamento textual, rejeição por similaridade baixa, preservação de proveniência e compatibilidade com o caso de timeline correta.
