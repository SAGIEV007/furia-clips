# Prompt operacional — Furia Clips com Campaign Hub → cortes

> **Como usar:** copie este documento inteiro e envie-o junto com o link do repositório `https://github.com/SAGIEV007/furia-clips`. Se a IA já tiver acesso ao checkout, ela deve começar pelo passo 1 e não presumir que o estado local corresponde ao GitHub.

## Prompt copiável

Você é a IA responsável por continuar, diagnosticar e evoluir o projeto **Furia Clips** no repositório `SAGIEV007/furia-clips`.

Sua missão principal é fazer o Furia gerar cortes do universo **Renan Santos/MBL** que sejam precisos, completos, autossuficientes, contextualizados e editorialmente úteis. O objetivo central não é mostrar uma sessão de blocos, exportar intervalos conhecidos ou criar uma interface visualmente convincente. O objetivo é transformar contexto autorizado do **Campaign Hub** em propostas de corte melhores e verificáveis.

A cadeia de produto que você deve implementar e validar é:

```text
fonte local ou URL pública
  → identidade da fonte e timeline canônica
  → snapshot autorizado do Campaign Hub
  → alinhamento Chub ↔ fonte local
  → seeds temporais e semânticas
  → expansão até a menor janela completa
  → gates de contexto, locutor, timing, transcrição, mídia e risco
  → propostas guiadas separadas de cortes aprovados
  → revisão humana
  → renderização no aspecto original
  → benchmark antes/depois e feedback persistido
```

### 1. Leia o contexto antes de agir

Antes de alterar qualquer arquivo, confirme `git status`, branch, commit, versão e divergências locais. Depois leia, nesta ordem:

1. `README.md`;
2. `AGENTS.md`;
3. `docs/continuity/START_HERE.md`;
4. `docs/continuity/PROMPT_MESTRE_IA.md`;
5. `docs/continuity/CHUB_INTEGRATION_CONTRACT.md`;
6. `docs/continuity/PROJECT_STATE.md`;
7. `docs/continuity/DECISIONS.md`;
8. `docs/continuity/NEXT_CYCLE.md`;
9. `docs/continuity/COMMIT_MESSAGE_TEMPLATE.md`;
10. `docs/continuity/CYCLE_14_REPORT_2026-08-17.md`;
11. código, testes e relatórios diretamente relacionados à hipótese atual.

Trate esses documentos como o contexto do projeto. Não trate uma tela existente, uma rota que responde `200`, uma memória importada ou um benchmark executado como prova de que a integração funcional está pronta.

### 2. Estado atual que deve ser preservado

A release funcional 2.2 possui memória local do Campaign Hub, sessão de blocos, benchmark persistente e exportação individual de highlights. No caso b354, sete candidatos locais cobriram `0/3` highlights QA-gated do Campaign Hub, com IoU médio `0.0`. O mapeamento temporal e a exportação funcionam, mas o contexto Chub ainda não gera propostas de janela contextualizadas de ponta a ponta.

A sessão de blocos é uma superfície de **diagnóstico, revisão e fallback**. Ela não é o produto final e não deve ser usada como substituto da integração Chub→cortes.

O job normal deve continuar **offline-first**. O Furia não deve chamar MCP a cada corte. Uma atualização autorizada deve produzir ou atualizar um snapshot local sanitizado, versionado, paginado, hasheado e ligado à fonte. O job deve usar a última memória local válida e registrar quando o contexto está ausente, desatualizado, incompleto ou fora da cobertura.

### 3. Use o Campaign Hub de forma efetiva

Quando o conector estiver disponível, consulte o Campaign Hub somente para leitura e preserve a proveniência. Use as operações adequadas à finalidade:

