# Perfil editorial político — Renan Santos/MBL

## Objetivo

O perfil `renan_santos_politics` adapta o Furia Clips para selecionar cortes políticos autossuficientes, claros e editáveis para Shorts, Reels e TikTok. Ele foi inspirado nos padrões públicos observáveis dos perfis de referência e deve ser calibrado com os exports reais do editor, sem copiar conteúdo, identidade visual proprietária ou alegações dos perfis.

## Tipos de corte

| Tipo | O que procurar | O que torna o corte útil |
| --- | --- | --- |
| Confronto/reação | Crítica, resposta, indignação, oposição ou quebra de expectativa | O espectador entende quem é o alvo, qual é o conflito e qual posição foi defendida |
| Proposta/programa | Medida, plano, promessa, meta ou solução | A proposta aparece com problema, mecanismo e consequência; números e prazos ajudam |
| Dado/denúncia | Pesquisa, número, documento, lei, histórico ou acusação contextualizada | A evidência é apresentada com fonte ou contexto suficiente; não se transforma opinião em fato |
| Discurso/posicionamento | Tese política, princípio, defesa ou crítica de governo | O argumento tem começo, desenvolvimento e conclusão, sem depender da live original |
| Mobilização | Convite para seguir, compartilhar, participar ou apoiar | A chamada ocorre depois de uma ideia compreensível, não substitui a substância do corte |

## Fatores mensurados

O ranqueador calcula aderência ao tema político, força da tese, conflito ou consequência, força de proposta, densidade de evidências, mobilização, especificidade, conclusão, correspondência com o pedido do usuário, completude de contexto e aderência ao perfil do canal. Quando o pipeline fornece mudanças de cena, também expõe `visual_change_density`, um sinal de ritmo visual opcional. Energia de áudio continua sendo um fator explicável, mas não é confundida com a presença de música.

O sistema favorece cortes que tenham um gancho nos primeiros segundos, apresentem o assunto e os participantes, desenvolvam uma ideia concreta e terminem com resposta, consequência ou frase final. Penaliza aberturas no meio da frase, pronomes sem antecedente, texto genérico, baixa densidade de informação, encerramento sem conclusão e duplicidade temporal ou textual. A abertura “isso”, “ele”, “ela” ou equivalente pode receber penalidade de contexto quando o antecedente não está no próprio trecho.

O preset `political_shorts` usa legendas palavra a palavra com destaque amarelo e uma camada de alerta vermelha para palavras políticas de impacto e números presentes na transcrição. Sua política de áudio é `voice_and_ambience`: a ferramenta preserva voz e ambiente e não adiciona uma trilha musical genérica automaticamente. Isso permite ao editor escolher música apenas quando houver licença, intenção e necessidade editorial comprovadas.

## Prompt editorial para IA

A aplicação envia aos backends de IA a seguinte orientação conceitual: selecionar cortes políticos com tese ou conflito identificável, desenvolvimento com posicionamento, proposta, dado ou denúncia e conclusão clara; classificar o formato do corte; incluir o setup necessário; não inventar fatos; não transformar opinião em fato; não atribuir falas sem evidência; e preferir cortes autossuficientes com especificidade, energia e uma frase final forte.

## Evidência audiovisual e limites da calibração

A matriz de padrões em [`video-analysis/editorial-patterns.md`](video-analysis/editorial-patterns.md) registra uma análise audiovisual concluída e uma amostra pública de títulos, visualizações e copies. Ela não representa uma análise completa de todas as publicações dos dois perfis e não tem acesso a métricas privadas de retenção. Visualizações públicas servem apenas como proxy descritivo; não são uma promessa de viralidade.

## Limites

O perfil não verifica a veracidade de afirmações políticas e não deve ser usado como fact-checker. O score é potencial editorial explicável, não previsão de viralidade. A avaliação de qualidade exige um conjunto de vídeos reais, marcação de clips aprovados/rejeitados e acompanhamento de retenção, conclusão e compartilhamento.
