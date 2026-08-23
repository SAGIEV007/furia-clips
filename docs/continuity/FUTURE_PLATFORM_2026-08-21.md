# Futuro da Furia Clips — fase final de plataforma e automação

## 1. Lugar deste documento no roadmap

Este documento não substitui o norte imediato do projeto. Ele descreve o **futuro da ferramenta**, especialmente a fase final, depois de o motor de cortes, contexto, locutor, ranking, integração Chub/MBL e revisão estarem comprovadamente fortes.

O norte imediato continua sendo transformar uma fonte longa em cortes Renan Santos/MBL curtos, autossuficientes, contextualmente completos, editorialmente fiéis e tecnicamente prontos. As automações de pesquisa, dossiês, alertas, WhatsApp, Telegram, smartwatch e acionamento remoto só devem ser construídas quando reduzirem trabalho sem enfraquecer a precisão dos cortes.

> **Fases anteriores:** precisão de corte, contexto, transcrição canônica, locutor, integração útil do Campaign Hub, ranking explicável, revisão e benchmark real.
>
> **Fase final futura:** plataforma de missões editoriais, pesquisa recente, dossiês rastreáveis, automações, alertas, canais móveis e integrações remotas.

A Furia poderá um dia ser uma plataforma de produção editorial assistida, mas isso é uma meta posterior. A expansão futura deve encontrar fontes melhores, contextualizar o material, reduzir trabalho manual e entregar cortes mais precisos; nunca deve competir com o núcleo de clipping.

A plataforma deve separar claramente quatro coisas que não podem ser confundidas: **descoberta**, **evidência**, **proposta editorial** e **publicação**. Encontrar uma notícia, imagem ou fala na internet não significa que ela esteja confirmada; um destaque do Campaign Hub não é automaticamente um corte; e um corte gerado não é automaticamente publicável.

## 2. Princípios permanentes

| Princípio | Regra operacional |
| --- | --- |
| Cortes antes de extras | Pesquisa, dossiês, alertas, formatos e integração remota devem melhorar a seleção e a revisão dos cortes, não competir com elas. |
| Contexto antes de impacto | Começo natural, antecedente, tese, resposta, evidência e payoff vencem slogan isolado ou frase viral. |
| Renan-first verificável | Não atribuir ao Renan fala de convidado, entrevistador ou outro integrante; incerteza de locutor vira revisão. |
| Chub como memória, não como verdade | Campaign Hub fornece seeds, contexto, riscos, proveniência e benchmark; não aprova automaticamente. |
| Fonte canônica | A transcrição fornecida pelo editor é preservada e usada explicitamente; Whisper/Gemini são alternativas declaradas, não substituições silenciosas. |
| Uma afirmação, várias fontes | Dossiês precisam separar fato confirmado, alegação, inferência, contradição e informação ainda não verificada. |
| Idempotência | Um comando, webhook ou reprocessamento repetido não pode criar jobs ou mensagens duplicadas. |
| Revisão antes de publicar | A Furia prepara e entrega pacotes; publicação automática em redes sociais fica fora do núcleo até existir governança explícita. |
| Privacidade por padrão | Tokens, cookies, transcrições privadas, mídia bruta e URLs internas não entram no Git nem em relatórios compartilhados. |
| Tudo auditável | Cada resultado precisa registrar fonte, data de coleta, versão, consulta, evidência, modelo, estado do job e decisão humana. |

## 3. O produto em camadas

A Furia deve evoluir em seis camadas, mantendo o Flask local como núcleo de processamento até que uma ponte remota seja escolhida.

| Camada | Função | Resultado esperado |
| --- | --- | --- |
| Motor de mídia | Ingestão, manifesto, intervalos, transcrição, análise audiovisual, seleção, ranking e FFmpeg | Cortes corretos e reproduzíveis |
| Memória editorial | Campaign Hub, exemplos publicados, aprovações, rejeições, headlines e formatos | Priors úteis e separados por conta/plataforma |
| Pesquisa e evidência | Busca recente, notícias, imagens, vídeos, fontes oficiais e timeline de fatos | Dossiês com rastreabilidade |
| Orquestração | Fila, estados, retries, cancelamento, idempotência, prioridades e permissões | Missões confiáveis e recuperáveis |
| Experiência | Dashboard, revisão, dossiê, console, notificações e comandos remotos | Menos cliques e menos interpretação manual |
| Aprendizado editorial | Feedback humano, motivos de rejeição, ajustes, métricas e benchmarks | Melhoria medida sem contaminar score com ruído |

