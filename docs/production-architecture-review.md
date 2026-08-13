# Avaliação de arquitetura e plano de produção do Furia Clips

## Objetivo correto do produto

O objetivo não é gerar de 30 a 50 cortes a partir de uma única live. O objetivo é processar aproximadamente **oito lives por dia**, cada uma com três a quatro horas, e entregar no fim do ciclo **39 a 50 cortes totais**, extraídos somente quando houver material realmente forte. Esses cortes podem ser políticos, confrontos, propostas, dados, comentários descontraídos, histórias, reações, bastidores ou momentos de humor. O perfil editorial deve orientar a leitura, mas não pode transformar toda fala em conteúdo político artificial.

A regra central deve ser: **qualidade mínima obrigatória antes de qualquer meta de quantidade**. Se oito lives produzirem apenas 31 cortes que realmente tenham contexto, conclusão e potencial, o sistema deve entregar 31 e informar a insuficiência. A faixa de 39–50 é uma meta operacional, não uma licença para preencher a fila com cortes medianos.

## Diagnóstico franco do estágio atual

O projeto já tem uma base acima da média de protótipos: há uma timeline canônica, persistência de jobs, fallback local, validação de mídia, ranking explicável, presets e revisão humana. Isso demonstra uma reconstrução funcional. Entretanto, ele ainda não tem o comportamento de um produto editorial sênior porque a parte mais importante — decidir quais poucos momentos merecem virar corte — continua apoiada em blocos heurísticos, notas de LLM e um ranking local que não conhece o portfólio inteiro do dia.

O problema não é falta de funcionalidades periféricas. O problema é que o sistema ainda não tem um **motor de decisão editorial global**, nem uma camada forte de garantia de contexto, nem um reenquadramento temporal profissional. Hoje ele encontra candidatos; ainda não seleciona de forma suficientemente rigorosa a nata de oito fontes diferentes.

| Área | Situação atual | Por que ainda não parece produto sênior | Prioridade |
| --- | --- | --- | --- |
| Seleção | O seletor trabalha com sentenças e blocos de aproximadamente 40–60 segundos, com limites fixos de candidatos. | Um bloco não representa necessariamente uma unidade de pensamento, uma troca de falante ou o melhor início/fim editorial. | Crítica |
| Ranking | O `EditorialRanker` calcula score explicável e diversidade dentro da seleção recebida. | O score é heurístico, não calibrado por decisões reais do editor e não faz competição global entre oito lives. | Crítica |
| Contexto | Há penalidade para aberturas incompletas e prompts que pedem contexto. | A garantia depende sobretudo de texto; faltam diarização confiável, identificação de pergunta/resposta e expansão automática antes/depois. | Crítica |
| Conclusão | O sistema verifica pontuação de completude e pontuação final do texto. | Ainda não existe um gate duro que descarte conclusões ausentes, respostas interrompidas ou payoff que ocorre depois do fim do clip. | Crítica |
| Viralidade | Há sinais de hook, energia, conflito, valor e especificidade. | Isso é potencial editorial, não previsão estatística de viralidade; falta calibrar o score com aprovados, rejeitados e desempenho posterior. | Alta |
| Enquadramento | Existem presets e face tracking, mas o corte pode usar posição média ou crop estático. | Em debate e split-screen, o rosto relevante pode sair do enquadramento; falta reframe temporal por plano, locutor e composição. | Crítica |
| Produção diária | A fila persistida existe, mas o `JobManager` atual usa um worker e o batch faz principalmente descoberta, hash e manifesto. | O produto não possui campanha diária, orçamento de cortes por live, fila com prioridades, retomada por etapa e seleção global. | Crítica |
| Revisão | Aprovação, rejeição e anotações já existem. | Falta um painel editorial que mostre por que o corte entrou, quais gates passou, alternativas próximas e distribuição por live/tema. | Alta |
| Legendas | O sistema já produz ASS/SRT e destaque político. | Isso é útil, mas não deve consumir o foco principal agora; o editor pode finalizar no CapCut. | Baixa |

