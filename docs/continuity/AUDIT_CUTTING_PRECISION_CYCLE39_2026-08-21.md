# Auditoria do núcleo de cortes — ciclo 39

**Data:** 2026-08-21
**Escopo:** precisão temporal, contexto, payoff, locutor, ranking, formatos e uso do Campaign Hub.
**Estado de partida:** release 6.22 publicada na branch de trabalho.

## Diagnóstico resumido

O Furia já deixou de ser um cortador genérico simples. Ele possui uma camada de perfil político Renan/MBL, identidade persistente de faixa, proveniência de transcrição, contrato narrativo, gates de locutor, guidance Chub, benchmark temporal, observabilidade e formatos editoriais. O que ainda falta não é uma única função mágica: é separar melhor **recall de localização**, **qualidade narrativa**, **segurança/identidade**, **adequação de formato** e **aprendizado de decisão humana**.

O maior risco atual é o ranking parecer inteligente porque produz uma pontuação detalhada, enquanto algumas decisões importantes ainda são feitas por heurísticas lexicais, por uma janela de sentença e por um único score final. O caminho mais promissor é aumentar a cobertura na primeira passada, refinar as bordas e o contexto na segunda, e só então ordenar candidatos que já passaram por uma elegibilidade mínima.

## O que já existe

| Área | Estado confirmado | Limite atual |
| --- | --- | --- |
| Fonte e faixa | Identidade de fonte, faixa, assinatura e digest de transcrição | Ainda falta benchmark amplo por família de fonte e transcript |
| Transcrição | Importada/manual, faster-whisper, cobertura, proveniência e contrato | Falta refinamento opcional por palavra/pausa e correção assistida com confirmação |
| Candidatos | NLP, LLM opcional, guidance Chub, fallback, diversidade e remoção de não-conteúdo | Recall ainda depende de seeds e heurísticas; não há rede de janelas multimodal completa |
| Contexto | Setup, anáfora, pergunta, tese, evidência, payoff, contexto completo | Muitas flags ainda dependem de texto e de janela de sentença; pergunta retórica e pergunta-resposta podem ser confundidas |
| Bordas | Reparos por frase, turno, pausa, contexto e agora `text_anchor` Chub | Falta timestamp por palavra e uma política explícita de abertura/fechamento por tipo de payoff |
| Locutor | Turnos, confiança, diarização, evidência Chub e gate Renan-first | `speaker_turn`, identidade, presença e menção ainda precisam de uma camada de fusão e calibração por fonte |
| Ranking | Score explicável com hook, flow, value, contexto, duração, Chub, Instagram e feedback limitado | Um score agrega dimensões diferentes; eligibility e ordering ainda não são superfícies totalmente separadas |
| Chub | Snapshot local, guidance, benchmark, alinhamento textual e evidência limitada | Não há sincronizador remoto portátil nem outcomes humanos suficientes para aprender preferência |
| Formatos | 9:16, 1:1, fake tweet, layout planner e preservação de composição | Falta validação visual automatizada e revisão rápida por formato com comparação de versões |
| Feedback | Store local de decisões, headlines e bundles | Ainda falta transformar rejeições em conjunto de hard negatives e pairwise ranking |
| Diagnóstico | Job events, breadcrumbs e diagnóstico copiável 6.21 | Execução real pela interface ainda precisa ser auditada pelo usuário |

## Lacunas de maior impacto editorial

A primeira lacuna é **recall de localização**. Um candidato pode ser muito bom se encontrado, mas o motor ainda precisa procurar mais amplamente em regiões de fala contínua, mudanças de assunto, perguntas, reações, entidades, energia, cenas e seeds Chub antes de descartar. A segunda é **precisão de borda**: a menor janela suficiente depende de palavra, pausa, turn, pergunta, tese e payoff, não apenas de linhas de legenda.

A terceira é **estrutura narrativa**. O contrato atual já é melhor que uma simples pontuação, mas ainda deve distinguir pergunta retórica, pergunta de entrevista, resposta iniciada fora da janela, conclusão, reação, chamada para ação, revelação e suspensão intencional. A quarta é **identidade do locutor**. Renan falando, Renan aparecendo, Renan sendo citado e Renan sendo assunto precisam continuar separados, com conflitos visíveis em vez de um gate binário que simplesmente elimina recall.

