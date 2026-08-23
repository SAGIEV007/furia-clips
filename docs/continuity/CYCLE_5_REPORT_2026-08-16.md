# Relatório do ciclo 5 — Furia Clips 1.5

## Resumo executivo

A rodada aplicou o Prompt 2 corrigido com foco em Renan Santos/MBL, na estabilidade do pipeline e na qualidade editorial antes de qualquer evolução do Estúdio de Texto de Arte. Foram implementadas duas mudanças observáveis: uma operação separada para transcrever uma fonte pública por URL, baixando áudio por padrão e sem criar projeto ou cortes; e um gate técnico final que mantém candidatos com revisão editorial explícita fora da renderização pronta, preservando-os para diagnóstico.

A versão pública foi incrementada de 1.4 para **1.5**. A branch de trabalho permanece `manus/rebuild-opus-parity`.

## Hipótese única da melhoria editorial

> Se o ranker já identifica uma pergunta sem ponte pergunta–resposta validada ou uma alegação sensível sem contexto/evidência explícitos, esse candidato não deve ser apresentado como corte pronto apenas porque tem score alto; deve ser adiado para revisão humana, mantendo intervalo, texto e motivos no diagnóstico.

O gate anterior de `context_complete=false` foi preservado. A nova regra atua depois do ranking e antes do `VideoCutter`.

## Implementações

### Transcrição por URL

Foi adicionada a rota assíncrona `POST /api/source/transcribe`. Ela valida a URL pública, enfileira um job persistente, baixa áudio com `format=ba/b` por padrão, valida a presença de áudio, executa o caminho de transcrição existente, arquiva o resultado e não cria projeto nem gera cortes. O download de vídeo permanece reservado ao fluxo de ingestão operacional para cortes.

O frontend recebeu um botão separado de “somente transcrever”. Ele envia `media_type: "audio"`, acompanha o job persistente e carrega o transcript no editor sem iniciar a renderização. O cancelamento reutiliza o contrato existente de jobs.

O smoke test real com `https://www.youtube.com/watch?v=d6Y8xQTmw3o` confirmou o enfileiramento no modo áudio e o diagnóstico sanitizado da falha. O YouTube recusou o download nesta sessão por verificação anti-bot; nenhum arquivo, cookie ou credencial foi utilizado e nenhum corte foi gerado. Os testes unitários cobrem o caminho de áudio, o contrato da rota, a validação de URL, a persistência e a separação entre transcrição e corte.

### Gate técnico antes da renderização

A função `_defer_context_incomplete_candidates` passou a adiar também candidatos cujo `technical_gate_status` seja `review`. Os motivos de `technical_gate_reasons` são preservados, e o job expõe contadores separados para contexto e revisão técnica. O diagnóstico também foi corrigido para preservar `start_time` e `end_time` dos candidatos persistidos.

## Mídia real processada

| Fonte | Duração | Transcrição | Resultado |
|---|---:|---|---|
| Coletiva de imprensa sobre a pré-candidatura e o vice | 33m38s | 372 segmentos nativos; qualidade estrutural 100/100 | 12 exports H.264/AAC em 16:9; diagnóstico de contexto, Q&A e revisão técnica |
| `OÚLTIMOANÁLISESRENAIS.mp4` | 98m25s | 1.429 segmentos Whisper local em dez lotes; 86.837 caracteres; qualidade estrutural 92/100 | 30 exports H.264/AAC antes do novo gate; replay real do gate identificou 13 candidatos para revisão |
| Amostra renal de 15 minutos | 15m00s | 222 segmentos da transcrição local correspondente | 3 exports H.264/AAC no smoke test pós-gate |

A transcrição renal cobriu até 5.720,72s de uma fonte de 5.905,07s. O validador registrou três sobreposições de timestamp e marcou a semântica como não verificada. O início confirma que o arquivo é, de fato, o “Último Análises de Renais”, com retrospectiva da live diária, origem de teses e passagem para a candidatura presidencial. A análise audiovisual automática devolvida para esse arquivo foi genérica e não foi usada como evidência de conteúdo.

