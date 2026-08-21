# Validação do Erro 0/0 Clips em Lives Longas (2026-08-21)

## Contexto
O usuário relatou que em uma live longa (com mais de uma hora de entrevistas e perguntas) o sistema chegou a encontrar candidatos (ex: "Selecionados 24 clips"), mas no momento de cortar entregou "Corte completo: 0/0 clips gerados".

## Descoberta e Causa Raiz
Ao auditar o pipeline e rodar os testes, encontrei a raiz no arquivo `modules/clip_selector.py` e em como o "Perfil Político" se comporta.
- Quando o perfil editorial é "Renan Santos e MBL", a ferramenta ativa automaticamente o `speaker_identity_required = True`.
- Em uma live não diarizada (onde o sistema não sabe com 100% de certeza quem está falando em cada trecho), a flag `speaker_identity_available` fica `False`.
- **O problema fatal:** O `clip_selector.py` estava programado para forçar a flag `context_complete = False` para *qualquer* corte onde a identidade do locutor fosse incerta.
- Como vimos na auditoria anterior, os gates editoriais no `app.py` barram e impedem a renderização de qualquer corte que tenha `context_complete = False`. 

Ou seja: se o vídeo for longo e a diarização falhar (comum em lives com várias pessoas), o Furia Clips descartava *todos* os candidatos de uma vez antes do render, gerando o sintoma de `0/0 clips`.

## A Solução
Em `modules/clip_selector.py`:
1. Desvinculei a flag `context_complete` da identidade do locutor.
2. A incerteza sobre quem fala agora ativa apenas o `review_required = True` (ou seja, o corte é gerado e fica marcado para revisão humana), mas não destrói o contexto sintático do corte nem o barra de ser renderizado.
3. Atualizei os testes de unidade em `test_speaker_identity_context.py` para refletir essa nova separação de conceitos.

## Resultado do Teste
Com as correções, a suíte inteira (594 testes) passou com sucesso. O sistema agora vai gerar os cortes para lives longas e entregá-los na interface do usuário marcados para revisão de locutor, permitindo que o editor assista e decida, em vez de deletar silenciosamente o trabalho de seleção da IA.
