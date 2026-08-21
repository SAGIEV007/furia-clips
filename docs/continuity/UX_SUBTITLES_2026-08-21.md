# Decisão de Continuidade: Modernização de UX Visual das Legendas
Data: 21/08/2026

## Problema
As legendas do Furia Clips, apesar de serem "word-by-word", usavam um estilo estático padrão do ASS (Advanced SubStation Alpha) com borda sólida preta e fonte fina (Arial). O padrão atual de vídeos curtos (TikTok, Reels, Shorts) de cortes políticos (ex: estilo "Opus Clip" ou "Vizard") exige maior dinamismo e impacto visual.

## Solução Implementada
A classe `SubtitleGenerator` (`modules/subtitle_generator.py`) foi modificada para injetar tags ASS avançadas que simulam a estética moderna:

1. **Tipografia de Impacto:**
   - A fonte padrão, se for "Arial", é automaticamente substituída por "Impact" (ou similar espessa) no preset `shorts`, aumentando a legibilidade.

2. **Remoção de Borda Sólida (Outline):**
   - As bordas duras (`OutlineColour`) foram zeradas (`BorderStyle=1`, `Outline=0`).
   - O foco foi passado para o contraste de cores puras.

3. **Efeito "Pop" (Animação de Escala):**
   - Na palavra atual (destaque), foi injetada a tag de transformação temporal: `{\t(0,50,\fscx115\fscy115)\t(50,150,\fscx100\fscy100)}`.
   - Isso faz a palavra "pular" (aumentar 15% em 50ms) e depois voltar ao tamanho normal, criando um ritmo visual sincronizado com a fala.

4. **Foco e Transparência (Alpha):**
   - As palavras que *não* estão sendo faladas no momento recebem a tag `{\alpha&H40&}` (transparência), reduzindo seu destaque e guiando o olho do espectador diretamente para a palavra atual.

## Impacto
- Maior retenção de atenção nos cortes finais gerados.
- Aproximação com o padrão de mercado (Opus/Vizard) sem depender de bibliotecas pesadas de animação em Python, aproveitando apenas o poder de renderização nativa do FFmpeg via `.ass`.

## Próximos Passos (Para o Claude)
- Se o usuário pedir ainda mais animação, considere implementar o preset "karaoke_bounce" usando scripts lua externos (Aegisub) aplicados via FFmpeg, ou ajustar os milissegundos da tag `\t` para ficarem perfeitamente proporcionais à duração da palavra (atualmente está fixo em 50ms/150ms).
- A fonte "Impact" foi forçada como padrão, mas pode ser interessante expor isso na interface UI (`app.js`) para que o usuário escolha entre "Impact", "Montserrat Black" ou "Burbank".