A quinta é **calibração**. O Furia guarda decisões, mas ainda precisa de um benchmark humano versionado com positivos, rejeitados e quase-positivos. Rejeições são mais informativas que apenas likes: começo sem contexto, final sem payoff, terceiro falando, propaganda, duplicata, headline infiel, risco factual, transcrição errada e problema visual devem virar hard negatives reutilizáveis.

A sexta é **validação multimodal seletiva**. Não é eficiente enviar uma live inteira a um modelo visual. O ideal é usar áudio/transcrição/VAD/cenas para recall barato e enviar apenas janelas candidatas comprimidas para confirmação de rosto, documento, tela, crop, texto queimado e coerência audiovisual.

## Decisão preliminar: núcleo genérico + perfil Renan/MBL

A arquitetura deve permanecer **genérica no motor e especializada no perfil**. Um fork totalmente Renan/MBL reduziria a reutilização, dificultaria testes e poderia fazer o programa confundir regras editoriais locais com verdades universais. Um núcleo totalmente genérico, por outro lado, desperdiçaria o valor real do Campaign Hub e dos padrões de publicação do MBL.

A solução efetiva é um núcleo comum com contratos explícitos para `source_family`, `editorial_profile`, `account`, `platform`, `format_profile` e `speaker_policy`. O perfil `renan_santos_politics` deve fornecer vocabulário, famílias editoriais, gates Renan-first, entidades/temas, riscos, priors por conta e padrões de headline, mas não substituir a seleção temporal, a transcrição, o ranking explicável ou a validação visual comuns.

| Componente | Núcleo genérico | Perfil Renan/MBL |
| --- | --- | --- |
| Segmentação | Frases, palavras, pausas, VAD, turnos e cenas | Vocabulário de pauta, nomes, siglas, jargão e blocos Chub |
| Recuperação | Consulta lexical/semântica e sinais multimodais | Seeds Chub, contas, fontes e prioridade Renan |
| Narrativa | Setup, pergunta, tese, evidência, payoff e fechamento | Famílias política, conflito, proposta, mobilização, reação e bastidor |
| Locutor | Turno, identidade, presença e menção | Renan-first, terceiros recorrentes e conflitos Chub/áudio/rosto |
| Ranking | Eligibility, ordering, diversidade e confiança | Priors pequenos por conta/formato/coorte e feedback do editor MBL |
| Formato | Políticas de aspecto e safe area | 9:16, 1:1 Alfinetei e fake tweet com regras editoriais específicas |
| Headline | Grounding, literalidade e entidades | Padrões reais de headline por conta, assunto e formato |

## Melhorias que merecem pesquisa ou implementação

As melhorias que podem ajudar minimamente já no próximo ciclo são: timestamp por palavra/pausa opcional; recuperação em duas passagens; expansão por rede de janelas anteriores e posteriores; classificação de payoff; hard negatives; eligibility separado do ordering; ficha de evidência do candidato; revisão textual pós-render; lint audiovisual; comparação antes/depois; reprocessamento seletivo; fila por motivo de revisão; e relatório de saúde editorial.

As melhorias que exigem benchmark maior antes de alterar o resultado são: pesos Chub mais fortes, modelo pairwise, embeddings semânticos, fusão de voz/rosto/Chub, prior de desempenho por plataforma, aprendizado de duração, detecção automática de headline vencedora e qualquer treinamento baseado somente em Reels publicados.

As melhorias de plataforma — WhatsApp, Telegram, smartwatch, pesquisa recente, dossiês e publicação — são úteis depois, mas não aumentam diretamente a precisão do corte. Não devem consumir o próximo ciclo do motor editorial.

## Regra de execução

A preferência do usuário por muitas melhorias será atendida como um **programa de ciclos**, não como uma alteração não mensurada de centenas de heurísticas. Cada ciclo pode conter uma pequena família coerente de mudanças, mas precisa de uma hipótese principal, regressão, baseline, validação e relatório. A ferramenta pode avançar muito sem o usuário testar imediatamente; porém deve manter honestidade sobre o que foi apenas implementado, o que foi testado em fixture e o que foi comprovado em mídia real.
