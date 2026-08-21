# Pesquisa de automação remota — 2026-08-21

## WhatsApp Business Platform

As páginas oficiais da Meta consultadas em 2026 informam que a WhatsApp Business Platform Cloud API permite enviar mensagens de texto, mídia e mensagens interativas, além de receber eventos por webhooks. O webhook pode informar mensagens recebidas, estados de mensagens enviadas, eventos de chamada e mudanças de conta. A página de webhooks informa que os payloads são JSON, podem chegar a 3 MB e podem ser reenviados por até 7 dias quando o endpoint não retorna HTTP 200; portanto, o receptor da Furia precisa ser idempotente por `message_id` e responder rapidamente.

A documentação de início exige uma conta de desenvolvedor/Meta, um app com WhatsApp, um número habilitado e configuração de webhook. Para produção, o token temporário de teste não basta: a Meta recomenda um system user e token permanente armazenado com segurança. Mensagens livres dependem da janela de atendimento de 24 horas após uma mensagem do usuário; fora dela, devem ser usadas mensagens template pré-aprovadas e opt-in. Isso torna WhatsApp viável, mas com maior custo de configuração, política e manutenção.

A arquitetura recomendada para a Furia não deve receber uma mensagem e processá-la dentro do próprio request do webhook. O webhook deve validar origem, deduplicar `message_id`, colocar a intenção em fila, responder 200 rapidamente e enviar depois uma mensagem de andamento. A confirmação de resultado deve depender de status de entrega do webhook, não apenas da aceitação da API.

## Telegram Bot API

A documentação oficial do Telegram descreve uma API HTTP para bots, com recebimento por `getUpdates` ou webhook HTTPS. O `setWebhook` pode usar um `secret_token` enviado no header `X-Telegram-Bot-Api-Secret-Token`, o que facilita validar a origem. A API também oferece teclados de resposta e inline keyboards; botões inline podem disparar callback data sem que o usuário precise escrever outra mensagem.

Para a Furia, Telegram é um caminho técnico mais simples para a primeira prova de conceito de comando remoto: `/pesquisar`, `/dossie`, `/cortar`, `/status`, `/cancelar` e botões `Aprovar`, `Rejeitar`, `Ver contexto`, `Gerar headline` e `Abrir projeto`. A documentação também expõe envio de documentos, fotos e vídeos, o que combina com relatórios e previews. O bot deve restringir chat/user IDs autorizados e nunca aceitar comandos de grupo por padrão.

## Wear OS

A documentação oficial do Android informa que notificações criadas no telefone são automaticamente encaminhadas para relógios pareados; uma aplicação de relógio própria só é necessária para experiências específicas. Notificações expansíveis e ações são suportadas, inclusive respostas por voz ou escolhas predefinidas. Uma ação disparada no relógio normalmente executa no telefone, que pode abrir o app correspondente.

A conclusão arquitetural é não começar por um app nativo de smartwatch. O relógio deve ser a superfície de alerta e confirmação curta: `job concluído`, `3 cortes prontos`, `aprovar`, `rejeitar`, `cancelar`, `abrir no telefone`. O comando completo pode sair do Telegram/WhatsApp ou do app móvel, e o relógio recebe a notificação do telefone. Isso reduz custo e mantém o relógio fora do processamento pesado.

## Referências consultadas

- Meta, [Webhooks](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview), atualizado em 26 jun. 2026.
- Meta, [WhatsApp Cloud API Get Started](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started), atualizado em 16 jun. 2026.
- Meta, [Service messages](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages), atualizado em 21 maio 2026.
- Meta, [About the WhatsApp Business Platform](https://developers.facebook.com/documentation/business-messaging/whatsapp/about-the-platform), atualizado em 4 ago. 2026.
- Telegram, [Bot API](https://core.telegram.org/bots/api), documentação oficial consultada em 21 ago. 2026.
- Telegram, [Bot buttons](https://core.telegram.org/api/bots/buttons), documentação oficial consultada em 21 ago. 2026.
- Android Developers, [Notifications on watches](https://developer.android.com/training/wearables/notifications), documentação oficial consultada em 21 ago. 2026.

## Descoberta de notícias, imagens e cobertura recente

O GDELT informa que monitora notícias impressas, transmitidas e web em mais de 100 idiomas, com atualização de seus fluxos a cada 15 minutos. Sua documentação descreve APIs JSON de busca textual, geográfica e televisiva, além de recursos de busca de imagens e metadados visuais. O DOC API pode retornar listas de artigos, RSS, galerias e imagens processadas, e permite restringir buscas por domínio, país, idioma, tema, proximidade textual, repetição de termo e sinais visuais como OCR, tags de imagem, número de faces e recorrência na web.

A recomendação é usar GDELT como camada de descoberta e triangulação, nunca como prova única. Para uma pergunta como “Renan derrubou uma barricada na favela?”, a Furia deve buscar variações do evento em GDELT, fontes oficiais, veículos locais, perfis públicos e Campaign Hub; agrupar artigos que apontam para o mesmo fato; extrair data, local, pessoas, verbos e grau de confirmação; e só então montar o dossiê. Imagens encontradas devem carregar URL da matéria, data de publicação, origem, legenda, sinal de reutilização e alerta de possível associação incorreta.

O GDELT é abrangente, mas não garante que todo acontecimento local ou publicação social esteja indexado. A aplicação deve mostrar `descoberto`, `corroborado`, `não confirmado` ou `contradito`, manter cada afirmação vinculada a suas fontes e impedir que uma busca de última hora seja transformada automaticamente em headline factual ou corte publicado.

O Bing Web Search API apareceu nos resultados como serviço com histórico de descontinuação/aposentadoria; portanto, não deve ser tratado como dependência principal sem uma verificação específica de disponibilidade. O desenho deve aceitar provedores substituíveis e começar por APIs/fontes cuja documentação e disponibilidade estejam confirmadas no momento da implementação.

Referências adicionais:

- GDELT, [The GDELT Project](https://www.gdeltproject.org/).
- GDELT, [Data: Querying, Analyzing and Downloading](https://www.gdeltproject.org/data.html).
- GDELT, [DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/).
