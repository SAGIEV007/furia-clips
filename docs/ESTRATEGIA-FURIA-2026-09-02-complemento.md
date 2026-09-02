# Estratégia do Furia — complemento (2026-09-02)

> Complemento ao `docs/ESTRATEGIA-FURIA-2026-09-02.md`.
> Registra minha análise baseada em como eu estava operando na prática —
> não só no que o documento leu.

---

## 1. Diagnóstico das conversas que você não iniciou

Causa: **múltiplo cron no mesmo profile `mbl`**, rodando em sequência:
- `furia-autonomous-cycle` — de hora em hora
- `hermes-research-cycle` — de 30 em 30 minutos
- `vigia-credito-opus` — de 2 em 2 horas

Quando o provedor grátis caiu hoje, os 3 entraram em loop de erro. Cada erro
vira notificação no WhatsApp. Quando o Opus voltou, eles retomaram e começaram
a gerar respostas.

**Sim, consumiu créditos do Opus.**

Os perfis `escriba`, `auditor`, `pesquisador`, `cortador` estão parados —
zero sessões recentes. Todo o tráfego está no `mbl`.

---

## 2. O que eu acrescentaria sobre agentes

### Regra que falta

> **Modelo grátis prepara e confere. Modelo grátis não decide.**

Decidir o que é um corte bom, onde a borda entra, o que vai para a tela —
é caro, e um erro aqui custa uma tarde de trabalho.

### O que não funciona

- 5 profiles separados — os perfis extras estão vazios. Não adianta ter 5
  profiles se o trabalho todo acontece no `mbl`.
- Delegar para modelo grátis — caiu hoje, consumiu tempo, e quando o Opus
  voltou os crons dispararam em massa.
- Ciclos autônomos sem trava — o incidente das 21:05 prova que agente
  autônomo apaga trabalho mesmo com proibição em texto.

### O que funciona

**Um profile só (`mbl`), com regra de parada.** Toda vez que um agente for
despachado, ele precisa de:
1. Um arquivo de entrada no disco (caminho fixo, não prompt longo)
2. Um arquivo de saída no disco (caminho fixo, não "terminei")
3. Um teste que valida o resultado

**Opus para decisão e código. Modelo grátis só para conferência.** Quando o
provedor voltar:
- Opus: decide o que é corte bom, escreve código, escolhe branch
- Grátis: roda suíte, mede números, compara diffs, procura strings em arquivos
- Nunca grátis decide algo que não seja verificável em 60s

**Cron zero enquanto você não está em casa.** Os 3 crons foram desativados na
prática hoje. Só religar quando você autorizar.

---

## 3. Skills que eu implementaria primeiro

| Skill | Impede | Como |
|---|---|---|
| `furia-verdade` | Aceitar branch por relatório. | Roda suíte em cópia descartável, devolve número cru. |
| `furia-corte-a-corte` | Achar que melhorou sem prova. | `bench_contexto.py` como gate obrigatório antes de qualquer mudança no motor. |
| `furia-registro` | Registro livre virar log ilegível. | Ciclo no Obsidian na estrutura fixa: Norte, Estado, Decisões, Defeitos, Ciclos, Material, Inbox. |

---

## 4. Modificações que eu faria no plano do Claude

### 4.1 A escolha do tronco

O documento diz `claude/repo-access-commits-imgjmk` — zero testes quebrados,
tem tudo. Mas a `furia-sync-portable` tem peças que o tronco não tem
(`chub_mcp.py`, `fronteira_assunto.py`, `youtube_importer.py`).

A colheita tem que ser **antes** da aposentadoria, com ordem e teste de
regressão.

### 4.2 A parte de agentes

O documento descreve os papéis mas não diz como implementar no Hermes. Eu
acrescentaria:
- Perfil único (`mbl`), sem perfis extras
- Crons desligados por padrão, religados só com autorização
- Skills implementadas como módulos Python, não apenas como conceito
- Regra de commit: todo trabalho significativo commitado no mesmo ciclo

### 4.3 O plano de execução

O documento diz "só começa o próximo quando a suíte estiver verde na sua
máquina" — mas não diz como medir "verde" de forma confiável. Eu acrescentaria
o `bench_contexto.py` como gate obrigatório antes de qualquer mudança no motor
de corte.

---

## 5. Lição do dia

O estudo do Claude é bom como **diagnóstico de repositório**. Ele acerta onde a
fragmentação veio, acerta as leis que faltam, acerta a regra de modelo grátis.

Mas ele não sabe como eu estava operando na prática: os crons disparando sem
parar, os agentes consumindo crédito sem entregar, o provedor grátis caindo, o
cron apagando trabalho no meio da sessão.

**A estratégia que funciona é a que sobrevive a essas falhas — não a que
funciona quando tudo está no lugar.**