## O que significa “contexto excepcional e conclusivo”

Um corte profissional precisa funcionar para alguém que nunca viu a live. O espectador deve entender, sem depender do título, quem está falando, qual é o assunto, qual é a tensão ou pergunta, qual é a tese e qual é a consequência, resposta ou punchline. O algoritmo não deve apenas encontrar uma frase impactante; deve encontrar uma **unidade editorial autossuficiente**.

O início ideal pode incluir alguns segundos de setup antes da frase viral. O meio deve conter o desenvolvimento necessário, mesmo que isso aumente a duração. O fim deve permanecer aberto até o ponto em que a ideia se resolve, a reação acontece, a piada termina ou a consequência é explicitada. Um corte que começa com “isso”, “ele”, “essa situação” ou “como eu falei” sem antecedente deve ser rejeitado ou expandido automaticamente.

O sistema também precisa aceitar que cortes descontraídos podem ser excelentes. Para esses casos, “conclusão” não significa uma tese política: pode ser o desfecho da história, a reação de outra pessoa, a piada, a surpresa ou a resposta que fecha a interação. A taxonomia deve distinguir **política**, **confronto**, **informação**, **história**, **humor**, **reação** e **bastidor**, sem impor o mesmo critério semântico a todos.

## Arquitetura-alvo de nível profissional

### 1. Ingestão e unidade de trabalho

Cada live deve virar uma unidade de análise com `source_id`, duração, data, título, participantes, idioma e metadados. O sistema deve permitir colocar oito arquivos em uma pasta ou arrastá-los de uma vez. A partir daí, deve criar uma campanha diária, calcular hashes, evitar duplicação e manter o estado por etapa: ingestão, transcrição, diarização, análise visual, geração de candidatos, validação, ranking, exportação e revisão.

A fila não deve iniciar oito análises pesadas sem controle. Ela precisa de concorrência configurável, prioridade e retomada. Em uma máquina comum, o padrão mais seguro é analisar uma ou duas lives simultaneamente e deixar transcrição, cenas e ranking em filas separadas. O objetivo é throughput diário, não saturar a máquina e fazer todas as etapas falharem juntas.

### 2. Análise multimodal real

A transcrição precisa conter palavras e timestamps. Sempre que possível, deve haver diarização ou, no mínimo, detecção de turnos de fala. O sistema deve detectar pausas, perguntas, respostas, interrupções, mudança de locutor, risos, aplausos, gritos, variações de energia e cenas. O áudio deve ser analisado como evidência de ritmo e reação, não como substituto do conteúdo.

A análise visual deve registrar cortes de cena, quantidade e posição de rostos, split-screen, layout vertical/horizontal, presença de tela compartilhada, texto na tela e estabilidade do plano. Música não deve ser adicionada automaticamente nesta fase. O produto deve entregar um corte limpo; a música continua sendo uma decisão do editor no CapCut.

### 3. Geração de candidatos por unidade de pensamento

Em vez de pedir ao modelo para escolher blocos arbitrários, o sistema deve construir candidatos a partir de unidades semânticas: pergunta + resposta, afirmação + justificativa, história + desfecho, acusação + evidência, opinião + consequência, setup + punchline ou confronto + reação. Cada candidato deve ser expandido para trás e para frente até passar os gates de contexto e conclusão.

A duração deve ser consequência da unidade editorial. Um corte de 24 segundos pode ser perfeito se fechar uma piada; um de 95 segundos pode ser necessário para concluir uma explicação. O limite de duração serve para impedir abusos, não para cortar raciocínios no meio.

### 4. Gates obrigatórios antes do ranking

Antes de comparar potencial viral, o sistema deve rejeitar candidatos que falhem em qualidade básica. Esses gates não devem ser compensados por um hook forte.

