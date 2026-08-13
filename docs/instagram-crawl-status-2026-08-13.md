# Status do inventário público do Instagram — 13/08/2026

O endpoint público de feed permitiu enumerar 60 itens do perfil `@renansantosmbl` em cinco páginas, sendo 59 vídeos, antes de retornar HTTP 401 na sexta página. Para `@renansantosreserva`, o catálogo salvo possui 12 itens na primeira página, todos vídeos, e o endpoint também indica mais páginas. A página pública informa aproximadamente 3.499 posts no perfil principal e 352–353 no Reserva, mas o inventário completo não foi obtido nesta execução.

O crawler é incremental e salva cada página; o erro 401 foi registrado como limitação de acesso/paginação, não como ausência de conteúdo. Não é correto declarar que todos os vídeos foram assistidos. A análise audiovisual local já pode ser executada sobre os 12 Reels do Reserva previamente baixados e os 12 Reels recentes do perfil principal baixados em `workspace/instagram_mbl_sample/`.

A estratégia recomendada é manter três estados por item: `inventariado`, `baixado` e `analisado`. O próximo lote deve retomar com uma sessão/rota de acesso válida ou com URLs individuais públicas, respeitando backoff e sem tentar milhares de downloads em uma única execução.
