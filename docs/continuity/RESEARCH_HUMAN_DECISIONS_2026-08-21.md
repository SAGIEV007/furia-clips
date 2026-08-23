# Pesquisa — decisões humanas para hard negatives (2026-08-21)

## Decisão
A próxima melhoria deve permitir importar decisões humanas reais para o benchmark `hard-negative-v1` sem sobrescrever o registro original. O benchmark deve manter histórico de revisões, distinguir ausência de decisão de rejeição, e registrar conflitos/adjudicação separadamente.

## Evidência técnica
A literatura de temporal moment localization trata a localização de início e fim em vídeo como uma tarefa sujeita a ambiguidade e subjetividade. A consequência prática para o Furia Clips é não transformar uma única borda humana em verdade absoluta: o sistema deve armazenar decisão, anotador, instante da decisão, origem e eventual adjudicação. Métricas de borda devem aceitar tolerância e métricas editoriais devem continuar separadas de métricas de cobertura.

## Contrato proposto para `hard-negative-v1`

- `decision`: somente `approved`, `rejected`, `needs_review` ou `unlabeled`.
- `decision_history`: lista append-only de eventos de decisão, sem texto integral da transcrição ou mídia.
- `annotator_id`: identificador pseudônimo ou rótulo local; nunca credencial.
- `source`: `manual_ui`, `imported_file`, `api` ou equivalente controlado.
- `decided_at`: timestamp ISO-8601 opcional.
- `adjudication`: opcional, com resultado e motivo curto, sem permitir apagar votos anteriores.
- conflito: duas decisões divergentes permanecem como conflito até adjudicação; não são convertidas automaticamente em aprovado/rejeitado.

## Fontes consultadas

1. Rodriguez-Opazo et al., *Proposal-free Temporal Moment Localization of a Natural-Language Query in Video using Guided Attention*, WACV 2020 / arXiv: https://arxiv.org/abs/1908.07236
2. Gao et al., *Detecting Moments and Highlights in Videos via Natural Language Queries*, NeurIPS 2021: https://proceedings.neurips.cc/paper_files/paper/2021/hash/62e0973455fd26eb03e91d5741a4a3bb-Abstract.html
3. Zhang et al., *Temporal Sentence Grounding in Videos: A Survey and Future Directions*, IEEE 2023: https://ieeexplore.ieee.org/abstract/document/10075491/

## Limite
Nenhuma alteração de peso ou calibração automática deve ser feita somente com esse contrato. Primeiro será preciso obter decisões humanas reais em fonte longa e medir before/after em um benchmark congelado.
