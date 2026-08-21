# Auditoria do motor de cortes e da integração Chub/MBL — 2026-08-21

## Estado real do motor

O `ClipSelector` possui três caminhos de seleção: Gemini quando há chave configurada, Ollama local quando disponível e NLP local como fallback. Nenhum caminho depende obrigatoriamente de API externa. Todos passam por uma sequência comum de reparos e gates depois da geração inicial.

A transcrição é dividida em frases, segmentos longos podem ser repartidos por pontuação, e blocos de entrevista tentam usar turnos do entrevistador como seams. O seletor já busca a menor janela que contenha contexto e payoff, tenta fechar perguntas com o começo da resposta, alinha bordas de entrevistas, reabre trechos que começam no meio da fala, remove irmãos que apenas encostam, descarta regiões sem conteúdo, anexa contexto temático local e reduz sobreposição.

O contrato editorial existente reconhece começo no meio da frase, referência anafórica, pergunta, pergunta que exige resposta, resposta suficiente, evidência textual, payoff, troca de locutor, identidade do locutor, timestamps ambíguos e sobreposição. O ranking registra fatores, versão do score, confiança, explicação, flags técnicas e proveniência.

## Papel atual do Campaign Hub

O Campaign Hub é carregado por snapshot local autorizado, sem chamada MCP no job normal. O adaptador preserva contas separadas para `@renansantosmbl`, `@renansantosreserva` e `@partidomissao`, além de fontes, transcrições, frases, blocos, highlights, possíveis cortes, posts, métricas, entidades, tópicos e benchmarks quando o snapshot contém essas coleções.

A integração atual converte highlights e possíveis cortes em seeds temporais. Prioriza highlights, carrega `renan_speaking`, `speaker_gate`, `needs_context`, riscos, `density_rank`, `self_contained_rank`, confiança, `trust_tier`, versões de labeler/prompt e proveniência. A identidade temporal pode ser rebaseada para um MP4 de bloco quando a duração local confirma a correspondência.

Seeds Chub são propostas guiadas, não aprovação. No modo Renan-first, somente `renan_speaking=true` entra no pool guiado publicável; itens false/desconhecidos permanecem como descoberta para auditoria. Candidatos locais também podem herdar evidência temporal de blocos Chub, mas essa evidência não aumenta automaticamente o score nem limpa todos os gates.

O ranqueador usa Campaign Hub principalmente como prior de hook e evidência de bloco, com influência deliberadamente pequena. O prior exige pelo menos três observações do hook, é comparado com baseline da conta e fica limitado aproximadamente à faixa 42–58. A evidência de bloco também é limitada. Isso evita contaminar o ranking, mas explica por que o Chub ainda não produz sozinho uma especialização forte.

## Medição mais importante disponível

Na fonte real `3XJfcqn56Rw`, com aproximadamente 5.905 segundos, 1.951 frases, 27 blocos e 66 highlights do Acervo, o relatório do ciclo 32 registrou:

| Condição | Recall IoU 0,10 | Recall IoU 0,25 |
| --- | ---: | ---: |
| Genérico sem Chub | 5/66 — 7,58% | 0/66 |
| Genérico com Chub | 18/66 — 27,27% | 6/66 — 9,09% |
| Renan-first sem Chub | 7/66 — 10,61% | 1/66 — 1,52% |
| Renan-first com Chub | 7/66 — 10,61% | 1/66 — 1,52% |

No modo Renan-first, o Chub encontrou 30 propostas, promoveu 6 e filtrou 24 por falta de `renanSpeaking=true`. A separação de descoberta e publicação foi confirmada, mas não houve ganho de recall publicável. Isso significa que o próximo plano precisa atacar **recall de sementes e alinhamento local**, não simplesmente aumentar pesos do Chub.

## Lacunas prioritárias

1. O benchmark de 66 highlights mede sobreposição com unidades do Acervo, mas não mede sozinho autossuficiência, payoff, locutor correto, fidelidade da headline ou preferência humana.
2. A integração preserva muitas coleções no snapshot, porém o caminho atual usa principalmente seeds, blocos e priors; transcrições, exemplos aprovados, métricas por formato e feedback ainda não formam um modelo editorial suficientemente rico.
3. `renan_speaking=true` é evidência do Acervo, não diarização independente. O Furia precisa medir falsos positivos e falsos negativos de locutor em amostra validada.
4. O `context_complete` local é forte como gate de segurança, mas ainda é heurístico: pontuação, pontuação final, marcadores lexicais, número de palavras e flags podem errar em fala espontânea, legendas sem pontuação e frases irônicas.
5. A divisão de blocos de entrevista depende de detectar turnos do entrevistador; lives, discursos, debates com interrupção e vários convidados precisam de famílias de segmentação diferentes.
6. O fallback NLP tem recall e precisão diferentes do Gemini/Ollama, mas ainda é difícil comparar os caminhos de forma controlada, porque a seleção inicial e os reparos posteriores interagem.
7. A qualidade final ainda depende de benchmark audiovisual real, incluindo início/fim percebidos, áudio, rosto, tela, documento, legenda e headline.
8. A deduplicação atual trabalha com intervalos e fingerprints de uma fonte; a identidade persistente de intervalo continua sendo necessária para reprocessar faixas diferentes sem colisão.

## Consequência para o próximo planejamento

A próxima etapa não deve começar por WhatsApp, smartwatch ou dossiês. Deve criar um benchmark editorial versionado, separar recall de qualidade, ampliar a memória útil do Chub, melhorar alinhamento de seeds com a transcrição local, validar locutor e contexto com amostras humanas e só então ajustar geração/ranking. Cada ciclo deve alterar uma hipótese principal e publicar apenas se o before/after for mensurável.
