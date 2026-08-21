# Correção: Timeout na Análise de Contexto e Falha de Apenas Cortes
Data: 21/08/2026

## Diagnóstico
O usuário relatou que o botão "Apenas cortes" não funcionou, e o log fornecido terminava com:
```
[Contexto] A análise de contexto excedeu o tempo esperado; verifique o console.
[Job 7b06e466] Contexto integral concluído
```

Ao investigar o código, descobrimos que **o usuário não havia clicado em "Apenas cortes"**. O fluxo executado (job `7b06e466`) era, na verdade, a rota autônoma `/api/editorial/context`, disparada pelo botão "Analisar contexto integral" na interface.

Nesta rota, o frontend (`app.js`) usava um `pollEditorialContextJob` que tinha um timeout rígido de **20 minutos** (linhas 2758-2760).
Como a live do Renan tinha mais de 1h30 e o Gemini devolveu erro 503 por sobrecarga (linhas 49-54 do log), o sistema ativou o **fallback de análise de áudio local** (energia). Esse processo local varreu mais de 6500 janelas de áudio, o que levou tempo suficiente para o frontend estourar o limite de 20 minutos e jogar a mensagem de erro na tela.
Apesar do erro no frontend, o backend concluiu o trabalho (linha 92 do log).

## Correção Implementada
- **Frontend (`app.js`)**: O limite de tempo no `pollEditorialContextJob` foi estendido de 20 minutos para **60 minutos**, permitindo que lives massivas processem o áudio local sem desconectar o painel de status do usuário.
- O botão de "Cortar shorts" / "Processo completo" usa o socket em vez de polling síncrono e já está imune a esse problema.

## Sobre a Falha da Headline com IA
A imagem fornecida mostra a mensagem: *"Nenhuma headline saiu deste trecho: não há um assunto que a fonte repita e nenhuma frase se sustenta sozinha..."*.

Ao cruzar isso com o `headline_studio.py` (linhas 351-382), verificamos que isso **não é um erro técnico nem falha de chave do Gemini**. O sistema rejeitou a geração de arte de propósito porque a legenda fornecida (um trecho aleatório inserido manualmente) não continha uma citação válida (mínimo de 4 palavras com sentido completo). O Furia bloqueia a IA de inventar coisas e retorna exatamente esse aviso para proteger a credibilidade do corte. Isso prova que o gate editorial está funcionando como projetado.
