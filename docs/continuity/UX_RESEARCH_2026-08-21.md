# Pesquisa de UX e Design: Estúdio Editorial
Data: 21/08/2026

## Visão Geral
Para redesenhar a interface do Furia Clips e resolver o problema de dessincronização de estados (ex: clicar num bloco antes de o vídeo estar pronto), foi conduzida uma pesquisa profunda sobre padrões de mercado em ferramentas de vídeo e dashboards de alta densidade. O objetivo é criar um "Estúdio Editorial por Etapas" incrível, responsivo e com microinterações refinadas, sem usar bibliotecas externas pesadas.

## Matriz de Referências e Decisões

| Referência de Mercado | Padrão Observado | Aplicação no Furia Clips | Risco Técnico |
|----------------------|------------------|---------------------------|---------------|
| **Opus Clip** | Timeline ancorada ao final da tela, sempre visível. | Fixar o `videoPreviewSection` no lado direito (desktop) ou num dock flutuante (mobile) durante a fase de análise. | Médio (requer reestruturação pesada do CSS Grid). |
| **Vizard.ai** | Estados vazios (Empty States) ilustrados e amigáveis. | Trocar o texto seco "Nenhum vídeo selecionado" por ícones de nuvem pulsantes e drag-and-drop iluminado. | Baixo. |
| **CapCut Web** | Navegação por abas horizontais (Source, Edit, Export). | Transformar as `workflow-steps` em uma barra de navegação global pegajosa (Sticky Header). | Baixo. |
| **Linear (App)** | Densidade de informação com microinterações sutis (hover com atraso). | Redesenhar os `action-cards` e `editorial-blocks` com bordas translúcidas que reagem ao mouse (efeito glassmorphism leve). | Médio (desempenho no scroll). |
| **Vercel** | Notificações não intrusivas no canto inferior. | Substituir os `alert()` e `run-bar` intrusivos por um sistema de `Toasts` no canto inferior direito. | Baixo. |

## O Problema do `focusReadingUnit`
Atualmente, o código `app.js` (linha 5030) faz isso:
```javascript
function focusReadingUnit(index) {
    const video = document.getElementById("videoPreview");
    if (video && Number.isFinite(Number(unit.start_s))) {
        video.currentTime = Number(unit.start_s);
    }
}
```
**O erro de UX:** O bloco pode ser clicado na etapa de "Análise", mas o vídeo pode não estar carregado no `videoPreview` (porque a etapa "Fonte" já foi fechada).

**Solução:** O vídeo não deve pertencer à etapa "Fonte". Ele deve ser um painel global à direita (em telas grandes) ou um modal/dock inferior (em telas pequenas) que escuta os cliques dos blocos, independentemente de qual etapa o usuário está navegando.

## Plano de Ação Visual
1. **Paleta e Tipografia:** Manter Preto/Dourado/Branco, mas usar "Inter" (já no vendor) com pesos mais marcados. Remover caixas com gradientes pesados e usar fundos sólidos com bordas sutis (`rgba(255,255,255,0.05)`).
2. **Layout Split-Screen (Desktop):** Esquerda = Fluxo (Fonte -> Análise -> Revisão). Direita = Player de Vídeo e Console.
3. **Microinterações:** Efeito de "glow" nos botões primários. Hover nos blocos editoriais que mostra o timestamp.
4. **Notificações:** Criar um gerenciador de Toasts no `app.js` para substituir mensagens de erro duras.
