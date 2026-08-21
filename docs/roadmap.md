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
| P3-A | Integrações opcionais | API local, fontes online, publicação e notificações opt-in | P2-B, P2-A |
| P3-B | Recursos multimídia avançados | B-roll, voz, áudio e upscaling opcionais | P2-B |
| P3-C | Pesquisa editorial YouTube–Chub | Buscar vídeos e temas, consultar evidências read-only, ranquear links, localizar transcrições/blocos e solicitar download seletivo | P2-B, P2-C |

## Ordem de implementação

A primeira unidade de código será a camada de timeline e qualidade de mídia, porque todo o restante depende de timestamps confiáveis. A segunda será o job orchestrator, porque a aplicação precisa ser recuperável antes de receber automação em lote. A terceira será segurança e configuração. Depois serão reconstruídos os candidatos, o ranking, o reframe, as legendas e a revisão.

A implementação não deve adicionar uma API online obrigatória. A compatibilidade com a experiência do OpusClip será buscada principalmente por meio do fluxo de usuário: prompt para encontrar momentos, resultados comparáveis, revisão rápida, presets, exportação em lote e feedback.

## Norte futuro: pesquisa no YouTube e no Campaign Hub

Em uma fase posterior, o Furia deverá ter uma área de **Pesquisa editorial**. O editor poderá informar um tema, pessoa, canal, URL ou combinação de filtros e pesquisar vídeos no YouTube diretamente pela ferramenta. A primeira entrega deve ser read-only, retornando links, títulos, canais, duração, data, disponibilidade de legenda, motivo da relevância e estado de acesso. A implementação deverá respeitar paginação, cache, debounce e limites de quota da API oficial; `search.list` aceita filtros de termo, canal, idioma, data, duração e legendas, mas tem limites de resultados e quota documentados pela [documentação oficial do YouTube](https://developers.google.com/youtube/v3/docs/search/list) e pelo [calculador de quota](https://developers.google.com/youtube/v3/determine_quota_cost).

Quando o editor pesquisar apenas um **tema**, o Furia poderá combinar a busca do YouTube com uma consulta somente leitura ao Campaign Hub. O resultado será um dossiê de descoberta contendo fontes, vídeos e links, blocos, timestamps, transcrições disponíveis, hooks, tópicos, métricas e evidências observadas. Contas, plataformas e proveniência deverão permanecer separadas. A relevância da busca, a qualidade da evidência, a disponibilidade de mídia e a confiança editorial serão mostradas separadamente; nenhum resultado do Chub aprovará automaticamente um corte.

O download do vídeo original ou de um trecho específico será uma ação posterior e explícita, separada da pesquisa. Quando permitido e acessível, o sistema deverá oferecer download até o limite configurado, validação de áudio/vídeo, cancelamento, retries limitados e deduplicação por fonte e intervalo. Quando houver somente metadata, link ou transcrição sem mídia, a interface deverá declarar essa limitação. A API oficial de legendas pode listar faixas, mas não entrega o texto em `captions.list` e o download depende de autorização; por isso, a transcrição poderá vir de legenda pública disponível, arquivo fornecido pelo editor, snapshot autorizado do Chub ou Whisper local, sem contornar bloqueios.

Essa fase não inclui publicação automática no YouTube. Credenciais ficarão fora do frontend, do código e do Git; quotas, direitos autorais, privacidade, atribuição e os [termos da API do YouTube](https://developers.google.com/youtube/terms/api-services-terms-of-service) serão tratados como requisitos de produto, não como detalhes opcionais.

### Camada local inspirada no Garimpo — implementada nesta rodada

A pesquisa editorial local já recebeu uma primeira camada compatível com o modelo observado no Garimpo. Ela continua baseada em snapshots read-only do Campaign Hub, mas agora aceita a plataforma efetiva do registro, inclusive YouTube, e expõe um dossiê de bloco com título, resumo, categoria, tópicos, pergunta-gatilho, intervalo, duração, momentos fortes, razões, necessidade de contexto, flags de risco, gates, tier de confiança e vídeo de origem. A interface também oferece filtro de plataforma, status de timestamps/download, cópia de pauta, transcrição, intervalo e momentos, além de uma apresentação visual mais próxima de uma bancada editorial.

Essa camada não é uma conexão online direta do Furia com o Chub e ainda não consulta o YouTube por conta própria. Ela torna os snapshots locais mais úteis e prepara o contrato de dados para a integração futura. Download continua explícito e desabilitado por padrão; ter URL e timestamps não significa que o arquivo possa ser baixado. A fase online deverá acrescentar autenticação/credenciais fora do frontend, paginação, cache, debounce, quota, disponibilidade real de mídia e verificações de direitos.

### Norte ampliado: filtros, pautas, preview e benchmark do Garimpo

A análise do Garimpo mostrou dois modos de descoberta que devem ser reproduzidos no futuro no Furia. O modo **Blocos** procura unidades semânticas já analisadas; o modo **Vídeos** procura a fonte longa pelo nome, tema ou metadados e depois abre uma bancada com seus blocos em ordem temporal. A busca deve aceitar consulta livre e distinguir busca semântica, lexical/exata e híbrida, mostrando qual modo foi aplicado.

Os filtros planejados incluem conta de origem, plataforma, período de publicação, duração da fonte, duração do bloco, categoria, tópicos, locutor principal, tier de confiança, qualidade da transcrição, presença de timestamps, autossuficiência, densidade, necessidade de contexto e disponibilidade de mídia. Nenhum filtro deve ser aplicado silenciosamente: o card deve declarar o escopo efetivo, o total encontrado, o cursor/página e a razão de exclusão quando relevante.

A área futura de **Pautas** deve consultar candidatos explicáveis do Chub, exibindo tese, pergunta-gatilho, contexto de borda, possíveis cortes, momentos fortes, risco, locutor, transcrição e os componentes do score. Pautas de fala principal e respostas críticas devem permanecer em seções distintas. O sistema pode sugerir momentos, mas não deve transformar sugestão em aprovação ou publicação.

Para uma consulta como `saúde`, o fluxo planejado é: pesquisar o conceito; listar blocos e fontes longas relevantes; alternar para `Vídeos` quando o editor quiser encontrar a gravação; abrir a bancada; navegar por momentos e transcrição; copiar pauta/timestamps; abrir o preview remoto; e somente depois decidir se vale baixar o intervalo. A busca por nome de vídeo deve funcionar separadamente da busca semântica para evitar que uma pesquisa de tema altere o significado do título da fonte.

O preview remoto é parte central do produto: quando houver uma URL YouTube válida, o Furia deve abrir a fonte ou o timestamp sem exigir o download do vídeo inteiro. O preview não é evidência suficiente para um corte; o editor precisa poder conferir áudio e imagem. A camada de download deve ser posterior, com intervalo semântico, margem técnica, ticket ou fonte autorizada, fila, progresso, cancelamento, validação e deduplicação.

O benchmark entre Furia e Garimpo deve medir **recall de momentos fortes**, cobertura de blocos, precisão de timestamps, autonomia contextual, continuidade de fala, identificação de locutor, taxa de falsos positivos, necessidade de revisão e deduplicação. Um teste de referência deve registrar quantos momentos o Garimpo apresenta em uma fonte, quantos o Furia encontra, quais coincidem temporalmente e quais foram descartados por evidência insuficiente. Quantidade nunca será usada isoladamente como métrica de qualidade.

O porte do Corteiros Helper ficará atrás de um adaptador opcional. O Furia não deve guardar token, URL assinada, cookie ou credencial; não deve chamar o endpoint remoto sem uma ação explícita; e deve funcionar sem helper instalado. O helper analisado mostrou limites de 12 minutos para o bloco, margem de aproximadamente 2 segundos por borda e download total limitado a 13 minutos, que só poderão virar limites do Furia quando a política da fonte estiver confirmada.

## Portões de qualidade

Nenhuma fase pode ser marcada como concluída quando houver falha P0 aberta. Um vídeo não pode ser considerado pronto somente porque o arquivo existe: ele precisa conter áudio e vídeo válidos, ter duração dentro da tolerância, resolução compatível com o preset, legendas sincronizadas quando habilitadas, caminho seguro e relatório de validação.

## Resultado de produto esperado

Ao final de P1, o Furia Clips deve ser confiável para um vídeo por vez: encontrar, explicar, revisar e renderizar clips. Ao final de P2, deve reduzir substancialmente o trabalho diário do usuário por meio de presets, lotes e histórico. P3 fica reservado para integrações e recursos caros que não são necessários para validar o núcleo do produto.


### Resultado do benchmark Garimpo–Furia — 2026-08-21

A fonte `gPl1Sbqzxks` não pôde ser baixada porque o YouTube respondeu com detecção de bot; nenhum bypass foi tentado. Como alternativa controlada, a transcrição pública timestampada do bloco selecionado foi usada localmente, com 121 segmentos entre 0:31 e 5:57. O Furia encontrou 3 capítulos, 15 candidatos pergunta–resposta e 9 hooks. As janelas candidatas cobriram os quatro momentos fortes de referência do Garimpo (recall temporal de 100%); o hook exato cobriu 75%. Esse resultado mede cobertura para revisão, não precisão editorial final, pois imagem, áudio e locutor não puderam ser validados sem a mídia.

O benchmark revelou e corrigiu uma duplicação no gerador de capítulos: quando a transcrição terminava, o último grupo era anexado e depois reaproveitado pelo fechamento da rotina. O acumulador agora é limpo após anexar o grupo final, com regressão automatizada em `tests/test_editorial_chapters.py`. O relatório detalhado está em `/home/ubuntu/FuriaClipsData/analyses/garimpo-furia-context-comparison-2026-08-21.md`.

## Norte ampliado — métricas profissionais de long-form para shorts

A experiência de CapCut, OpusClip, Vizard, Descript, Klap e Riverside confirma que um cortador profissional precisa combinar descoberta de highlights, seleção por gênero/tópico, duração configurável, edição por transcrição, reframe orientado por locutor, revisão e ranking. O Furia não deve copiar um Virality Score opaco: deve apresentar um score relativo e explicável, separado de confiança, gates técnicos e métricas pós-publicação.

A métrica central desta evolução será a qualidade de localização e contexto. O benchmark deverá registrar temporal IoU, Precision@IoU, Recall@IoU, HIT@K, erro de início/fim, hit de borda, completude contextual, recuperação de antecedente, redundância semântica, cobertura temporal da fonte, precisão de locutor, cobertura do sujeito no enquadramento, jitter do crop e taxa de ajustes manuais. A nova camada `modules/quality_metrics.py` já calcula a base temporal quando o editor fornece referências reais; `daily_portfolio.py` a expõe somente via `reference_intervals` opcional.

As próximas fases devem transformar esses sinais em um scorecard visual de quatro camadas: Contexto, Força editorial, Técnica e Confiança. O ranking agregado continua útil para ordenar, mas nenhum candidato com falha de transcrição, locutor, áudio, borda, evidência ou enquadramento deve parecer aprovado apenas por pontuação alta. O objetivo de 39–50 cortes continua sendo faixa operacional, nunca motivo para aceitar material fraco.

A implementação deve seguir uma arquitetura hierárquica: ingestão e identidade da fonte; timeline de baixo custo; capítulos por shot/pausa/semântica; candidatos por família editorial; fusão de texto, áudio e vídeo; ranking; diversidade/deduplicação; revisão; e somente então render/exportação. Para vídeos de 4–7 horas, o sistema deve trabalhar com janelas, cache e paginação, sem enviar o vídeo inteiro a um modelo online por padrão.

A pesquisa completa, matriz de comparação, definições, plano M0–M12 e referências oficiais estão em [`docs/long-to-short-metrics-and-plan-2026-08-21.md`](long-to-short-metrics-and-plan-2026-08-21.md). Dados de feedback, transcrições, mídia e métricas pós-publicação permanecem fora do Git; o repositório recebe apenas código, testes e documentação sanitizada.


## Benchmark operacional long-form → shorts — 2026-08-21

O checkout publicado foi baixado novamente em diretório limpo e executado sobre a mídia local `DbWxJ54hbKO.mp4` (4m58,931s; 720×1280; H.264/AAC). A primeira execução encontrou a ausência da dependência declarada `faster-whisper`; depois de instalada, o pipeline concluiu com 7 clips renderizados. O código atualizado, executado com banco isolado e transcrição em cache, também concluiu com 7 clips, sem rejeição de renderização, e persistiu intervalos, texto e scorecards.

A rodada confirmou deduplicação: no banco compartilhado, os 7 intervalos já gerados foram reconhecidos e descartados em vez de repetidos. O diagnóstico de 9 candidatos esperados e 7 finais foi mantido como `quality_pool_below_reference`, sem fabricar cortes de qualidade inferior para cumprir uma quota. A implementação agora expõe scorecard de Contexto, Força editorial, Técnica e Confiança, persiste o scorecard, normaliza limites ao reabrir projetos e calcula cobertura/HIT@K quando referências reais são fornecidas.

A ausência de `faster-whisper` passou a produzir uma mensagem acionável sobre a instalação, em vez de um `ModuleNotFoundError` de um fallback não declarado. Não houve alteração de pesos do ranker, pois a mídia ainda não possui rótulos humanos ou intervalos anotados que permitam calibração honesta. A próxima etapa de precisão deve usar decisões reais do editor, medir aprovação por faixa de score, ajuste manual de bordas, contexto completo e redundância por fonte/família.
