# Pesquisa e Implementação — Perfil Político (2026-08-21)

## Objetivo
Enriquecer a taxonomia e o vocabulário do `political_profile.py` para que a detecção de formato e de sinais editoriais ("family", "topic", "conflict") responda melhor aos termos usados pelo MBL, Missão e Renan Santos nas campanhas atuais.

## Oportunidade
O perfil político já detectava bem discursos institucionais (governo, STF, congresso), mas carecia de sensibilidade para temas locais, pautas de segurança pública mais contundentes e o jargão próprio da pré-campanha/Livro Amarelo.

## Implementação
Em `modules/political_profile.py`:
1. **Tópicos (`TOPIC_TERMS`):** Adicionados `livro amarelo`, `desfavelizacao`, `favela`, `moradia`, `pcc`, `faccao`, `milicia`, `interior`.
2. **Conflito (`CONFLICT_CUES`):** Adicionados termos fortes de segurança e retórica (`guerra`, `punicao`, `cadeia`, `fuzil`, `bola de ferro`, `incompetente`).
3. **Afirmação (`CLAIM_CUES`):** Adicionados marcadores de resumo oral que conectam o perfil aos hooks já mapeados (`pra resumir`, `em resumo`, `o que acontece e`, `no final das contas`).

## Testes e Validação
- Os testes unitários (`test_political_profile.py`) passaram.
- A melhoria garante que trechos falando de "desfavelização" ou "Livro Amarelo" recebam o boost de tópico político corretamente e que ganchos sobre "bola de ferro" sejam classificados como denúncia/conflito para as headlines.