## 4. A principal evolução: um pipeline de corte de ponta

### 4.1 Manifesto e identidade da fonte

Toda fonte deve gerar um manifesto contendo URL ou caminho, duração, streams, resolução, hash leve, ID do vídeo quando existir, data de ingestão, intervalo escolhido e relação com a fonte original. Uma identidade persistente de intervalo deve distinguir `live inteira`, `00:00–05:00` e `05:00–10:00`, permitindo deduplicar a mesma faixa sem bloquear outra faixa da mesma live.

O manifesto também deve dizer se a mídia é `processing_source` ou `reference_only`. Reels e cortes publicados continuam sendo referência editorial; lives longas e arquivos crus são fontes de processamento.

### 4.2 Transcrição canônica e diagnóstico de cobertura

A Furia precisa exibir, antes de qualquer contexto, qual transcrição está usando: fornecida pelo usuário, legenda pública, Whisper local, Gemini ou fallback. O painel deve mostrar cobertura temporal, número de segmentos, idioma, confiança disponível, lacunas e se houve rebase por intervalo.

Quando o editor inserir uma transcrição manual, o sistema deve bloquear uma retranscrição silenciosa. Se houver conflito entre transcrição manual e automática, o Furia deve oferecer comparação e declarar qual foi usada para a seleção.

### 4.3 Context Composer

Em vez de enviar o vídeo inteiro para uma análise de contexto, o motor deve montar um pacote compacto por candidato com: frases anteriores, frase atual, frases posteriores, entidades, pergunta e resposta próximas, mudanças de locutor, tópicos, riscos, timestamps, sinais visuais necessários e contexto do Campaign Hub. O vídeo comprimido só deve ser anexado quando a imagem for indispensável.

O contexto deve ter um veredito explicável: `completo`, `completo após expansão`, `incompleto`, `locutor incerto`, `evidência visual necessária` ou `revisão obrigatória`.

### 4.4 Geração de candidatos em rede de janelas

Para cada seed, o Furia deve gerar várias janelas aninhadas: curta, média, expandida para o antecedente e expandida para o payoff. Cada janela deve ser avaliada por contexto, estrutura, locutor, risco, duração, qualidade da transcrição e evidência audiovisual. O ranking escolhe a **menor janela suficiente**, não a menor janela possível.

### 4.5 Gates antes do ranking

Nenhuma energia, palavra viral, métrica Chub ou headline deve compensar: locutor incorreto, começo no meio da frase, pergunta sem resposta necessária, final truncado, transcrição incompleta, risco factual sem suporte, mídia sem áudio, tela preta, duração inválida ou evidência visual cortada.

### 4.6 Ranking em três passagens

A arquitetura recomendada é: primeiro maximizar recall com candidatos amplos; depois aplicar gates estruturais; por fim ranquear os aprovados por autossuficiência, payoff, tese, energia, clareza, relevância Renan-first, risco, diversidade e compatibilidade de formato. Isso torna possível medir exatamente em qual fase um destaque foi perdido.

### 4.7 Diversidade e cobertura

A lista final não deve devolver cinco variações do mesmo assunto. Deve cobrir temas e blocos diferentes, preservar o melhor candidato de cada ideia e mostrar quando o orçamento de uma fonte longa foi insuficiente. Um “todos os cortes” correto significa todos os candidatos que passaram pelos critérios, não uma quantidade arbitrária.

### 4.8 Headline como verificação, não decoração

Para cada corte, gerar alternativas separadas para `16:9 original`, `1:1 Alfinetei`, `9:16` e `fake tweet`. Cada headline deve receber verificações de sujeito, verbo, objeto, fidelidade à fala, especificidade, contexto, legibilidade, tom e risco de exagero. Uma headline deve poder ser rejeitada mesmo quando o corte é bom.

### 4.9 Lint audiovisual e pacote final

Antes de exportar, validar codec, áudio, frames congelados, duração, proporção, legenda, safe area, sobreposição, headline encoberta, rosto ou documento cortado, tela preta, volume e continuidade de áudio. O resultado deve formar um pacote com vídeo, SRT, headline, intervalo original, versão, evidências, score, flags e checklist.

## 5. Automações realmente úteis

### 5.1 Missão “cortar esta fonte”