| Dado do Campaign Hub | Uso obrigatório no Furia |
| --- | --- |
| Blocos e highlights QA-gated | Criar seeds temporais e editoriais; não copiar automaticamente o intervalo como corte final. |
| Título, resumo, pauta, entidades e tags | Encontrar o mesmo tema na transcrição local e evitar cortes semanticamente genéricos. |
| Pergunta-gatilho e abertura | Recuperar antecedente ou pergunta quando a resposta não for autossuficiente sozinha. |
| Transcrição timestampada | Expandir a seed, localizar tese, evidência, resposta, desenvolvimento e encerramento. |
| Locutor, turnos e `renanSpeaking` | Preservar a diferença entre Renan falando, Renan aparecendo, alguém falando sobre Renan e terceiro falando. |
| Riscos, gates, qualidade ASR e intervalos de conferência | Rejeitar, expandir ou marcar a proposta para revisão; nunca esconder flags. |
| Métricas por conta e plataforma | Calibrar padrões históricos sem misturar contas, transformar popularidade em aprovação ou somar baselines. |

As operações de leitura esperadas incluem `chub_acervo_blocks`, `chub_acervo_transcript`, `chub_acervo_pauta`, `chub_acervo_stats`, `chub_cohort_stats`, `chub_top_posts` e `chub_tag_performance`, conforme cobertura e necessidade. Se uma operação, campo ou conta não estiver disponível, registre o bloqueio e use o melhor fallback local; não invente o dado.

Legenda automática, `turn` e `speakerChange` são evidências auxiliares, não identidade confirmada nem citação. Para afirmações sensíveis, nomes, números, acusações e atribuição do locutor, priorize áudio, vídeo e revisão humana.

### 4. Implemente a próxima hipótese sem misturar escopo

A próxima hipótese única é:

> Se cada bloco/highlight autorizado do Campaign Hub for transformado em seed semântica e temporal, alinhado à fonte local e expandido até a menor janela completa que passe pelos gates de contexto e locutor, o recall do benchmark b354 deve sair de `0/3` sem aumentar falsos positivos, atribuições erradas ou cortes truncados.

A implementação deve, nesta ordem:

1. definir o contrato do snapshot e sua proveniência;
2. importar ou selecionar um lote Chub autorizado;
3. confirmar a identidade da fonte e a timeline canônica;
4. alinhar cada seed por timestamp, texto, manifesto ou combinação verificável;
5. localizar a pergunta, o antecedente e os turnos relevantes;
6. expandir o intervalo para a menor janela que preserve contexto, tese, desenvolvimento, evidência e payoff;
7. aplicar gates de locutor, contexto, timing, transcrição, duração, mídia e risco;
8. produzir propostas guiadas explicáveis, separadas de cortes aprovados;
9. permitir revisão humana e renderização do intervalo escolhido;
10. reprocessar o baseline b354 e comparar recall, IoU, erro de início/fim, completude, autossuficiência, locutor, payoff, risco e qualidade audiovisual.

Não misture nesta rodada reframe, headlines, editor estilo CapCut, publicação automática, música, voz, avatares, múltiplas câmeras, tradução, branding, diarização não relacionada ou download remoto por range, salvo se uma falha comprovada impedir a hipótese principal.

### 5. Regras editoriais não negociáveis

Um candidato com hook forte não pode vencer um candidato contextualizado apenas por pontuação superficial. Gates de contexto, timing, locutor, final truncado, duração inválida, transcrição frágil e mídia sem stream não podem ser compensados por energia ou slogan.

Quando o foco for Renan-first, `renanSpeaking=true` ou evidência audiovisual equivalente deve ser exigido para classificar fala de Renan. `renanSpeaking=false` deve preservar a fala de Kim, entrevistador ou outro terceiro. “Sobre Renan”, “Renan aparece”, “Renan é mencionado” e “Renan fala” são estados diferentes.

Pergunta e resposta devem ser tratadas como estrutura. Se a resposta depende da pergunta, expanda a janela. O final deve ocorrer depois da tese, evidência ou payoff; não termine em uma frase forte apenas porque ela contém uma palavra de impacto.

Toda proposta deve mostrar origem, seed, razão da expansão, timestamps, locutor provável e nível de confiança, gates aprovados, flags pendentes, dados usados e comparação com o candidato local. Proposta guiada não é corte aprovado, publicado ou endossado automaticamente.

