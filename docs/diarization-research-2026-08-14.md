# Pesquisa aplicada — diarização local para o Furia Clips

## Conclusão executiva

A diarização deve entrar no Furia Clips como **módulo opcional e conservador**, não como requisito do fluxo principal. A combinação WhisperX + pyannote pode fornecer timestamps por palavra e rótulos de locutor, mas exige dependências pesadas, modelos externos e, em vários cenários, token de acesso do Hugging Face. O sistema deve continuar funcionando sem essa camada, marcar confiança baixa e preservar a proporção original quando a identificação do locutor ou do active speaker for incerta.

## Evidências técnicas

| Fonte | Evidência relevante | Decisão de produto |
| --- | --- | --- |
| [pyannote.audio](https://github.com/pyannote/pyannote-audio) | Toolkit Python open source baseado em PyTorch para diarização; a pipeline `community-1` é executada localmente, requer FFmpeg, instalação do pacote, aceite das condições do modelo e token do Hugging Face. | Oferecer integração opcional; não tornar o primeiro uso dependente de token externo. |
| [WhisperX](https://github.com/m-bain/whisperX) | Combina ASR batelado, timestamps por palavra via alinhamento, VAD e diarização com pyannote; recomenda `int8`/CPU quando não há GPU e declara que sobreposição de fala e diarização ainda não são perfeitas. | Usar para revisão de pergunta–resposta e marcação de locutor, nunca como verdade absoluta ou requisito de corte. |
| [Modelo pyannote no Hugging Face](https://huggingface.co/pyannote/speaker-diarization) | Acesso ao modelo envolve aceitar condições e compartilhar contato; suporta limites de número de speakers e execução em arquivo ou trecho. | Solicitar configuração somente quando o usuário optar pela função; registrar dependência e fallback. |

## Arquitetura recomendada

A rota segura é: extrair áudio mono temporário; executar diarização somente se o usuário habilitar; alinhar os segmentos de transcript aos intervalos de locutor; calcular confiança; anexar `speaker_id`, `speaker_overlap`, `speaker_confidence` e `diarization_source`; e deixar o ranqueador usar esses sinais como penalidade/explicação, não como filtro absoluto.

Em entrevistas, um candidato deve receber prioridade quando contém pergunta e resposta, mas deve ser penalizado quando há sobreposição de vozes ou quando o active speaker não é identificável. O reframe facial só deve ser aplicado se a face correspondente ao locutor tiver confiança suficiente. Sem confiança, a saída correta continua sendo a proporção original e o aviso “revisar locutor/enquadramento”.

## Plano de implementação incremental

| Etapa | Escopo | Critério de aceite |
| --- | --- | --- |
| 1 | Esquema neutro de locutores no transcript | Segmentos aceitam `speaker`, `speaker_confidence` e `overlap_suspected` sem quebrar transcrições antigas. |
| 2 | Detector local opcional | Ausência de pyannote/WhisperX não interrompe o processamento; o usuário recebe uma explicação visual. |
| 3 | Integração com ranking | Sobreposição e speaker desconhecido influenciam `clarity`/`context_match` apenas com confiança mensurável. |
| 4 | Reframe seguro | Nenhum crop agressivo em múltiplos locutores ou split-screen. |
| 5 | Benchmark do canal | Comparar aprovação editorial de entrevistas com e sem diarização usando feedback persistente. |

## Limitações que devem permanecer explícitas

A diarização não identifica automaticamente o nome real de cada pessoa; ela normalmente produz rótulos de locutor. Sobreposição de fala é um caso difícil. Timestamps por palavra melhoram a precisão de cortes, mas podem falhar em palavras sem representação no modelo de alinhamento. Em notebooks sem GPU, o custo de CPU e memória precisa ser medido antes de ativar o recurso por padrão.

## Referências

[1]: https://github.com/pyannote/pyannote-audio "pyannote.audio — toolkit oficial no GitHub"
[2]: https://github.com/m-bain/whisperX "WhisperX — repositório oficial no GitHub"
[3]: https://huggingface.co/pyannote/speaker-diarization "pyannote speaker-diarization — model card"