| Gate | Regra de rejeição |
| --- | --- |
| Frase | Começa ou termina no meio de uma frase sem justificativa editorial. |
| Referência | Usa pronome, demonstrativo ou expressão anafórica sem antecedente compreensível. |
| Falante | O locutor principal não pode ser identificado quando isso for importante para o sentido. |
| Pergunta | Mostra uma resposta sem a pergunta ou o contexto mínimo necessário. |
| Conclusão | A tese, história, piada, reação ou consequência não se resolve dentro do intervalo. |
| Áudio | Fala ininteligível, volume muito baixo, clipping severo ou ruído que impede compreensão. |
| Visual | O falante ou elemento central fica cortado, coberto ou fora da área segura. |
| Repetição | É quase igual a outro candidato já aprovado na mesma live ou no mesmo dia. |
| Evidência | Afirma ser dado, denúncia ou número, mas não apresenta a informação mínima que sustenta a categoria. |

Um candidato que falhar em um gate deve ser expandido uma vez. Se continuar falhando, deve ser rejeitado com motivo explícito. Isso é mais importante do que elevar artificialmente a quantidade final.

### 5. Ranking correto e seleção de portfólio

O ranking precisa separar **qualidade mínima**, **potencial editorial** e **diversidade do conjunto**. A nota de um corte não pode ser apenas a soma de hook, fluxo e energia. Uma proposta operacional para a nota final, depois dos gates, é:

| Dimensão | Peso | O que mede |
| --- | ---: | --- |
| Contexto autossuficiente | 25% | O espectador entende situação, participantes e assunto sem assistir à live. |
| Conclusão/payoff | 20% | A ideia termina com resposta, consequência, reação, punchline ou síntese. |
| Força da tese ou história | 15% | Existe algo específico que vale ser dito e lembrado. |
| Hook e tensão | 15% | Os primeiros segundos criam curiosidade, conflito, surpresa ou identificação. |
| Potencial de conversa | 10% | O trecho provoca comentário, compartilhamento, discordância ou identificação. |
| Clareza e áudio | 5% | A fala é compreensível e o ritmo não é prejudicado por ruído ou excesso de filler. |
| Enquadramento e ritmo visual | 5% | O elemento central está visível e as mudanças visuais ajudam a retenção. |
| Novidade/diversidade | 5% | O corte acrescenta algo ao conjunto e não repete outro candidato. |

A nota deve ter também confiança, evidência e motivos de rejeição. A confiança não pode ser calculada apenas pelo tamanho da transcrição; deve cair quando há falha de diarização, áudio ruim, baixa certeza de conclusão ou conflito entre sinais.

Depois do score individual, deve haver uma segunda etapa de **otimização do portfólio diário**. Ela escolhe os melhores 39–50 entre todos os candidatos das oito lives, com limites suaves por fonte, tema e formato. O algoritmo deve impedir que uma única live ocupe a fila inteira e deve preservar uma mistura de política, confronto, dado, história, humor, reação e bastidor quando houver material.

A meta recomendada é um orçamento adaptativo de aproximadamente quatro a oito cortes por live, mas a distribuição deve depender da qualidade. Uma live excepcional pode entregar dez; uma live fraca pode entregar dois; o total só deve chegar a 39–50 quando os gates e a nota mínima permitirem. O sistema deve reportar quantos candidatos foram analisados, quantos foram rejeitados por cada gate e por que cada corte entrou.

### 6. Enquadramento profissional

O reenquadramento deve ser temporal. Um único `avg_x` por clip é insuficiente para debates, reações e mudanças de locutor. O sistema deve identificar planos, rostos e locutor dominante por janela, calcular uma trajetória de crop e aplicar suavização para evitar saltos. Em split-screen, deve escolher entre preservar o quadro, focar o interlocutor ou alternar em pontos de mudança, sem cortar olhos, boca ou texto relevante.

