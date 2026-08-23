# Verificação visual do intervalo — 2026-08-20

A interface local da 6.16 carregou em `http://127.0.0.1:3001` e exibiu o modal de execução com o novo card `Processar apenas um trecho`. A viewport de notebook mostrou os campos `Início` e `Fim`, o chip `Fonte inteira`, a explicação de que a fonte original permanece intacta e a aceitação de segundos, `mm:ss` e `hh:mm:ss`.

O modal mantém a hierarquia visual do branch de referência: cabeçalho com ícone, superfície escura com destaque dourado, controles agrupados, ação primária destacada e cancelamento separado. A seção de métricas observadas já possui o painel recolhível da referência (`btnTogglePerformanceMetrics`/`performanceMetricsBody`), portanto não foi duplicada nem alterada funcionalmente.

O teste foi somente visual/DOM: nenhum arquivo foi processado, nenhum job foi iniciado e nenhuma fonte externa foi usada. O servidor local temporário foi iniciado apenas para a verificação e deve ser encerrado ao final do ciclo.
