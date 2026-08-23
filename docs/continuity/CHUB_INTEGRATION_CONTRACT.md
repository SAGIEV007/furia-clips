# Contrato de integração Campaign Hub–Furia Clips

> Este documento define o norte funcional principal do Furia Clips. A visualização em blocos é uma superfície de diagnóstico e revisão; o produto só cumpre sua missão quando o contexto do Campaign Hub melhora de forma verificável a seleção e a montagem dos cortes.

## 1. Objetivo principal

O Furia Clips é um programa de cortes focado no universo **Renan Santos/MBL**. Sua finalidade é transformar vídeos longos, entrevistas, lives, eventos e arquivos MP4 em cortes **precisos, completos, autossuficientes, contextualizados e editorialmente úteis**.

O Campaign Hub deve ser usado para aumentar a qualidade dessa decisão. O Furia não deve apenas mostrar blocos, exportar intervalos conhecidos ou exibir que uma memória existe. Ele deve aproveitar, de forma auditável, os dados autorizados do Campaign Hub para encontrar o contexto certo, propor a janela correta, preservar a identidade do locutor e evitar cortes que começam ou terminam sem sentido.

A métrica de sucesso não é “a sessão de blocos aparece”. A métrica é: **o corte guiado pelo contexto do Campaign Hub é melhor do que o candidato local sem esse contexto, em recall temporal, completude, autossuficiência, locutor, payoff, risco e qualidade audiovisual**.

## 2. Estado real no início deste contrato

A release 2.2 tornou o caso b354 mensurável, mas o benchmark cobriu `0/3` highlights QA-gated do Campaign Hub, com IoU médio `0.0`. O mapeamento temporal e a exportação individual funcionaram; a geração local de candidatos não alcançou as unidades de referência.

O código atual possui três camadas diferentes, que não devem ser confundidas:

| Camada | Estado real | Consequência |
| --- | --- | --- |
| Memória local | Importa snapshots autorizados de blocos, highlights, riscos, proveniência e métricas. | Permite trabalho offline, mas não garante que o conteúdo seja usado no corte. |
| Sessão de blocos | Lista, filtra, seleciona e exporta intervalos ou highlights já conhecidos. | É útil para inspeção e fallback, mas não é ainda o motor de cortes guiados. |
| Ranking local | Usa prior de desempenho e evidência de bloco como ajustes pequenos e explicáveis. | O Campaign Hub atualmente influencia pouco o resultado e não cria propostas de janela. |

A leitura correta é, portanto: **há uma fundação de integração, mas ainda não há uma ponte funcional completa entre dados do Campaign Hub, geração de candidatos, gates de contexto e renderização**.

## 3. Fluxo-alvo obrigatório

A integração deve evoluir para o seguinte fluxo:

```text
fonte local ou URL pública
        ↓
identidade da fonte e timeline canônica
        ↓
contexto autorizado do Campaign Hub
(blocos, highlights, pauta, transcrição, riscos, locutor e proveniência)
        ↓
alinhamento Chub ↔ fonte local
(YouTube ID, timestamps, texto e manifesto)
        ↓
seeds editoriais de contexto
(pergunta-gatilho, tese, highlight, entidade, risco, payoff)
        ↓
expansão para a menor janela completa
(frase, antecedente, pergunta–resposta, tese, evidência e encerramento)
        ↓
gates de locutor, contexto, timing, transcrição, mídia e risco
        ↓
propostas guiadas separadas de cortes aprovados
        ↓
revisão, renderização original e validação audiovisual
        ↓
benchmark antes/depois e feedback persistido
```

O job normal deve continuar funcionando com a última memória local válida e não pode depender de uma chamada MCP a cada corte. A atualização do contexto pode ser feita pelo agente, por uma ação administrativa explícita ou por um exportador incremental autorizado. O uso offline-first é uma restrição de operação e armazenamento, não uma justificativa para ignorar o contexto Chub durante a seleção.

## 4. Dados que devem influenciar a proposta

O contexto do Campaign Hub deve ser normalizado em um pacote de proposta com proveniência e confiança. Quando disponíveis, devem ser preservados:

| Campo | Uso no Furia |
| --- | --- |
| `source`, `videoId`, plataforma, conta e URL pública | Confirmar que o snapshot corresponde ao vídeo local e manter proveniência separada. |
| `start`, `end`, duração e timeline da unidade | Criar a seed temporal e mapear o intervalo para a fonte local. |
| `title`, `summary`, `topicTags`, entidades e pauta | Procurar o mesmo tema na transcrição local e evitar cortes semanticamente genéricos. |
| `triggerQuestion` e frases de abertura | Recuperar a pergunta ou o antecedente que torna a resposta autossuficiente. |
| `highlights` e textos dos destaques | Criar seeds de tese/payoff, não copiar automaticamente o intervalo como corte final. |
| `renanSpeaking`, locutor, turnos e confiança | Priorizar fala real de Renan e impedir atribuição indevida a Kim, entrevistador ou outro convidado. |
| `riskFlags`, `gateWarnings`, `audioCheckRanges` e qualidade de transcrição | Rejeitar, expandir ou marcar para conferência trechos frágeis. |
| `selfContainedRank`, `densityRank` e razões editoriais | Priorizar contexto e densidade depois que os gates básicos passarem. |
| desempenho por conta/plataforma/crosspost | Calibrar padrões históricos; nunca somar contas ou transformar popularidade em aprovação. |