A inspeção visual dos seis melhores exports confirmou um estúdio/podcast estável, Renan em plano de câmera utilizável, faixa gráfica inferior, QR code no canto superior direito e um candidato em composição de tela compartilhada que deve ser preservado em 16:9 e não tratado automaticamente como 9:16.

## Antes e depois observável

No lote renal completo anterior ao gate, foram renderizados 30 candidatos. O replay determinístico do mesmo conjunto de candidatos reais sob a regra 1.5 classificou 17 como renderizáveis e 13 como adiados:

| Motivo do adiamento | Quantidade |
|---|---:|
| Pergunta detectada sem ponte pergunta–resposta validada | 10 |
| Alegação sensível sem contexto/evidência explícitos | 2 |
| Ambos os motivos | 1 |

A amostra renal de 15 minutos executada após o carregamento da versão com o gate concluiu com três exports, todos validados por FFprobe como vídeo H.264, áudio AAC e resolução 1920×1080. Esse smoke test confirma que o gate não bloqueia o pipeline inteiro; ele ainda precisa de um benchmark pareado v1.4/v1.5 sobre exatamente o mesmo conjunto de candidatos para uma taxa comparável de redução.

## Diagnóstico editorial

O pipeline atual recuperou contexto e payoff em todos os 30 candidatos renais registrados no projeto 39, mas identificou revisão técnica em 13 deles. Esse resultado é importante: o seletor já não estava apenas premiando frase impactante; ele estava reconhecendo risco editorial, mas a etapa de renderização ainda o ignorava. A 1.5 fecha essa fronteira.

A transcrição base local é estruturalmente utilizável para seleção, mas apresenta erros semânticos claros em nomes próprios, termos políticos e palavras de fala espontânea. Por isso, os clips não devem ser publicados automaticamente com headline baseada somente no ASR. O próximo ciclo deve medir confiança lexical e revisar nomes/entidades antes de gerar headline definitiva.

O Estúdio de Texto de Arte permaneceu sem alterações, conforme a prioridade definida pelo usuário.

## Validação técnica

- Suíte completa: **293 testes aprovados** após o gate e a transcrição por áudio.
- Regressões focadas do gate, runtime, ingestão e transcrição: **31 testes aprovados** na última execução.
- `py_compile app.py modules/*.py`: aprovado.
- `node --check static/js/app.js`: aprovado.
- `git diff --check`: aprovado antes do fechamento desta documentação.
- Smoke real de URL: job criado, modo áudio confirmado, falha anti-bot persistida, sem cortes e sem credenciais.
- FFprobe: exports da coletiva, do lote renal completo e do lote renal de 15 minutos com vídeo H.264, áudio AAC e 1920×1080.

## Limitações e itens não verificados

A transcrição externa do vídeo renal não foi concluída por indisponibilidade da conta do serviço; a transcrição usada para seleção foi feita localmente com faster-whisper base. A análise audiovisual multimodal do vídeo renal devolveu um texto genérico, portanto não comprova timestamps nem teses específicas. Não foi feita ainda uma comparação audiovisual humana de todos os 30 clips renais, nem existe ground truth de aprovação fornecido pelo usuário para esse lote.

A URL pública do YouTube continua sujeita a anti-bot nesta sessão. A função por URL está implementada e testada, mas a aquisição real só será concluída quando a fonte aceitar o downloader ou quando o usuário fornecer o MP4 autorizado.

## Próxima hipótese única

> Antes de gerar headlines, detectar e marcar erros semânticos de ASR em nomes próprios, entidades políticas e termos raros; impedir headline definitiva quando o texto tiver baixa confiabilidade lexical, preservando o clip para revisão humana e comparando a transcrição local com uma fonte corrigida quando disponível.

Essa hipótese não deve ser misturada ao Estúdio de Texto de Arte, a novos pesos de ranking ou a mudanças de layout. O próximo ciclo deve usar os candidatos renais e da coletiva já produzidos, criar fixtures com nomes/termos reais do Renan/MBL, medir falsos positivos e só então ajustar o pipeline.