O editor envia uma URL, MP4, transcrição ou intervalo. A Furia cria o manifesto, baixa ou reutiliza a fonte, transcreve apenas se necessário, consulta a memória local, seleciona candidatos, renderiza previews e entrega uma fila de revisão com os melhores cortes e motivos de inclusão/exclusão.

### 5.2 Missão “encontre onde ele disse isso”

O editor envia uma frase como “prendeu-matou”. A Furia pesquisa transcrições locais, snapshots autorizados, blocos do Campaign Hub e fontes públicas, devolve possíveis lives, timestamps, confiança, links e trechos de contexto. A busca deve distinguir ocorrência literal, paráfrase e mera relação temática.

### 5.3 Garimpo pessoal de fontes longas

A Furia mantém uma fila de fontes candidatas: lives recentes, entrevistas, vídeos do MBL e links autorizados. Para cada uma, mostra duração, data, provável presença do Renan, status de ingestão, transcrição disponível, risco de anti-bot e prioridade editorial. Não deve baixar automaticamente todo o acervo.

### 5.4 Monitor de pauta quente

O editor cadastra termos, pessoas, eventos, locais e variações. O monitor consulta fontes recentes em intervalos controlados, agrupa ocorrências sobre o mesmo fato e alerta apenas quando há novidade relevante. Um alerta deve carregar “o que mudou”, “desde quando”, “quantas fontes independentes” e “qual fonte primária falta”.

GDELT é uma boa camada de descoberta porque seus fluxos informam atualização a cada 15 minutos e oferecem busca de artigos, temas, idiomas, fontes e imagens [1] [2]. Ainda assim, a Furia deve classificar o resultado como descoberta e buscar confirmação em fonte primária ou veículo confiável antes de transformá-lo em dossiê factual.

### 5.5 Dossiê de última hora

Para um pedido como “pesquise se Renan derrubou uma barricada na favela”, o fluxo ideal é:

1. normalizar a pergunta e extrair entidades, tempo, local e ação;
2. pesquisar variações linguísticas e sinônimos;
3. consultar fontes oficiais, veículos locais, GDELT, vídeos públicos, imagens e Campaign Hub;
4. agrupar resultados por evento e eliminar duplicações de republicação;
5. construir uma timeline com publicação, ocorrência e atualização;
6. separar fato, alegação, inferência e contradição;
7. localizar fotos e vídeos com origem, data, legenda, matéria associada e sinal de reutilização;
8. indicar o que ainda não foi confirmado;
9. sugerir cortes, perguntas de follow-up e headlines condicionadas ao grau de confirmação;
10. exportar um dossiê em Markdown/HTML com links e evidências.

O dossiê nunca deve escrever “Renan fez X” apenas porque uma única postagem afirma isso. A formulação deve ser “há uma alegação de X publicada por Y; foi corroborada por Z; a fonte primária permanece ausente” quando esse for o estado real.

### 5.6 Kit de mídia para pauta

Para cada dossiê, produzir uma pasta com links de matérias, imagens candidatas, vídeos, thumbnails, capturas autorizadas, créditos, datas, texto OCR, possível reutilização, licença quando disponível e relação com a afirmação. A Furia deve recomendar o ativo, não assumir que qualquer imagem encontrada representa o evento.

### 5.7 Briefing diário ou por demanda

Gerar um briefing com pautas recentes do universo Renan/MBL, mudanças desde o briefing anterior, links, relevância, nível de confirmação, possíveis fontes longas e oportunidades de corte. O briefing deve evitar repetição e registrar horário da última coleta.

### 5.8 Watchlist de eventos

Para cada evento acompanhado, guardar um dossiê vivo com fontes novas, correções, contraditórios, vídeos encontrados, imagens repetidas e evolução do vocabulário. O editor pode pedir “o que mudou desde ontem?” em vez de repetir toda a pesquisa.

### 5.9 Alertas de job

Enviar notificações somente para eventos acionáveis: fonte importada, transcrição pronta, candidatos prontos, falha que exige intervenção, intervalo concluído, pacote exportado ou job cancelado. Não enviar uma mensagem por cada progresso percentual.

### 5.10 Aprovação por mensagem

Uma mensagem pode conter os três melhores candidatos com botões `Abrir`, `Aprovar`, `Rejeitar`, `Contexto`, `Headline` e `Cancelar`. A aprovação deve exigir o identificador do candidato, versão do contexto e usuário autorizado; nunca aceitar apenas o texto “sim” fora de uma sessão identificada.

