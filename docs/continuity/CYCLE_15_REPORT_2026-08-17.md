# Relatório do ciclo 15 — Prompt operacional Chub→cortes

**Data:** 2026-08-17
**Versão documental:** 2.5
**Branch:** `manus/rebuild-opus-parity`
**Commit de publicação:** `8592227` — `docs: adicionar prompt operacional Chub para execução (2.5)`
**Natureza:** criação de prompt operacional e atualização das entradas de continuidade; nenhuma ponte funcional Chub→cortes foi implementada nesta rodada.

## 1. Objetivo

Criar um prompt copiável para orientar uma IA que receba o repositório Furia Clips e precise executar a próxima etapa real do projeto: fazer o Campaign Hub alimentar a seleção e a geração de propostas de cortes Renan Santos/MBL precisos, completos, contextualizados e auditáveis.

## 2. Documento criado

Foi criado [`PROMPT_EXECUCAO_CHUB_CORTES.md`](PROMPT_EXECUCAO_CHUB_CORTES.md). O prompt determina a ordem de leitura, o estado atual, o fluxo-alvo, os dados do Campaign Hub, as regras de locutor e contexto, a hipótese única da próxima rodada, os gates de aceitação, o ciclo de engenharia, a documentação obrigatória, o padrão de commits e o formato da entrega.

O documento insiste em uma distinção essencial: a sessão de blocos é diagnóstico, revisão e fallback; o produto final é uma proposta de corte guiada por contexto, alinhada à fonte local, expandida até a janela completa, validada e separada de um corte aprovado.

## 3. Entradas atualizadas

`START_HERE.md`, `AGENTS.md` e `README.md` agora encaminham diretamente ao prompt operacional, além do prompt mestre e do contrato `CHUB_INTEGRATION_CONTRACT.md`. A versão documental foi incrementada para `2.5`, e os testes de identidade do runtime foram alinhados a essa versão sem alteração de comportamento funcional.

## 4. Estado preservado

A última release funcional continua sendo a 2.2, com memória local do Campaign Hub, sessão de blocos, benchmark persistente e exportação individual. O benchmark b354 permanece em `0/3` highlights recuperados, com IoU médio `0.0`. A ponte funcional Chub→seeds→expansão→gates→propostas ainda precisa ser implementada.

## 5. Validação

A validação desta rodada confirmou **327 testes aprovados**, `compileall`, `node --check static/js/app.js` e `git diff --check`. O asset BlazeFace foi provisionado temporariamente com origem e SHA-256 conferidos e removido automaticamente ao final; não entrou no commit. A revisão dos arquivos não encontrou tokens, cookies, mídia grande, bancos locais, modelos binários ou dados privados.

## 6. Próxima hipótese

A próxima rodada deve ignorar melhorias estéticas na sessão de blocos e implementar a menor ponte funcional possível: consumir snapshot Chub autorizado, transformar highlight/bloco em seed, alinhar à timeline local, recuperar contexto da transcrição, expandir a janela, aplicar gates e produzir uma proposta auditável. O caso b354 deve ser comparado ao baseline de sete candidatos com métricas antes/depois.
