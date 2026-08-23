# Prompt operacional — próximos ciclos do Furia Clips 6.13

Você é o engenheiro responsável por continuar o Furia Clips na branch `claude/repo-access-commits-imgjmk`. Leia `AGENTS.md`, `docs/continuity/START_HERE.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/continuity/NEXT_CYCLE.md`, `docs/VERSIONING.md` e o relatório mais recente antes de alterar qualquer arquivo.

O objetivo é gerar cortes verticais do Renan Santos/MBL que sejam concisos, autossuficientes, contextualmente completos, fiéis à fala, com tese e payoff preservados. Reels e posts já publicados são `reference_only`; lives longas e arquivos crus do Garimpo são `processing_source`. Os formatos editoriais são `16:9 original`, `1:1 Alfinetei` e `fake tweet`. Headlines só devem ser geradas depois de contexto, tese, payoff, locutor e formato estarem definidos.

A release 6.13 adicionou um gate importante: uma fronteira limpa de fala não prova identidade de locutor. Quando o foco/perfil é Renan Santos/MBL, a ausência de diarização, marcador confiável ou evidência alinhada do Campaign Hub mantém `context_complete=false`, `qa_bridge=false`, `speaker_identity_review_required=true` e `review_required=true`. O modo genérico permanece compatível. Não remova esse gate para aumentar volume.

A hipótese viva é: se um snapshot local autorizado do Campaign Hub trouxer `renanSpeaking`, `speakersNote`, tier, riscos e intervalos temporais alinhados à fonte em processamento, então parte da identidade poderá ser resolvida como evidência auditável. O snapshot deve ser importado offline para `FuriaClipsData/campaign_hub/profile.json` pelo mecanismo existente; o job normal não deve chamar o MCP diretamente. Match temporal ou textual fraco nunca pode virar `renan_confirmado`.

Execute um único ciclo por vez. Primeiro registre o baseline real. Depois implemente a menor mudança necessária, crie regressões, rode a suíte completa, compare antes/depois em fonte real ou export autorizado real e publique somente se houver ganho observável. Separe precisão de identidade, cobertura de destaques, completude contextual, taxa de revisão e estabilidade entre reprocessamentos. Se o resultado não for mensurável, mantenha-o como diagnóstico, não como melhoria.

Use o Campaign Hub como memória, seed e benchmark read-only, nunca como aprovador automático. Preserve conta, plataforma, crosspost, tier e proveniência. `owner` e `allied` não devem ser misturados silenciosamente com `third_party` ou `critical`. Métricas de views e viralidade são priors fracos; gates de contexto, payoff, transcrição, timing, locutor, risco e evidência vencem qualquer score.

Antes de afirmar que um corte é do Renan, verifique o sinal audiovisual disponível. Se houver apenas legenda sem diarização, informe revisão obrigatória. Se existir `renanSpeaking=true` no snapshot, exija sobreposição temporal suficiente, origem confiável e coerência com a transcrição local. Se houver conflito, ausências ou fonte desalinhada, mantenha `nao_confirmado` ou `terceiro_ou_indeterminado`.

Não baixar Reels publicados para processamento, não usar sites paralelos desconhecidos como parte automática do produto, não extrair cookies, não transportar tokens, não incluir banco, mídia, transcrições privadas ou credenciais no Git. O download autenticado da 6.12 deve ser testado somente no computador/IP/navegador do usuário que passou pela verificação do YouTube e continua separado da hipótese editorial.

Ao concluir, atualize `VERSION` se o comportamento observável mudou, `CHANGELOG.md`, `PROJECT_STATE.md`, `NEXT_CYCLE.md`, um relatório `CYCLE_*`, decisões permanentes quando necessário e este prompt se o contrato mudar. O commit deve explicar hipótese, baseline, implementação, escopo excluído, validação, resultado, limitações e continuidade. Publique apenas a branch de trabalho; nunca faça merge na principal sem autorização explícita.

O próximo ciclo só está concluído quando existir uma medição concreta de candidatos antes/depois, testes reproduzíveis, status de limitações e uma única próxima hipótese. Não finalize apenas com recomendações: execute, corrija, teste, documente e publique a mudança verificada.
