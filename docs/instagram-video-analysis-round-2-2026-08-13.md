# Segunda rodada de análise audiovisual — Renan Santos/MBL

| Campo | Valor |
| --- | --- |
| Data | 13 de agosto de 2026 |
| Corpus principal | 12 Reels locais de `@renansantosmbl`, todos com folhas de contato inspecionadas |
| Corpus reserva | 12 Reels locais de `@renansantosreserva`, com relatórios audiovisuais individuais preservados |
| Objetivo | Transformar padrões visuais e editoriais em critérios mais seguros de seleção e enquadramento |
| Limitação | A paginação pública adicional retornou HTTP 401 e não foi contornada; o documento cobre o corpus local disponível, não todos os posts históricos |

## Resultado da rodada

A análise local confirma que a marca não possui um formato único. O perfil principal alterna monólogo de estúdio, pronunciamento próximo, entrevista externa, podcast, react, colagem documental, palco e institucional. O perfil reserva apresenta forte recorrência de headline fixa, composição 4:5 ou 1:1, split-screen, imagem contextual estática, entrevista/podcast e locutor ativo na área oposta. A decisão correta para o Furia Clips é classificar o layout antes de selecionar o reframe, em vez de aplicar 9:16 por padrão.

| Família | Evidência principal | Regra de seleção | Regra visual |
| --- | --- | --- | --- |
| Monólogo/close | Uma face dominante, tese direta, gesto e headline | Hook + ideia completa + consequência | Reframe 9:16 pode ser seguro com tracking estável |
| Entrevista externa | Dois rostos, pergunta, resposta e reação | Manter pergunta quando necessária e preservar o payoff | Quadro amplo; não cortar o interlocutor secundário |
| Podcast/split-screen | Microfone, múltiplos planos, texto e alternância de faces | Pergunta–resposta ou raciocínio autossuficiente | Manter composição original e áreas gráficas |
| React/documental | Fala âncora, TV, câmera, notícia, card ou arquivo | Claim → evidência → interpretação/conclusão | Tracking pausa durante insert e retorna após validação |
| Palco | Microfone, mãos, plateia, plano aberto/fechado | Tese, mobilização ou transformação | Preservar mãos, microfone e relação com a plateia |
| Institucional/campanha | Cards, dados, assinatura, grupo e mensagem visual | Unidade visual autossuficiente com contexto | Proteger texto, margens e cartelas; não ampliar rosto cegamente |

## Padrões confirmados no perfil principal

Os 12 Reels locais do perfil principal demonstram que o corte forte geralmente alterna uma **face âncora** com uma **camada de prova**. A prova pode ser uma notícia, uma operação policial, câmera de segurança, palco, imagem de arquivo, card ou pessoa entrevistada. O trecho perde força quando termina durante o insert, antes do retorno à interpretação ou sem a frase que explica o card. O ranking deve portanto reconhecer a sequência `tese → evidência → consequência`, além do hook inicial.

A legenda publicada é grande, curta e de alto contraste, muitas vezes amarela, com variações de cor para distinguir fala principal, citação ou fonte. Ela é útil para OCR e proteção de área segura, mas não deve substituir a transcrição nem ser tratada como evidência de viralidade. O áudio natural, reação da plateia e energia da voz contribuem para o ritmo; não há base suficiente para exigir música automática em todos os cortes.

## Padrões confirmados no perfil reserva

Os 12 relatórios locais do perfil reserva reforçam quatro decisões. Primeiro, headlines no topo funcionam como promessa editorial e devem permanecer visíveis. Segundo, imagens estáticas de pessoas, posts do X/Twitter, marcas de emissoras e cards não podem ser confundidos com o locutor ativo. Terceiro, a composição 4:5 e 1:1 é parte da edição original em diversos casos; um crop centralizado pode destruir contexto. Quarto, perguntas, respostas e reações de participantes secundários devem ser tratadas como uma unidade, com confiança de locutor explicitada.

O reserva também amplia a taxonomia com pronunciamento oficial, política pública, economia, palco, campanha e confronto com seguidor. Um vídeo com tese contrária ou frase de ataque isolada não deve ganhar pontuação máxima sem exemplo, evidência ou consequência. Em peças curtas de aproximadamente 30 segundos, o corte integral pode ser preferível quando já contém começo e payoff.

## Regras aplicáveis ao Furia Clips

| Sinal detectado | Tratamento no pipeline |
| --- | --- |
| Uma face estável e dominante | Permitir tracking facial conservador e marcar `reframe_9_16` |
| Duas ou mais faces, split-screen ou pergunta–resposta | Preservar original e marcar necessidade de revisão se o active speaker for ambíguo |
| Headline, post, card, GC ou marca de emissora | Detectar área segura; não cortar nem sobrepor; não tratar como face ativa |
| Insert documental | Exigir retorno à fala ou conclusão; manter o insert que sustenta a tese |
| Reação silenciosa | Não descartar apenas por baixa energia sonora; avaliar expressão, troca de fonte e contexto |
| Dado ou acusação | Exigir atribuição clara ao orador e marcar `needs_review` para validação humana |
| Corte iniciado com conector (`mas`, `porque`, `então`) | Penalizar abertura no meio da ideia, salvo se a pergunta anterior estiver incluída |
| Fim durante frase, card ou reação | Penalizar completude e impedir recomendação automática como clip final |

## Calibração alcançada no código

As regras de enquadramento foram aplicadas tanto ao corte rápido quanto ao processo completo. O sistema só anuncia reframe 9:16 quando a estabilidade do locutor é suficiente; entrevistas, layout indefinido, fullscreen e split-screen preservam o original. A central visual agora mostra essa decisão por clip e o motivo.

O feedback `approved`, `rejected` e `needs_review` é persistido. A calibração do ranking só é ativada após pelo menos 12 decisões finais, com no mínimo três aprovados e três rejeitados, e limita a correção a uma faixa pequena. Essa barreira evita que poucas decisões ou marcações de contexto alterem excessivamente o comportamento do seletor.

## Próxima expansão da análise

A coleta pública deve ser retomada somente quando o endpoint aceitar o cursor novamente. O crawler continua incremental, mas a resposta HTTP 401 impede avançar sem autenticação e não deve ser contornada. Enquanto isso, a próxima fonte de evidência pode ser uma nova amostra pública fornecida pelo editor ou os próprios exports aprovados/rejeitados pelo Furia Clips. Assim, a ferramenta evolui a partir de dados de uso real sem declarar cobertura histórica que não foi comprovada.

## Referências

[^1]: [Achados visuais dos 12 Reels do perfil principal](instagram_mbl_sample_visual_findings.md).
[^2]: [Relatórios audiovisuais individuais do perfil reserva](instagram_reserva_analysis/).
[^3]: [Base editorial consolidada dos dois perfis](instagram-mbl-catalog-analysis.md).
[^4]: [Catálogo paginado e status da coleta pública](instagram-feed-catalog-full.json) e [status do crawler](instagram-crawl-status-2026-08-13.md).

Fontes públicas de contexto: [@renansantosmbl](https://www.instagram.com/renansantosmbl/) e [@renansantosreserva](https://www.instagram.com/renansantosreserva/).
