# Fluxo de fonte, Gemini persistente e dois notebooks

## O que mudou

O painel de link público agora possui duas ações independentes:

- **Baixar somente**: baixa e une vídeo/áudio até a qualidade escolhida, sem procurar legenda, chamar Gemini ou iniciar Whisper.
- **Baixar e transcrever**: baixa a fonte e gera uma transcrição apenas quando não existe uma transcrição manual confirmada. Se a transcrição manual já foi aplicada na aba **Transcrição**, ela é anexada ao projeto e reutilizada sem nova busca pública, Gemini ou Whisper.

A importação também possui uma trava contra duplo clique. O dashboard de jobs passou a impedir carregamentos concorrentes e a deduplicar mensagens idênticas no console; atualizações reais de progresso continuam visíveis.

O botão **Abrir pasta** do vídeo selecionado usa a rota segura existente do aplicativo e abre diretamente a pasta permitida do arquivo.

## Configuração Gemini persistente

Ao salvar a chave pela interface, ela é gravada fora do checkout em:

```text
FuriaClipsData/config/local.env
```

O aplicativo lê esse arquivo antes do `.env` local do repositório. Assim, substituir ou atualizar a pasta do GitHub não remove a configuração. O arquivo nunca deve ser versionado nem enviado ao GitHub.

Para usar dois notebooks, há duas opções seguras:

1. usar a mesma pasta `FuriaClipsData` em uma pasta sincronizada deliberadamente, como OneDrive, mantendo apenas um notebook executando o aplicativo por vez; ou
2. copiar uma vez o arquivo `FuriaClipsData/config/local.env` para o segundo notebook e salvar a chave pela interface se ela for renovada.

Quando `FURIA_CLIPS_DATA_DIR` é definido nos dois computadores apontando para a mesma pasta sincronizada, o banco editorial, transcrições, decisões e o arquivo `config/local.env` seguem o mesmo diretório. Não é recomendado executar duas instâncias simultâneas contra o mesmo SQLite sincronizado.

## Métricas observadas

Essa aba registra resultados **depois da publicação**. O usuário cola um snapshot autorizado ou uma anotação manual com views, curtidas, comentários, compartilhamentos, salvamentos e janela de observação. O Furia Clips calcula quantidade de conteúdos, views observadas, velocidade aproximada e engajamento informado.

As métricas não são a transcrição, não substituem os gates de contexto e não são uma previsão automática de viralização. Elas servem para calibrar sinais locais depois que há dados reais. O programa não inventa retenção nem tenta reproduzir fórmulas privadas de plataformas.

## Sinais técnicos consultados no Campaign Hub e no Garimpo

O Campaign Hub foi consultado exclusivamente em modo de leitura. Os sinais mais úteis para a precisão foram a existência de blocos QA-gated, a validação temporal `end > start`, a densidade como sinal secundário e a separação entre cobertura do acervo e desempenho. O Furia Clips incorporou apenas a invariável temporal e manteve o restante como referência agregada; nenhum conteúdo bruto foi enviado de volta ao serviço.

O Garimpo foi tratado como referência de observação de desempenho e contexto, não como dependência obrigatória. Como seus critérios internos não são integralmente expostos como contrato público, o aplicativo não finge reproduzir sua fórmula. Os gates locais continuam priorizando início compreensível, pergunta–resposta completa, evidência, payoff, troca de locutor e timestamps confiáveis.