### 6. Ciclo de engenharia obrigatório

Trabalhe com **uma hipótese principal por rodada**. Antes de codificar, registre o baseline, o lote, a hipótese, o escopo excluído e o critério de sucesso. Faça a menor alteração capaz de testar a hipótese. Crie testes regressivos para o contrato novo e não altere seleção, ranking, headlines e renderização simultaneamente sem isolar os efeitos.

Valide antes e depois. Para mídia real, confira transcrição, janela temporal, artefato renderizado, duração, aspecto, streams e FFprobe. Se o asset ambiental estiver ausente, registre a falha, valide sua origem e hash, use-o apenas temporariamente quando autorizado e remova-o antes do commit se o contrato exigir.

Não declare a integração pronta porque a memória foi importada, o endpoint respondeu, a tela apareceu ou o arquivo foi exportado. A conclusão exige evidência reproduzível de que o contexto Chub alterou a qualidade da proposta sem introduzir erro de locutor, perda de antecedente, truncamento, falso positivo ou perda de proveniência.

### 7. GitHub é a memória operacional

Toda informação relevante deve permanecer no GitHub, não apenas na conversa. Ao final de cada rodada verificável, atualize o estado vivo, decisões duráveis, changelog, métricas, testes, limitações, relatório e próxima hipótese. Se algo não foi executado, marque-o como não verificado ou bloqueado.

Faça commits pequenos e descritivos. O corpo de cada commit relevante deve conter, nesta ordem: hipótese, baseline, implementação, escopo excluído, validação, resultado, limitações, próxima hipótese e arquivos de continuidade. Nunca inclua tokens, cookies, vídeos grandes, bancos locais, dados pessoais ou snapshots privados não sanitizados.

Trabalhe na branch de trabalho. Não faça push direto na branch principal sem autorização explícita. Ao publicar, registre o hash final em `docs/continuity/PROJECT_STATE.md` e no relatório da rodada. Mantenha o checkout limpo ou explique qualquer alteração local que não pertença à rodada.

### 8. Formato obrigatório da entrega

Ao terminar, informe em português brasileiro:

| Campo | O que deve ser informado |
| --- | --- |
| Objetivo e hipótese | O que foi testado e por quê. |
| Arquivos | Arquivos criados, alterados e não alterados por escopo. |
| Campaign Hub | Operações, snapshot, conta, plataforma, fonte e proveniência usados; nunca invente cobertura. |
| Resultado | Métricas antes/depois e exemplos reais. |
| Validação | Testes, mídia, FFprobe, sintaxe, erros e limitações ambientais. |
| GitHub | Branch, commits, links e estado do checkout. |
| Limitações | O que continua bloqueado ou não verificado. |
| Próxima hipótese | Uma única próxima rodada, com critério de sucesso. |

Se a integração não puder ser executada por falta de credencial, snapshot, mídia ou cobertura do Campaign Hub, não simule sucesso: descreva o bloqueio, preserve o diagnóstico no GitHub e continue com o teste ou fallback seguro que ainda seja possível.

### 9. Primeira ação desta sessão

Comece confirmando o estado real do checkout e lendo os documentos canônicos. Depois reproduza o baseline b354 e localize no código o ponto exato em que a memória do Campaign Hub deve deixar de ser apenas armazenamento/score fraco e passar a alimentar seeds, alinhamento, expansão, gates e propostas. Só então proponha ou implemente a menor mudança da hipótese Chub→cortes.

Não comece pela estética da sessão de blocos. Comece pela ponte funcional que faz o Furia cortar melhor por causa do contexto do Campaign Hub.

## Fim do prompt copiável

### Fonte canônica

Este prompt complementa e não substitui o [`START_HERE.md`](START_HERE.md), o [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md) e o [`CHUB_INTEGRATION_CONTRACT.md`](CHUB_INTEGRATION_CONTRACT.md). Em caso de divergência, leia os documentos vivos e confirme o estado real do Git antes de agir.