### 5.11 Reprocessamento seletivo

Se apenas a headline mudou, não repetir download, transcrição ou ranking. Se apenas a legenda mudou, reexportar legenda e lint. Se o contexto mudou, reabrir somente candidatos afetados. Cada etapa deve ter cache, versão e invalidadores explícitos.

### 5.12 Fila de revisão inteligente

Ordenar itens por urgência, risco, baixa confiança, headline pendente, problema técnico, presença de Renan, relevância do tema e proximidade de uma pauta quente. Mostrar o motivo da prioridade em linguagem simples.

### 5.13 Aprendizado com rejeições

Guardar rejeições com motivo controlado: `sem contexto`, `locutor errado`, `payoff ausente`, `começo abrupto`, `headline exagerada`, `repetido`, `técnico`, `não é Renan`, `não é pauta`, `evidência visual ausente`. Usar isso para regressões e calibração, não para transformar uma preferência de uma pessoa em verdade universal.

### 5.14 Comparador de cortes

Exibir duas janelas candidatas lado a lado com transcrição, contexto, score, flags, headline e explicação do que uma janela ganhou ou perdeu. Isso acelera a aprovação humana e produz dados de preferência muito melhores que um simples “gostei/não gostei”.

### 5.15 Busca semântica no acervo local

Indexar transcrições, headlines, dossiês e feedback em busca textual/semântica para encontrar exemplos parecidos: “mostre cortes onde Renan responde uma acusação”, “encontre headlines 1:1 sobre segurança” ou “qual rejeição mais comum em lives?”.

### 5.16 Relatório de saúde editorial

Mostrar semanalmente recall medido, taxa de aprovação, taxa de rejeição por motivo, locutor incerto, transcrição corrigida, headline rejeitada, reexportação, tempo economizado e diferenças entre modo Chub e modo local.

## 6. Canais de acionamento remoto

### 6.1 WhatsApp

A integração oficial da Meta permite receber mensagens por webhook e enviar texto, mídia e mensagens interativas [3] [4]. O desenho deve ter endpoint público HTTPS, validação, deduplicação, fila e resposta rápida. A Meta informa que webhooks podem ser reenviados por até sete dias após falha e que duplicidades podem ocorrer [3]; por isso, `message_id` precisa ser uma chave idempotente.

O WhatsApp é atraente por estar no celular do usuário, mas exige conta Meta/WhatsApp Business, número, tokens, webhook, opt-in e atenção à janela de atendimento de 24 horas; fora dela, templates pré-aprovados podem ser necessários [4] [5]. É uma integração de produção, não o primeiro protótipo sem configuração.

### 6.2 Telegram

O Telegram oferece uma API HTTP, recebimento por polling ou webhook HTTPS, token secreto no header do webhook e teclados inline que podem disparar callbacks [6] [7]. Isso o torna adequado para uma prova de conceito rápida de comandos, aprovações e envio de documentos, sem exigir a mesma configuração empresarial do WhatsApp.

### 6.3 Smartwatch

Não começar por um aplicativo nativo de relógio. Em Wear OS, notificações do telefone podem ser automaticamente encaminhadas ao relógio e podem incluir ações, respostas por voz e escolhas predefinidas [8]. O relógio deve ser uma superfície de “glance”: `3 cortes prontos`, `aprovar`, `rejeitar`, `cancelar`, `abrir no telefone`. O processamento e a revisão completa permanecem no telefone ou computador.

### 6.4 Opções arquiteturais

| Abordagem | Experiência | Trade-offs | Custo recorrente | Complexidade |
| --- | --- | --- | --- | --- |
| Local + Telegram polling | O usuário envia comandos e a Furia local responde enquanto o computador está ligado | Zero servidor público; não funciona com o computador desligado; segurança precisa restringir chat | Baixo, fora consumo de APIs | Baixa |
| Control plane hospedado + worker local | O celular envia comandos para uma fila remota; o computador local executa FFmpeg e devolve resultados | Melhor equilíbrio de privacidade e acesso remoto; exige um pequeno serviço persistente e ponte autenticada | Uso do serviço e APIs escolhidas | Média |
| WhatsApp Cloud API + control plane + worker | Experiência natural no WhatsApp, com botões, mídia e notificações | Configuração Meta, opt-in, templates, webhooks, políticas e manutenção | Variável conforme mensagens/serviço | Média/alta |
| Plataforma toda em nuvem | Funciona mesmo com notebook desligado e escala mais facilmente | Upload de fontes grandes, custo de armazenamento/transcodificação, privacidade e dependência externa | Médio/alto | Alta |
| App móvel próprio + push + smartwatch | Melhor produto final, fila, revisão e notificações nativas | Mais tempo de desenvolvimento, publicação e manutenção de dois sistemas | Variável | Alta |

