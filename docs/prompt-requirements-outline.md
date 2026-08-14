# Estrutura de requisitos do prompt

## 1. Diagnóstico antes do corte

O sistema deve receber uma fonte local ou pública, obter a mídia e gerar uma análise antes de renderizar qualquer clip. A análise deve incluir duração, resolução, proporção original, participantes prováveis, turnos de fala, perguntas, respostas, mudanças de assunto, sobreposições, intensidade e blocos de entrevista.

## 2. Mapa de candidatos auditável

Cada candidato deve ter `start`, `end`, `duration`, `title`, `hook`, `thesis`, `question_text`, `answer_summary`, `conclusion`, `speaker_focus`, `topic`, `evidence`, `risk_flags`, `viral_score`, `quality_score`, `context_score` e `recommended_aspect_ratio`. Candidatos rejeitados também devem poder ser consultados com o motivo da rejeição.

## 3. Decisão de composição

A análise deve decidir entre `original_16_9`, `1:1`, `4:5`, `9:16_single_speaker`, `9:16_split` e `9:16_picture_in_picture`. A decisão deve considerar a plataforma, o foco do trecho, a quantidade de locutores, a troca de câmera, a posição do rosto, a área segura para legendas e o grau de confiança. Em ambiguidade, deve recomendar o original, não um crop central arbitrário.

## 4. Active speaker profissional

Combinar transcrição timestampada, VAD, diarização/sinais de voz quando disponíveis, detecção facial, tracking temporal, cortes de câmera e análise multimodal do Gemini. O sistema deve trocar o enquadramento conforme o locutor muda, usar split/PIP quando necessário e registrar a confiança de cada transição. A revisão por preview deve permitir aceitar, ajustar ou rejeitar o enquadramento.

## 5. Ranking editorial Renan/MBL

Priorizar teses fortes, frases autossuficientes, conflito, clareza, novidade, especificidade, conclusão, potencial de comentário e aderência aos padrões das páginas do Renan. Preservar pergunta quando ela for necessária, mas também encontrar respostas autossuficientes. Separar cortes políticos, descontraídos, bastidores, reação, conversa e humor.

## 6. Benchmark e validação

Pesquisar recursos oficiais de OpusClip, Vizard, Klap e outras ferramentas relevantes, separar marketing de capacidade verificável e converter os melhores padrões em requisitos testáveis. Criar testes com fontes horizontais, entrevistas, split-screen, múltiplos locutores, mudança de câmera e falas sobrepostas. Medir precisão de início/fim, completude Q&A, correção do locutor, estabilidade do crop, proporção, áudio, duração e taxa de rejeição.
