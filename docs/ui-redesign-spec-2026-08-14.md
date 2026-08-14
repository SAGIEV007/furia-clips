# Especificação visual — Furia Clips

## Objetivo

Transformar o dashboard atual em uma estação editorial de clipping: o usuário deve entender em poucos segundos qual vídeo está ativo, qual etapa está em andamento, qual fonte de transcrição será usada e onde revisar/aprovar os cortes.

## Direção

A interface preserva o tema escuro e o amarelo da marca, mas troca o contraste bruto por uma escala de superfícies grafite, bordas discretas e acentos semânticos. O amarelo fica reservado para ação primária, seleção ativa e foco editorial. Verde representa concluído/aprovado; âmbar representa revisão; vermelho representa falha ou rejeição; azul representa informação.

## Hierarquia

A experiência será organizada em quatro níveis: contexto da sessão no cabeçalho; preparação da fonte; execução de análise; revisão e aprendizado. Configurações avançadas permanecem acessíveis na lateral, mas com menor competição visual. O console continua disponível como diagnóstico, porém não domina o fluxo.

## Decisões de UX

A tela inicial deverá ter um estado vazio útil, com uma chamada primária para importar vídeo e uma explicação curta do pipeline. O cartão de fonte deve destacar Upload, Transcrição e Link público como três entradas equivalentes. A escolha da fonte de transcrição fica agrupada com o idioma e apresenta o comportamento em linguagem humana.

Os cartões de ação devem ter estados hover/focus acessíveis, altura consistente e uma distinção clara entre ações auxiliares e o caminho principal “Cortar e ranquear”. Os resultados devem destacar ranking, score, status editorial e alertas de revisão antes de detalhes secundários.

## Critérios de aceite

A interface deve permanecer funcional em viewport desktop e em telas estreitas, manter contraste legível, não esconder botões críticos, preservar IDs e handlers existentes e não introduzir dependências externas novas. Toda mudança será validada por compilação, teste automatizado, sintaxe JavaScript e inspeção visual local.