A evolução deve manter o motor pesado local enquanto o volume e a confidencialidade justificarem isso. O control plane remoto pode carregar somente comandos, estados, hashes, thumbnails e resultados sanitizados; a mídia bruta fica no worker local. O primeiro canal pode ser Telegram ou outro canal que o usuário escolha, enquanto WhatsApp fica como adaptação de produção. A decisão final do canal deve ser feita quando o usuário puder autorizar as credenciais e definir se o computador precisa continuar ligado.

## 7. Arquitetura de missões

Toda ação remota deve ser convertida em uma missão versionada:

```text
mensagem / botão / interface
        ↓
intenção estruturada + usuário autorizado
        ↓
planejador de missão
        ↓
fila idempotente com prioridade e orçamento
        ↓
worker de mídia / pesquisa / dossiê
        ↓
artefatos + evidências + estado
        ↓
revisão humana e entrega por canal
```

Uma missão deve ter `mission_id`, `request_id`, usuário, canal, intenção, parâmetros, fontes permitidas, limites de pesquisa, prazo, estado, tentativas, custo estimado, artefatos e auditoria. Estados recomendados: `received`, `authorized`, `planned`, `queued`, `running`, `waiting_review`, `completed`, `failed`, `cancelled`, `expired`.

O planejador não deve conceder a si mesmo permissões. Ações de leitura, download, transcrição, geração de dossiê, renderização, aprovação e publicação precisam de escopos distintos. Publicação externa deve exigir confirmação explícita e, inicialmente, permanecer fora da automação.

## 8. Design da experiência

### Dashboard “Hoje”

A tela inicial deve mostrar missões recentes, jobs em andamento, cortes que aguardam revisão, pautas quentes, fontes disponíveis, alertas de falha e memória Chub atualizada. Não mostrar apenas botões de ferramenta; mostrar trabalho pendente e decisões necessárias.

### Caixa de entrada de missões

Cada pedido recebido por texto, upload ou link vira um cartão com intenção reconhecida, parâmetros, risco, origem, prazo e ações. Se a Furia entendeu “pesquisar” como “cortar”, o usuário corrige antes da execução.

### Central de revisão

A central deve apresentar vídeo, transcrição, contexto, locutor, intervalo, headline, formato, score, motivos de inclusão, motivos de risco, evidência Chub e comparação com alternativas. `Aprovar`, `Rejeitar` e `Reprocessar` precisam ser ações claras e reversíveis.

### Dossiê

O dossiê deve ter resumo executivo, pergunta original, resposta atual, timeline, matriz de afirmações, fontes, imagens, vídeos, entidades, contradições, grau de confirmação e sugestões de próximos passos. Cada afirmação deve apontar para as fontes que a sustentam.

### Console útil

O console deve manter log completo copiável, filtro por missão/job, busca por erro, download de pacote sanitizado e distinção entre mensagem operacional, alerta, evidência e erro. Um usuário não técnico deve entender “o que aconteceu” sem interpretar stack trace.

### Celular e relógio

No celular, a primeira experiência pode ser uma conversa com bot + botão para abrir a revisão web. No relógio, somente alertas curtos e ações reversíveis. Não tentar editar timeline ou assistir longos vídeos no relógio.

## 9. Segurança, veracidade e governança

A camada de pesquisa precisa tratar notícias recentes como informação potencialmente contraditória. Toda resposta deve trazer horário da coleta, URLs, fonte, data do fato versus data da publicação, duplicação de matéria, nível de confiança e lacunas. A Furia não deve fabricar uma imagem de uma barricada, completar uma alegação com memória ou usar uma foto antiga como se fosse atual.

Os comandos remotos precisam de allowlist de usuários, rotação de tokens, segredo de webhook, limite de frequência, proteção contra replay, registro de auditoria, confirmação para ações destrutivas e expiração de links. Webhooks devem responder rápido e delegar trabalho à fila. Nenhuma credencial deve entrar em prompts, logs ou Git.

