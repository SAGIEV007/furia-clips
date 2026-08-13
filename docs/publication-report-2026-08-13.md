# Relatório final de publicação — Furia Clips

## Resultado da publicação

A versão especializada foi publicada no repositório [SAGIEV007/furia-clips](https://github.com/SAGIEV007/furia-clips). A branch `manus/rebuild-opus-parity` recebeu 15 commits à frente da antiga branch `devin/1782248654-furia-clips`, incluindo o pipeline reconstruído, o perfil político, a interface, os testes e a documentação. Ela foi definida como a **branch padrão** do repositório, portanto o botão de download e novos clones passam a receber a versão validada.

A tentativa de criar um merge técnico pela API do GitHub retornou HTTP 403 (`Resource not accessible by integration`) e a abertura de pull requests está desabilitada pelo proprietário. Como a comparação indicou que as branches eram mescláveis automaticamente, a solução funcional foi publicar integralmente na branch de trabalho e torná-la a branch padrão. A antiga branch `devin/1782248654-furia-clips` permanece preservada como histórico e backup.

## O que foi implementado

O modo `renan_santos_politics` classifica os candidatos em cinco formatos: confronto/reação, proposta/programa, dado/denúncia, discurso/posicionamento e mobilização. O ranking expõe sinais de relevância temática, tese, conflito, proposta, evidência, mobilização, especificidade, conclusão, aderência ao perfil e completude de contexto.

A completude de contexto penaliza aberturas que começam com pronomes ou referências sem antecedente no próprio trecho. Quando o pipeline fornece mudanças de cena, a densidade visual passa a ser usada como sinal opcional de ritmo. A energia de áudio agora é calculada pelas janelas que realmente caem dentro de cada clip, em vez de retornar sempre um valor neutro.

O preset `political_shorts` exporta em 1080×1920, preserva uma área segura vertical maior e usa legendas palavra a palavra com destaque de impacto. Termos políticos fortes e números presentes na transcrição podem receber o estilo de alerta vermelho, sem inventar texto. A política de áudio é `voice_and_ambience`: o aplicativo preserva voz e ambiente e não adiciona música genérica automaticamente. O editor pode acrescentar uma trilha licenciada quando isso fizer sentido.

A interface agora possui o seletor de perfil editorial, chips de contexto político, o preset Política Editorial — 9:16 e a identificação do tipo editorial na revisão humana. A documentação pública registra a matriz de padrões e a amostra descritiva de Shorts.

## Validação

A suíte local terminou com **40 testes aprovados**. Foram cobertos o perfil político, contexto de abertura, ranking por tema, energia por janela, densidade de mudanças de cena, legendas com destaque, margem segura vertical, smoke tests HTTP, renderização real com FFmpeg e validação de mídia com `ffprobe`.

## Limite importante da análise audiovisual

A análise anterior não foi vídeo por vídeo de todas as publicações dos perfis. A pesquisa realizada nesta etapa examinou uma amostra pública verificável, combinando páginas indexadas, títulos, visualizações, copies disponíveis e os vídeos que puderam ser processados/observados. Os relatórios distinguem observação direta de hipótese e não afirmam acesso a métricas privadas de retenção, compartilhamento ou conclusão.

Consequentemente, o Furia Clips já está melhor orientado para cortes políticos autossuficientes no estilo editorial desejado, mas a calibração de potencial viral ainda deve ser refinada com exports reais aprovados/rejeitados pelo editor e métricas próprias dos canais.

## Como usar

Baixe o ZIP da [branch padrão atual](https://github.com/SAGIEV007/furia-clips/archive/refs/heads/manus/rebuild-opus-parity.zip) ou clone o [repositório](https://github.com/SAGIEV007/furia-clips). Depois instale Python 3.10 ou superior, FFmpeg e `ffprobe`, execute `run.bat` no Windows ou crie um ambiente virtual e rode `python app.py` no Linux/macOS.

Na interface, selecione **Perfil editorial → Renan Santos / MBL**, use os chips para orientar a busca e informe um contexto textual específico, como “encontre confrontos jurídicos com consequência clara” ou “encontre propostas de segurança pública com números”. Para a saída vertical dedicada, escolha **Política Editorial — 9:16**. Revise os candidatos, aprove ou rejeite os cortes e só então utilize os exports finais.

## Referências do projeto

- [Branch padrão publicada](https://github.com/SAGIEV007/furia-clips/tree/manus/rebuild-opus-parity)
- [Branch histórica preservada](https://github.com/SAGIEV007/furia-clips/tree/devin/1782248654-furia-clips)
- [Guia do perfil editorial](https://github.com/SAGIEV007/furia-clips/blob/manus/rebuild-opus-parity/docs/editorial-profile.md)
- [Matriz de padrões audiovisuais](https://github.com/SAGIEV007/furia-clips/blob/manus/rebuild-opus-parity/docs/video-analysis/editorial-patterns.md)
- [Amostra descritiva](https://github.com/SAGIEV007/furia-clips/blob/manus/rebuild-opus-parity/docs/video-analysis/shorts-sample-analysis.md)