Legenda automática e `speakerChange` são evidências auxiliares. Não são citação nem identidade confirmada. O áudio e a fonte audiovisual continuam necessários para nomes, números, acusações, locutor e claims de risco.

## 5. Regras de decisão

O Campaign Hub é um **motor de contexto e calibração**, não um aprovador automático. Um bloco QA-gated é uma referência forte para comparação e uma seed para proposta, mas pode estar incompleto, baseado em ASR automático ou conter erro. O Furia deve conservar a proveniência, indicar o grau de confiança e permitir revisão.

A influência do Campaign Hub não deve permanecer limitada a um `+/-2` no score quando o objetivo for gerar uma proposta guiada. O prior de performance pode continuar limitado no ranking legado, mas a integração principal deve ocorrer antes do score, por meio de contexto, seeds, alinhamento, expansão e gates. Um candidato sem contexto suficiente não pode vencer apenas porque tem hook ou energia.

Quando o foco for Renan-first, `renanSpeaking=true` ou uma evidência audiovisual equivalente deve ser tratado como requisito para classificar o corte como fala de Renan. `renanSpeaking=false` deve preservar a fala de terceiro. “Sobre Renan”, “Renan aparece”, “Renan é mencionado” e “Renan fala” são estados distintos.

Pergunta e resposta devem ser tratadas como estrutura. Se a resposta depende da pergunta, o Furia deve expandir a janela para incluí-la. A janela final deve terminar depois de tese, evidência ou payoff; não basta cobrir uma frase que contém uma palavra forte.

Propostas guiadas pelo Campaign Hub devem permanecer separadas de cortes aprovados, publicados ou aceitos pelo editor. O usuário deve conseguir ver a origem da proposta, a razão da expansão, os gates aprovados, as flags pendentes e a comparação com o candidato local.

## 6. Operações de leitura do Campaign Hub

As operações autorizadas devem ser usadas conforme a finalidade, sem depender de uma única consulta:

| Operação | Papel |
| --- | --- |
| `chub_acervo_blocks` | Recuperar unidades QA-gated, intervalos, resumo, pergunta-gatilho, riscos, highlights e proveniência para criar seeds. |
| `chub_acervo_transcript` | Recuperar frases timestampadas e regiões não-bloco para expandir a seed e preservar o antecedente. |
| `chub_acervo_pauta` | Recuperar pauta, entidades, temas e estrutura quando a unidade estiver disponível. |
| `chub_acervo_stats` | Entender cobertura, saúde e versão dos dados antes de interpretar ausência como zero. |
| `chub_cohort_stats`, `chub_top_posts` e `chub_tag_performance` | Calibrar padrões editoriais por conta e plataforma, sem misturar proveniência nem substituir evidência do vídeo. |

Uma consulta externa deve produzir snapshot ou evidência registrada. Não guardar tokens, cookies, dados privados, mídia grande ou URLs privadas no Git. O snapshot local deve ser sanitizado, versionado, paginado, hasheado e vinculado à fonte.

## 7. Critérios de aceitação da integração

Uma rodada só pode ser considerada avanço funcional quando demonstrar, em mídia real ou benchmark reproduzível:

| Critério | Evidência mínima |
| --- | --- |
| Cobertura | O recall de highlights ou seeds Chub melhora em relação ao baseline local. |
| Alinhamento | IoU, erro de início/fim e mapeamento para a timeline local são registrados. |
| Contexto | A proposta inclui antecedente, pergunta quando necessária, tese/desenvolvimento e payoff. |
| Locutor | A identidade não é inferida apenas por `speakerChange`; casos de terceiros continuam preservados. |
| Autossuficiência | Um revisor entende o trecho sem assistir à fonte inteira. |
| Risco | `riskFlags`, `gateWarnings` e intervalos de conferência aparecem no resultado. |
| Reprodutibilidade | O mesmo lote reprocessado mantém ou explica variações de candidatos. |
| Renderização | O intervalo aprovado é renderizado no aspecto original e validado com FFprobe e inspeção audiovisual. |
| Proveniência | Conta, plataforma, fonte, versão do snapshot e origem de cada seed permanecem visíveis. |

Não chamar a integração de pronta porque a memória foi importada, a sessão de blocos carregou ou um endpoint respondeu `200`.

## 8. Próxima hipótese funcional

> Se o Furia importar um lote autorizado de unidades do Campaign Hub, transformar cada highlight/bloco em seed semântica e temporal, alinhar a seed à transcrição local e expandi-la até a menor janela completa que passe pelos gates de contexto e locutor, então o recall do benchmark b354 deve sair de `0/3` sem aumentar falsos positivos, atribuições erradas ou cortes truncados.

Essa hipótese deve ser testada antes de investir em reframe, headlines, editor estilo CapCut, publicação automática, música, voz, avatares, múltiplas câmeras ou download remoto por range.

## 9. Evidência consultada

A transcrição autorizada do vídeo `gVrW6a5e6Tc` retornou 90 frases entre `279.96s` e `578.16s`. A fonte é legenda automática do YouTube, com `qualityTier=automatic`, e o próprio Acervo informa que exige conferência de áudio. O retorno também alerta que `turn` e `speakerChange` indicam mudanças detectadas na legenda, não identidades. Esse caso deve ser usado para validar expansão de pergunta, resposta, locutor e risco sem tratar a legenda como citação.

O registro operacional dessa consulta está em `/home/ubuntu/chub_video_context_2026-08-17.md` no ambiente de trabalho; o conteúdo sanitizado e relevante deve ser promovido a relatório de ciclo ou snapshot do projeto quando for usado como evidência de implementação.
