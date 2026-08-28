# Relatório do ciclo experimental — 28 de agosto de 2026

## Escopo

Este ciclo manteve o **Furia 1 como único motor canônico** para transcrição, geração de candidatos, reparo de bordas, gates, ranking e exportação. Gemini e Campaign Hub foram tratados como recursos auxiliares, opcionais e subordinados à revisão humana. Nenhuma mídia, transcrição, legenda, banco, log bruto, chave ou URL privada foi adicionada ao repositório.

## QA manual

A instância local foi testada como usuário real. O modal de importação abriu e fechou sem selecionar arquivo, com explicação sobre cópia local, formatos aceitos e ação de confirmação. Ajustes abriu no mesmo Studio e expôs Whisper local, motor de análise, chave Gemini opcional, interpretação audiovisual, memória histórica do Chub, duração e captions. Biblioteca, Cortes, Console e retorno à Mesa também foram testados.

O fluxo Mesa → Biblioteca → Cortes → Mesa permaneceu em uma única aplicação, sem segunda aba, sem troca silenciosa de instância e sem erro no estado vazio. A persistência de projeto já coberta pelo ciclo anterior permanece protegida por regressão dedicada.

## Calibração e disponibilidade local

O inventário local identificou três fontes completas compatíveis com a matriz sanitizada: aproximadamente **17 min 15 s**, **29 min 32 s** e **44 min 30 s**. Nesta sessão, os arquivos completos de Fonte A/B não estavam mais disponíveis nos workspaces ativos; por isso, não foi iniciado um novo processamento que pudesse produzir uma conclusão artificial. O banco de upload preserva resultados históricos agregados, incluindo execuções com 20, 9 e 30 clips, mas esses resultados não foram tratados como uma nova rodada audiovisual.

Essa decisão preserva a validade da calibração: sem o arquivo original e sua referência correspondente, não se deve declarar melhoria editorial com base apenas em contagem de clips ou em timestamps persistidos. As regras generalizáveis de perguntas fragmentadas, turnos, abertura e fechamento do raciocínio, bordas de interrupção e preservação de oportunidades posteriores continuam cobertas pelos fixtures do repositório.

## Regressão automatizada

A regressão focada em fronteiras, divisão de segmentos, palavras temporais, turnos de entrevista, perguntas, fechamento do raciocínio, volume e pool passou com **96 testes aprovados**. A regressão de integrações opcionais — Chub, memória histórica, vínculo de Acervo, batching, revisão Gemini, quota, espera, multimodalidade e backend auxiliar — passou com **81 testes aprovados**.

A suíte completa passou com **880 testes aprovados**, **27 ignorados** e **2 xfails esperados**, em 17,74 segundos. `git diff --check` também passou.

## Passe de legibilidade e responsividade

Foi aplicado um passe CSS reversível, sem mudança de contrato de backend. O passe reforça foco visível, alvos de toque, altura mínima de botões, leitura de placeholders, quebra segura de texto, recolhimento do Console, rolagem contida de modais e reflow dos controles em telas estreitas. A composição retrô foi preservada, mas a hierarquia das superfícies de trabalho ficou mais adequada para teclado e toque.

A Mesa recarregou corretamente após a mudança, mantendo os controles de importação, Console, Ajustes, contadores, estado vazio e navegação inferior em uma única página.

## Publicação

As atualizações foram publicadas exclusivamente na branch experimental `furia-studio-experimental-20260828`. Os commits deste ciclo foram:

| Commit | Conteúdo |
|---|---|
| `f82def5` | Relatório inicial de QA manual sanitizado |
| `fa3330f` | Regressão focada de fronteiras e pool editorial |
| `c0eba34` | Regressão dos contratos opt-in de Chub e Gemini |
| `cb594fa` | Passe de legibilidade e alvos responsivos |
| `2ad0d96` | Suíte completa e encerramento da rodada de testes |

## Próximo ciclo

O próximo ciclo deve retomar a análise audiovisual de Fonte A e Fonte B quando os arquivos privados forem disponibilizados novamente no workspace local. A ordem permanece: processar com Furia 1, comparar com referências humanas, revisar amostras de maior risco, adicionar somente regras generalizáveis com fixtures positivos e negativos, e então continuar o refinamento responsivo por larguras de 320, 375, 768, 1024 e 1440 pixels.
