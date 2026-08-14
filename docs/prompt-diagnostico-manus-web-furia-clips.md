# Prompt para usar no Manus Web — diagnóstico e evolução do Furia Clips

Você deve atuar como engenheiro sênior de produto, software e edição audiovisual responsável por verificar e evoluir o projeto **Furia Clips**, disponível em:

- Repositório: https://github.com/SAGIEV007/furia-clips
- Branch de trabalho: `manus/rebuild-opus-parity`
- Objetivo: transformar lives políticas longas em cortes verticais ou na proporção original, priorizando contexto completo, alto potencial editorial, enquadramento seguro, ranking explicável e revisão visual profissional.

## Contexto do produto

O Furia Clips é uma ferramenta local de clipping automático de vídeos longos para Shorts, Reels e TikTok. O uso principal é processar aproximadamente oito lives por dia, com três a quatro horas cada, e encontrar a nata dos cortes para chegar a uma meta operacional de **39 a 50 cortes aprovados por dia**, priorizando qualidade e não quantidade.

A referência editorial são os formatos observados nos perfis públicos `@renansantosmbl` e `@renansantosreserva`: monólogos políticos, entrevistas, podcasts, reacts, perguntas e respostas, cortes de palco, selfies, bastidores, campanhas, peças institucionais, B-roll, split-screen e vídeos com narrativa visual sem fala contínua.

O sistema deve funcionar de forma **genérica para conteúdo político**, podendo usar foco específico em Renan Santos/MBL quando configurado. Não presuma que todo vídeo seja sobre Renan.

## Restrições obrigatórias

1. **Não publique, faça push, merge, release ou alteração destrutiva no GitHub.** A publicação só poderá ocorrer depois de autorização explícita do usuário.
2. Não apague dados editoriais, feedbacks, projetos, clips aprovados ou bancos de dados existentes.
3. Não exponha, copie, mostre ou grave chaves de API, cookies, tokens ou informações pessoais.
4. Não contorne bloqueios, CAPTCHAs, respostas HTTP 401/403, limites de plataforma ou mecanismos de autenticação.
5. Se alguma capacidade não estiver disponível no Manus Web, informe a limitação com precisão e continue as verificações que forem possíveis.
6. Não diga que algo foi executado apenas porque o código parece correto. Toda conclusão deve estar acompanhada de evidência: URL, SHA, arquivo, saída de teste, log ou captura de tela.
7. Não pare apenas para pedir confirmação. Execute tudo o que for seguro e não destrutivo; peça intervenção somente se uma ação realmente exigir acesso que você não possui.

## Primeira tarefa: comprovar se o trabalho está funcionando

Antes de propor novas melhorias, faça um diagnóstico real e objetivo.

### 1. Verificar o estado do repositório

Abra o repositório e confirme:

- qual branch está sendo visualizada;
- qual é o commit mais recente;
- se a branch `manus/rebuild-opus-parity` existe;
- se os arquivos de persistência editorial, ranking, revisão visual, cancelamento, importação de transcrição e prioridade Gemini estão presentes;
- se o GitHub mostra commits recentes ou se está visualizando outra branch;
- se há diferença entre o estado local e o estado publicado, quando essa informação estiver disponível.

Não confunda a branch de trabalho com a branch principal. Registre o SHA real e o link da branch.

### 2. Verificar a estrutura do aplicativo

Inspecione pelo menos estes arquivos, quando estiverem disponíveis:

- `app.py`
- `config.py`
- `database.py`
- `modules/clip_selector.py`
- `modules/editorial_ranker.py`
- `modules/viral_ranker.py`
- `modules/gemini_video.py`
- `modules/persistent_data.py`
- `static/js/app.js`
- `static/css/style.css`
- `templates/index.html`
- testes em `tests/`
- documentação em `docs/`

Verifique se o fluxo principal existe e está coerente:

1. upload ou importação por link;
2. escolha segura do diretório de destino;
3. download em até 1080p quando a fonte permitir;
4. importação de transcrição timestampada manual ou pública;
5. análise Gemini online como prioridade quando configurada;
6. fallback local explícito para Whisper CPU;
7. geração de candidatos;
8. ranking editorial explicável;
9. ajuste de fronteiras e cenas;
10. decisão de reframe somente quando o active speaker estiver seguro;
11. exportação dos clips;
12. revisão visual;
13. registro persistente de aprovação, rejeição e ajustes;
14. meta diária de 39–50 aprovados;
15. backup e restauração segura dos dados editoriais.

### 3. Verificar a experiência do usuário

Confira visualmente se a interface apresenta, sem depender de logs técnicos:

- estado da operação atual;
- progresso real de download, transcrição, análise e renderização;
- botão de cancelamento seguro;
- fonte da transcrição: Gemini, legenda, manual ou Whisper;
- razão de fallback quando o Gemini não concluir;
- quantidade de clips encontrados, aprovados, rejeitados e pendentes;
- score e fatores do ranking;
- tipo de fechamento: conclusão, frase fechada, continuidade/cliffhanger ou fecho a revisar;
- tema e penalidade de diversidade;
- família editorial, quando disponível;
- recomendação de proporção original ou reframe;
- aviso quando houver múltiplos locutores, split-screen, B-roll, texto visual ou fala sobreposta;
- biblioteca de projetos e lives recentes;
- backup e saúde dos dados editoriais.

