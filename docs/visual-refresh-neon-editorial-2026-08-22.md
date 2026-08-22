# Furia Clips — identidade visual Neon Editorial

**Data:** 22 de agosto de 2026
**Escopo:** redesign visual e de UX; nenhum ranking, transcrição, ingestão, renderização ou regra de seleção foi alterado nesta rodada.

## Direção

O Furia passa a ser tratado como uma **bancada de inteligência editorial**. A organização usa a lógica de editores de vídeo — matéria-prima, fonte, preview, contexto, revisão e exportação — mas a estética não tenta copiar CapCut, OpusClip ou Vizard. A linguagem visual combina uma superfície de trabalho escura, sinais de estado, cards de alta informação e uma command surface inspirada em ferramentas de produtividade.

A identidade recebeu o nome **Neon Editorial**: azul-noite quase preto como base, grafite azulado nas superfícies, verde-limão como ação primária, ciano/mint como estado saudável, azul e violeta para análise/IA e coral para atenção. O brilho é reservado para foco e mudança de estado. A tipografia, as linhas e os espaçamentos mantêm leitura editorial, sem transformar a tela em um painel neon decorativo.

## O que mudou visualmente

| Área | Tratamento |
|---|---|
| Cabeçalho | Título mais forte, copy curta, estado do workspace e versão em uma faixa compacta com linha de energia sutil. |
| Sidebar | Superfície escura elevada, marca Furia reduzida, controles com campos mais consistentes e dicas secundárias menos ruidosas. |
| Workflow | Fonte → Análise → Revisão → Aprendizado em uma trilha compacta com estado ativo e conectores luminosos. |
| Matéria-prima | Drop zone com foco visual, profundidade e ação Importar Video claramente dominante. |
| Fonte | Tabs em cápsula, campos com superfícies profundas e estados mais legíveis. |
| Contexto/IA | Blocos com faixa lateral violeta/azul para diferenciar análise de operação comum. |
| Cards de ação | Cards modulares com hover, sinal de estado, CTA previsível e destaque especial para Processo Completo. |
| Operação diária | Métricas com quatro estados cromáticos: andamento, fila, concluído e atenção. |
| Fila de revisão | Central e cards com hierarquia maior, scorecard visual, revisão necessária e bordas/ações mais destacadas. |
| Console | Mantido como área secundária, com contraste de terminal e progresso mais claro. |
| Responsividade | Sidebar e workflow adaptados para telas estreitas; grids e scorecards colapsam sem rolagem horizontal. |

## Princípios de UX adotados

A interface mostra primeiro o que o editor precisa decidir e deixa configurações e histórico como camadas secundárias. Esse princípio vem da orientação de dashboards que recomenda começar pela pergunta do usuário e usar alinhamento, tamanho, cor e forma para indicar importância [1].

A navegação global e os painéis seguem a ideia de um “chrome” consistente, com alinhamento preciso entre labels, ícones, tabs e superfícies, uma prática discutida no redesenho do Linear [2]. A organização também preserva a ideia de fluxo curto de importar, analisar, revisar e exportar observada nas interfaces de edição de vídeo [3] [4].

A estética futurista usa uma command surface como referência conceitual do Raycast: ações importantes devem ser rápidas, compactas e encontráveis, sem transformar cada capacidade em um botão permanente [5].

## Limites deliberados

Nenhum componente funcional foi removido, nenhum id de frontend foi alterado e nenhum contrato técnico foi modificado. A camada foi implementada por tokens, CSS, copy de apresentação e ajustes de layout. O Campaign Hub não participa desta alteração visual e não recebeu nenhuma escrita.

O verde-limão não representa aprovação automática, viralização ou confiança estatística; ele é somente a cor de ação e foco da interface. Status de revisão, erro e disponibilidade continuam sendo exibidos por texto e estrutura, não apenas por cor.

## Referências

[1]: https://grafana.com/blog/getting-started-with-grafana-best-practices-to-design-your-first-dashboard/ "Grafana — Getting started with dashboard design"
[2]: https://linear.app/now/how-we-redesigned-the-linear-ui "Linear — How we redesigned the Linear UI"
[3]: https://vizard.ai/tools/ai-video-editor "Vizard — AI Video Editor"
[4]: https://www.capcut.com/resource/capcut-tutorial-for-beginners "CapCut — Tutorial and editing workflow"
[5]: https://www.raycast.com/ "Raycast — productivity launcher"


## Segunda rodada: redesign estrutural

A primeira versão foi considerada superficial porque alterava principalmente cores. A segunda rodada corrigiu isso com três mudanças estruturais. O cabeçalho principal recebeu o asset original `static/assets/furia-hero-atlas.png`, criado especificamente para o Furia em 2560×1440, com composição cinematográfica e espaço negativo para o título. A sidebar deixou de ser uma coluna colada à janela e passou a funcionar visualmente como um dock flutuante, com borda, raio, sombra e respiro próprios. O cabeçalho passou a ser uma âncora de marca com imagem, máscara, leitura `LONGFORM → SHORTS` e estado de workspace.

A aplicação continua organizada como uma ferramenta de edição, mas a estética agora comunica uma estação de inteligência editorial: imagem de abertura, workflow em trilha, painéis em camadas, sinais de estado e ação primária iluminada. O asset é original e não contém logos, pessoas identificáveis, texto gerado ou marca de terceiros.

A validação headless em 1440×1000 confirmou a presença do hero, o carregamento HTTP do PNG e a composição integrada. O teste visual da tela inicial vazia não substitui uma captura futura com clips carregados; por isso, a fila de revisão mantém seus estilos específicos e deve ser revisitada quando houver um lote disponível.