O sistema também precisa de limites editoriais para temas sensíveis. Alegações criminais, acusações, violência, identidade de pessoas, crianças, localização precisa e acontecimentos em curso devem receber revisão obrigatória e linguagem condicional quando não houver confirmação suficiente.

## 10. Roadmap priorizado

| Prioridade | Entrega | Motivo | Dependência |
| --- | --- | --- | --- |
| P0 | Identidade persistente de intervalo | Evita duplicação e bloqueio de faixas diferentes | SQLite, regressões |
| P0 | Transcrição canônica explícita | Evita o bug de ignorar transcrição fornecida | Fluxo atual de transcrição |
| P0 | Context Composer com limites | Reduz estouro de tokens e melhora contexto | Transcrição e entidades |
| P0 | Lint audiovisual pré-exportação | Evita entregar cortes tecnicamente quebrados | FFprobe/FFmpeg existentes |
| P0 | Fila de revisão com motivos | Transforma candidatos em decisões rápidas | Dados de candidatos |
| P1 | Feedback estruturado de aprovação/rejeição | Cria aprendizado editorial real | Banco e UI |
| P1 | Dossiê por demanda | Expande a Furia sem misturar prova e alegação | Pesquisa web + fontes |
| P1 | Descoberta GDELT + fontes primárias | Acelera pautas recentes e imagens candidatas | APIs e política de fontes |
| P1 | Garimpo pessoal de fontes longas | Encontra material para cortar sem baixar tudo | Ingestão e manifesto |
| P1 | Briefing e watchlist | Automatiza acompanhamento de temas | Serviço persistente/cron |
| P1 | Telegram ou canal de comandos | Primeira operação remota de baixa fricção | Token e endpoint/polling |
| P2 | Ponte control plane + worker local | Permite usar celular com computador ligado | Serviço persistente e autenticação |
| P2 | WhatsApp Cloud API | Canal natural para uso de escritório | Meta Business, webhook, opt-in |
| P2 | Pacote de mídia do dossiê | Reúne fontes, imagens, vídeos e créditos | Pesquisa e storage |
| P2 | Aplicativo móvel/PWA | Revisão e alertas melhores que chat puro | Backend remoto |
| P3 | Ações no smartwatch | Aprovações e alertas rápidos | Notificações móveis |
| P3 | Nuvem para renderização | Libera dependência do notebook | Custos, storage, privacidade |
| P3 | Publicação assistida | Envia para plataformas após confirmação | APIs oficiais e governança |

## 11. Critério de sucesso do novo norte

A plataforma será considerada realmente melhor quando, em um benchmark de lives longas do Renan/MBL, ela aumentar ou preservar recall sem perder autossuficiência, reduzir falsos positivos de locutor, diminuir revisões inúteis, respeitar a transcrição fornecida, gerar headlines fiéis e permitir que o editor conclua uma missão com menos operações manuais.

Para a camada de pesquisa, sucesso significa que um dossiê recente deixa claro o que foi encontrado, quando, por quem foi publicado, qual evidência corrobora ou contradiz a afirmação e quais imagens/vídeos são apenas candidatos. Velocidade sem rastreabilidade não é qualidade.

## 12. O que não fazer agora

Não começar pelo smartwatch nativo, por publicação automática, por baixar todo o acervo do Instagram, por uma cópia integral do Campaign Hub, por um agente que navega sem limites, por um ranking treinado em métricas agregadas sem aprovação humana ou por um dossiê que transforma um único post em fato.

Não transformar a Furia em um editor genérico antes de resolver corte, contexto, locutor, transcrição, headline e revisão. Não conectar WhatsApp ou qualquer serviço externo dentro do Flask local sem considerar que um computador desligado não recebe webhook. Não usar tarefas agendadas de alta frequência para polling; um serviço persistente ou cron apropriado deve executar a coleta.

## Referências

[1]: https://www.gdeltproject.org/ "GDELT Project"
[2]: https://www.gdeltproject.org/data.html "GDELT Data and live APIs"
[3]: https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview "Meta WhatsApp Webhooks"
[4]: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started "Meta WhatsApp Cloud API Get Started"
[5]: https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages "Meta WhatsApp Service Messages"
[6]: https://core.telegram.org/bots/api "Telegram Bot API"
[7]: https://core.telegram.org/api/bots/buttons "Telegram Bot Buttons"
[8]: https://developer.android.com/training/wearables/notifications "Android Developers — Notifications on watches"