Verifique especificamente se a seleção de pastas abre um explorador nativo ou se o usuário fica obrigado a colar caminhos manualmente. Se o ambiente web não puder abrir o explorador nativo do computador, registre essa limitação em vez de simular que funcionou.

### 4. Executar verificações seguras

Se houver acesso a terminal ou ambiente de execução, execute sem alterar o GitHub:

```bash
python3 -m pytest -q
python3 -m compileall -q app.py config.py database.py modules
node --check static/js/app.js
git diff --check
```

Se o ambiente não tiver terminal, faça uma inspeção equivalente pelos arquivos e pela interface. Registre exatamente quais verificações foram possíveis e quais não foram.

Quando um teste falhar, diagnostique a causa, corrija somente arquivos locais e execute o teste novamente. Não faça commit ou push.

### 5. Verificar a integração Gemini

Confirme no código e na interface:

- Gemini online é tentado antes do Whisper CPU;
- HTTP 503 temporário não causa loop infinito nem perda silenciosa do job;
- o fallback local usa configuração compatível com CPU, incluindo `fp16=False` quando necessário;
- o usuário consegue fornecer uma transcrição timestampada manualmente;
- o sistema não exige Gemini para funcionar quando o usuário prefere modo local;
- a chave não aparece em logs, HTML, respostas de API ou mensagens de erro;
- limites e falhas são exibidos de forma visual e compreensível.

Não peça ao usuário para colar uma chave no chat e não inclua nenhuma chave no relatório.

### 6. Verificar a qualidade editorial do ranking

Faça uma revisão específica do ranqueador. O candidato forte deve conter, quando aplicável:

- gancho compreensível;
- unidade semântica;
- pergunta e resposta completas em entrevistas;
- premissa, justificativa e consequência;
- evidência, card ou B-roll atribuído corretamente;
- especificidade de pessoas, fatos, números ou propostas;
- conclusão real, não apenas promessa de continuação;
- penalidade para cliffhanger e fala interrompida;
- diversidade temática entre os clips do mesmo portfólio;
- penalidade para duplicatas e cortes quase iguais;
- suporte a formatos genéricos, não apenas ao nome Renan;
- reframe conservador quando há duas ou mais pessoas, split-screen, cards ou material visual essencial.

Verifique se o resultado explica por que o clip foi selecionado e se o editor consegue corrigir início, fim, enquadramento e decisão sem abrir outro programa.

### 7. Verificar persistência dos dados

Confirme se feedback editorial, clips aprovados, projetos e backups ficam fora da pasta substituível do GitHub, preferencialmente em diretório persistente configurável. Verifique se:

- reprocessar o mesmo vídeo preserva a identidade editorial do clip;
- o feedback não desaparece quando o código é atualizado;
- o backup contém manifesto e validação SQLite;
- uma restauração cria pré-backup automático;
- caminhos perigosos ou ZIP inválido são rejeitados;
- endpoints de status não vazam segredos.

Não restaure backup nem sobrescreva dados reais durante este diagnóstico.

## Se o diagnóstico comprovar funcionamento

Depois de comprovar o estado atual, continue somente com melhorias locais seguras e pequenas, priorizadas nesta ordem:

1. corrigir bugs que impeçam o fluxo principal;
2. melhorar progresso, erros e cancelamento na interface;
3. melhorar seleção de cortes conclusivos e diversidade do portfólio;
4. melhorar classificação de entrevistas, reacts, campanhas, institucionais, selfies e cortes sem fala;
5. melhorar a decisão de reframe e preservar composição original quando necessário;
6. registrar feedback editorial de modo persistente;
7. adicionar testes de regressão;
8. atualizar a documentação em português brasileiro.

Não implemente diarização pesada ou dependências grandes sem medir impacto em instalação, CPU e operação offline. Primeiro deixe o sistema funcional e explicável; depois experimente pyannote, WhisperX ou alternativa equivalente em modo opcional.

## Relatório obrigatório ao final

Entregue um relatório curto, mas baseado em evidências, contendo:

| Item | Resultado exigido |
| --- | --- |
| Estado real do GitHub | Branch, SHA, data do último commit e link verificado |
| Estado local | Arquivos modificados e se existem alterações não publicadas |
| Testes | Comando executado, quantidade aprovada e falhas |
| Interface | O que foi verificado visualmente e o que não foi possível verificar |
| Gemini | Prioridade online, fallback e eventuais limitações |
| Ranking | Fatores confirmados e eventuais lacunas |
| Persistência | Local dos dados e status de backup, sem mostrar segredos |
| Melhorias feitas | Lista exata de arquivos e mudanças locais |
| Bloqueios | Limitações reais, sem contornar plataformas |
| Próximo passo | Uma única recomendação prioritária, sem publicar nada |

A resposta final deve separar claramente estas três categorias:

- **Comprovado funcionando**;
- **Existe no código, mas não foi possível executar/verificar**;
- **Ainda falta implementar**.

Não use frases vagas como “parece funcionar” ou “está tudo pronto”.

Comece agora pelo diagnóstico e só depois execute melhorias locais seguras. Não faça push, merge, publicação ou restauração de backup.
