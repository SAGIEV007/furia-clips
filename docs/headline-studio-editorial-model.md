# Estúdio de Texto de Arte

## Propósito

O Estúdio de Texto de Arte gera apenas a cópia que será colocada **dentro do vídeo**. Ele não produz SEO, hashtags, descrição de postagem ou metadados de publicação. A entrada pode ser uma transcrição manual, um arquivo `.txt`, `.srt` ou `.vtt`, ou a transcrição já carregada para o corte.

A análise usa a transcrição e um minicontexto opcional para localizar a tese, o contraste, a consequência e o grau de conclusão. O minicontexto orienta a intenção do editor, mas não autoriza o sistema a inventar fatos, acusações, números ou falas que não estejam claramente sustentadas no corte.

## Formatos editoriais

| Formato | Uso visual | Limite aplicado | Saída esperada |
| --- | --- | ---: | --- |
| `vertical_916` | Headline central em amarelo, texto preto e destaque pontual branco em vermelho | 58 caracteres | Headline curta, possível palavra/trecho de destaque e quebra visual em até três linhas |
| `square_alfinetei` | Chamada curta no topo e headline branca em peça 1:1 | 18 + 64 caracteres | Palavra de atenção e uma headline enxuta em até três linhas; não há descrição separada |
| `fake_tweet` | Simulação de publicação do perfil com vídeo incorporado | 180 caracteres | Rascunho conciso de publicação, sujeito à revisão antes de atribuição ao perfil |

A recomendação do formato é explicável. Uma tese com desenvolvimento suficiente tende a favorecer `square_alfinetei`; conflito imediato e leitura de impacto tendem a favorecer `vertical_916`; uma posição autoral claramente expressa pode sugerir `fake_tweet`. O editor pode sempre forçar um formato.

## Base editorial aplicada

A calibração inicial usa a análise pública já documentada dos Reels acessíveis dos perfis `@renansantosmbl` e `@renansantosreserva`. A base identifica a recorrência de hook textual, frases curtas em alto contraste, alternância entre rosto âncora e evidência, retorno à conclusão e uso seletivo de cores para voz, citação ou alerta.[^1] Ela não afirma que a amostra representa toda a história dos perfis nem usa métricas privadas de retenção.

O motor não replica uma frase antiga. Ele aplica princípios observados: tese reconhecível, conflito ou consequência claros, legibilidade em poucas linhas e atribuição cautelosa quando há afirmação factual, jurídica ou acusatória.

## Aprendizado persistente

Quando o editor usa **Escolher** em uma sugestão, a decisão é gravada em `headline_feedback` dentro de `FuriaClipsData/database/editorial_learning.sqlite3`. São preservados formato, texto escolhido, tema, excerto de transcrição e minicontexto. Esses dados ficam fora do checkout GitHub, entram no Backup Editorial e sobrevivem à substituição da pasta do programa.

A coleta é deliberadamente local e revisável. O sistema mostra o número de escolhas acumuladas e a distribuição por formato, sem tratar uma escolha isolada como “treinamento” estatístico confiável. À medida que o editor acumular escolhas e rejeições, o próximo passo seguro será comparar padrões aprovados por tema, formato, duração e família editorial.

## Alertas de revisão

O Estúdio marca quando a transcrição termina no meio de uma frase e reaproveita os alertas factuais/jurídicos do perfil político. Esses alertas não bloqueiam a geração de uma headline; eles impedem que o resultado seja confundido com uma verificação de verdade e orientam revisão humana antes de publicar alegações sensíveis.

## Limites da análise de perfis

A rotina autônoma pode ampliar a base apenas com vídeos públicos que estejam acessíveis de forma legítima. Quando a plataforma negar paginação, autenticação ou mídia, o estado deve ser registrado como pendente e o desenvolvimento continua com o corpus já disponível. O programa não contorna restrições de plataforma.

## Referências

[^1]: [Catálogo editorial e análise audiovisual consolidada](instagram-mbl-catalog-analysis.md) e [achados visuais da amostra principal](instagram_mbl_sample_visual_findings.md).