Cada export precisa passar por uma checagem automática de área segura, detecção de rosto parcialmente cortado e estabilidade do crop. Se a confiança visual for baixa, o sistema deve preservar o enquadramento original e sinalizar “revisão de enquadramento”, em vez de produzir um vertical aparentemente pronto mas mal composto.

### 7. Revisão mínima do editor

A revisão deve ser rápida, não uma segunda edição completa. Cada cartão precisa mostrar o vídeo de origem, trecho com alguns segundos de margem, score, confiança, tipo editorial, live de origem, motivo de entrada, gates aprovados, alternativas próximas e uma opção de rejeição com motivo. O editor deve conseguir aprovar, rejeitar, trocar o início/fim com handles e mandar o corte para uma fila “precisa de reenquadramento”.

O trabalho posterior no CapCut deve ficar restrito a legenda final, música, identidade visual e pequenos ajustes. Se a revisão ainda exigir procurar contexto, recompor o começo ou salvar um corte que terminou antes do payoff, o problema está no pipeline e deve virar dado de calibração.

## Ordem de implementação recomendada

A primeira entrega profissional não deve começar por mais cores, presets ou integração de música. Deve começar pela qualidade da unidade editorial e pela seleção global.

| Fase | Entrega | Critério de conclusão |
| --- | --- | --- |
| 1 | Campanha diária para oito lives e fila por etapas | O usuário adiciona oito arquivos, acompanha cada etapa e retoma após falha sem repetir processamento concluído. |
| 2 | Candidatos por turnos e unidades de pensamento | Pergunta/resposta, história/desfecho e tese/consequência são preservados como unidades, sem depender apenas de blocos de 40–60 s. |
| 3 | Gates de contexto, conclusão, áudio e visual | Candidatos incompletos são rejeitados ou expandidos automaticamente antes da nota viral. |
| 4 | Ranking global e orçamento diário | O sistema combina oito lives, deduplica candidatos e entrega apenas os melhores 39–50 que passarem da nota mínima. |
| 5 | Reframe temporal e QA visual | O crop acompanha locutor/rosto por janela e sinaliza baixa confiança em vez de inventar enquadramento. |
| 6 | Aprendizado com revisão | Aprovações, rejeições e correções de início/fim alteram a calibração por perfil e por tipo editorial. |

## Critérios de aceite do produto profissional

A versão pode ser considerada pronta para a rotina quando, em um conjunto real de oito lives, produzir uma lista global ranqueada sem duplicatas, com origem e explicação de cada corte. Todo corte aprovado deve ser compreensível sem a live completa, terminar o raciocínio ou payoff, possuir áudio inteligível e ter enquadramento verificável. A quantidade deve ficar na faixa de 39–50 somente quando houver material suficiente; a aplicação deve ser capaz de retornar menos e justificar.

A métrica mais importante não é “quantos candidatos foram gerados”. É a **taxa de aprovação na primeira revisão**. Outras métricas úteis são taxa de rejeição por contexto, taxa de ajuste manual de início/fim, percentual de cortes com enquadramento corrigido, distribuição de cortes por live e correlação posterior entre score e desempenho real. O score deve ser recalibrado com o histórico do editor, não tratado como verdade absoluta.

## Conclusão

Na minha avaliação, o Furia Clips já deixou de ser um protótipo vazio, mas ainda está entre uma ferramenta funcional e um produto editorial profissional. O salto decisivo será trocar “gerar candidatos bons” por “provar que cada corte selecionado merece ocupar uma das 39–50 vagas do dia”. Isso exige gates duros, unidades de pensamento, seleção global entre lives, enquadramento temporal e aprendizado com as suas decisões.

A legenda pode ficar em segundo plano por enquanto. A prioridade correta é: **contexto, conclusão, seleção global, enquadramento, throughput e calibração com revisão humana**. Com essa ordem, a ferramenta passa a atuar como um assistente editorial de produção, e não apenas como um cortador automático.
