# Garimpo e Campaign Hub — revisão de integração

## Conclusão executiva

O material audiovisual e textual já disponível é suficiente para continuar aprimorando o motor editorial do Furia 1. O Garimpo também é uma referência útil, mas principalmente pela **proveniência, estados operacionais, filtros explicáveis e separação entre memória histórica e decisão editorial**. Não é seguro copiar uma arquitetura autenticada ou transformar os números do Campaign Hub em previsão automática de viralidade.

A rota pública de Garimpo redirecionou para a tela de autenticação do Criadores. A página informa que o acesso ocorre por ID Missão e que o Criadores não recebe a senha do usuário [1]. Nenhum login, CAPTCHA, envio de dados ou tentativa de contornar a proteção foi realizado. A inspeção de código limitou-se ao HTML público e aos bundles carregados nessa tela; o bundle específico da rota autenticada não é entregue antes da sessão do usuário.

## O que foi observado publicamente

| Elemento | Observação | Utilidade para o Furia |
| --- | --- | --- |
| Identidade | O domínio apresenta Criadores/Missão e uma entrada por ID Missão. | Reforça a ideia de acesso claro e de uma única superfície, sem criar uma segunda aplicação no Furia. |
| Privacidade de autenticação | A tela afirma que o Criadores recebe autorização para reconhecer o usuário, não a senha [1]. | Referência de comunicação: explicar o que é local, o que é opcional e o que é enviado a um serviço. |
| Linguagem editorial | A página fala em acompanhar contas, views e XP. | Inspira uma camada de acompanhamento, mas não deve ser confundida com a revisão de corte. |
| Restrições de coleta | O `robots.txt` público não fornece sitemap nem conteúdo do Garimpo e declara sinais de conteúdo sem liberar a rota autenticada [2]. | A análise respeitou o limite público e não usa engenharia reversa de sessão. |

## Contrato do Campaign Hub observado pelo conector autorizado

O conector `missao` expõe uma separação clara de contas e exige que cada consulta orgânica declare um canal. A conta prioritária para o Furia continua sendo `@renansantosmbl`; `@renansantosreserva` e `@partidomissao` possuem baselines independentes e não devem ser misturadas.

A superfície Acervo é particularmente útil porque separa as responsabilidades: transcript com frases e timestamps; blocos QA-gated com ranks lexical/semântico, tier de confiança, proveniência, warnings e foco de locutor; e estatísticas de freshness, filas e consistência temporal. O próprio contrato alerta que caption é evidência automática, nunca citação, e que `densityRank` e `selfContainedRank` devem ser preferidos às autoavaliações brutas do modelo.

Uma consulta limitada a cinco blocos sobre “crime organizado”, com conta e foco em Renan explicitamente definidos, retornou zero itens. Esse resultado é tratado como **zero de recall naquela consulta**, não como prova de que o tema não existe. A consulta operacional de freshness expôs filas e latências do Acervo; esses dados são úteis para diagnóstico de ingestão, não para ranquear cortes.

## Comparação com o Furia atual

O Furia já adota a decisão arquitetural correta: a aplicação local não chama o MCP diretamente; recebe um snapshot autorizado, mantém o contexto fora do checkout e aplica a memória como referência histórica limitada. O normalizador já possui guardas de conta, limites de tamanho e separação entre prior de performance e score técnico.

Nesta rodada, o importador passou a aceitar também snapshots oficiais com `accounts`, `record_counts`, `records` e `sync`. Ele extrai apenas metadados agregados e bounded, sem importar transcripts ou blocos crus para o projeto. O payload anexado agora explicita `readOnly: true`, `scoreTechnical: false`, conta, versão, contagens, escopo e atualização. O cartão de memória do Studio mostra esses elementos ao editor.

| Sinal do Chub | Tratamento no Furia |
| --- | --- |
| Conta/canal | Guardado e exibido; a conta padrão continua sendo `@renansantosmbl` quando não há outra seleção válida. |
| Tiers, ranks e warnings | Podem ser transportados como contexto de proveniência em snapshot; não substituem os gates locais de contexto, locutor e continuidade. |
| Transcript/Acervo | Pode orientar navegação e comparação, mas caption nunca vira citação automaticamente. |
| Freshness e filas | São apropriados para status/diagnóstico de integração, não para score editorial. |
| Métricas e ratios | Permanecem como memória histórica limitada; não são promessa de viralidade nem fator que possa superar início, fim, locutor ou contexto. |
| Conteúdo de outras contas | Não é misturado silenciosamente. Ausência de uma plataforma é tratada como fora de escopo, não como zero. |

## O que ainda vale aprimorar

A próxima melhoria de alto valor é uma matriz de discordância por candidato. Ela deve manter separados o veredito textual do Furia, a observação audiovisual, o contexto do Chub, a decisão humana e a razão estável da decisão. Isso permite medir se um sinal ajuda sem fingir que uma amostra pequena constitui aprendizagem causal.

Também é recomendável utilizar o Acervo para navegação de proveniência: ao abrir um candidato, o editor deve poder saber se existe um bloco relacionado, qual é o tier, se há warning, qual é a faixa de `audioCheckRanges` e se a legenda é automática ou manual. Essa informação deve aparecer como contexto e revisão, nunca como aprovação silenciosa.

O Garimpo completo só poderá ser avaliado visual e funcionalmente depois que o usuário autenticar no navegador ou fornecer material público adicional. Se essa inspeção for desejada, o caminho seguro é o próprio usuário assumir o login; não é necessário compartilhar senha, cookie ou token por mensagem.

## Validação desta rodada

Passaram `py_compile` para o backend e módulos relevantes, `node --check static/app.js`, `git diff --check` e **24 regressões do Studio adapter/Campaign Hub**. A árvore continha somente `static/app.js`, `studio_adapter.py` e `tests/test_studio_adapter_routes.py` como alterações de código, sem mídia, transcript, banco ou credenciais.

## Referências

[1] [Criadores/Missão — rota pública do Garimpo](https://criadores.missao.org.br/garimpo)

[2] [Criadores/Missão — robots.txt](https://criadores.missao.org.br/robots.txt)
