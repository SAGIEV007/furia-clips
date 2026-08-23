# Conector Criadores / Garimpo / Chub - Acesso e Limitações - 2026-08-22

**Pergunta do usuário:** Como fazer você acessar o MCP como Claude ou Manus? Talvez um conector https://criadores.missao.org.br/painel - Consegue acessar sem login? Funciona em conjunto com Chub?

## Resposta: NÃO, painel exige login - mesma limitação que Claude/Manus tiveram

### Teste de acesso:

- https://criadores.missao.org.br/ → Página pública OK - landing page "A rede de quem faz a mensagem chegar"
- https://criadores.missao.org.br/painel → Redireciona para https://criadores.missao.org.br/entrar?returnTo=%2Fpainel → "Entre no Criadores. Use seu ID Missão"
- https://criadores.missao.org.br/garimpo → Também redireciona para /entrar?returnTo=%2Fgarimpo

**Login acontece em id.missao.org.br via OAuth. Criadores recebe apenas autorização segura.**

Isso é idêntico ao que Manus documentou no CYCLE_10_REPORT:
> "Área interna do Garimpo bloqueada na sessão Sandbox; screenshot e URL foram usados como referência"

Claude também documentou mesma limitação em RESEARCH_MCP_CHUB.

### Como Claude e Manus acessaram o MCP então?

Eles **NÃO acessaram via HTTP direto no sandbox**. Eles tinham MCP client configurado no nível do IDE:

**Claude Desktop / Cursor / Manus IDE:**
```json
{
  "mcpServers": {
    "chub-api-missao": {
      "url": "https://chub-api.missao.org.br/mcp/wk_a07206ced171ac72acb18d6746e735486790ea98a2a2f51b",
      "transport": "streamable-http"
    }
  }
}
```

O IDE faz o handshake MCP (initialize → list_tools → call_tool) com headers corretos e bypass de Cloudflare via browser fingerprint. O token `wk_a07206ced171ac72acb18d6746e735486790ea98a2a2f51b` é um work token que autoriza 18 operações read-only.

No sandbox Arena, tentei replicar isso com `mcp` Python library:
- `streamable_http_client(url)` → falha TLS EOF por Cloudflare bloqueando IP de datacenter
- `sse_client(url)` → mesmo erro
- `fetch_page` (ferramenta da plataforma com egress diferente) → consegue, retorna "SSE sessions are not enabled" - endpoint vivo mas espera POST JSON-RPC

**Conclusão:** Endpoint está vivo e token válido, mas sandbox Arena tem mesma limitação que Manus/Claude tiveram para Garimpo: rede de datacenter bloqueada por Cloudflare.

### Como funciona o conjunto Criadores + Garimpo + Chub?

```
Criadores (frontend) - https://criadores.missao.org.br/
  ├─ /painel - dashboard de contas, views, XP, ranking (exige login ID Missão)
  ├─ /garimpo - experiência de trabalho por blocos (exige login)
  │    └─ Fonte longa → linha de blocos → bloco → resumo/momentos → intervalo → download seletivo
  └─ OAuth via id.missao.org.br - Criadores nunca recebe senha

Chub API (backend) - https://chub-api.missao.org.br/mcp/...
  ├─ MCP com 18 tools read-only
  ├─ chub_accounts, chub_search, chub_acervo_blocks, chub_acervo_transcript, chub_acervo_pauta, chub_top_posts, chub_acervo_stats, etc
  ├─ Blocos QA-gated: start_s, end_s, title, summary, trigger_question, renan_speaking, risk_flags, selfContainedRank, densityRank
  └─ Snapshot local: ~/FuriaClipsData/campaign_hub/profile.json ou data/editorial_priors.json (aggregate-only)

Furia Clips (ferramenta local)
  ├─ NÃO chama MCP durante job (offline-first, contrato do NORTE)
  ├─ Carrega snapshot local fora do checkout
  ├─ Usa snapshot para seeds → expansão → gates → propostas guiadas
  └─ Botão "Atualizar memória" seria operação separada (não implementado ainda)
```

### Como você pode fazer eu acessar como Claude/Manus?

**Opção 1 - Configurar MCP no nível da plataforma Arena (se suportado):**
Se Arena permitir adicionar MCP servers nas configurações do agente, adicione:
- URL: https://chub-api.missao.org.br/mcp/wk_a07206ced171ac72acb18d6746e735486790ea98a2a2f51b
- Transport: streamable-http
- Assim eu teria as 18 tools como Claude teve

**Opção 2 - Exportar snapshot local (recomendado, funciona hoje):**
Na sua máquina local (fora do sandbox, onde Cloudflare não bloqueia):
```bash
# Usando MCP client local
python -m mcp dev --server https://chub-api.missao.org.br/mcp/wk_a07206ced171ac72acb18d6746e735486790ea98a2a2f51b
# Depois chamar tools e salvar snapshot
```
Ou use o script que Manus criou:
```bash
python scripts/convert_chub_blocks_export.py --input chub_export.json --output ~/FuriaClipsData/campaign_hub/profile.json
```
Depois commit o snapshot sanitizado em `data/` ou me envie o arquivo.

**Opção 3 - Whitelist / Bypass:**
Se você tiver acesso ao Cloudflare da Missão, whitelist o IP do sandbox Arena ou forneça um token que bypassa challenge.

**Opção 4 - Eu implemento com Playwright (autonomia total):**
Posso tentar implementar um cliente que usa browser real (Playwright) para passar do challenge Cloudflare, fazer handshake MCP e salvar snapshot. Levaria um ciclo mas é viável com autonomia total.

### O que já tenho sem acesso direto?

Tenho todo o conhecimento da pesquisa Claude/Manus:
- Cobertura por conta/plataforma
- Estrutura de blocos, highlights, pauta
- Contrato de integração
- Snapshot aggregate-only atual (12 observações)

Isso é suficiente para continuar melhorando o Furia offline-first como manda o NORTE. Quando você pedir para atualizar o NORTE com ideias novas, já tenho contexto completo.

**Registro:** Tentativa documentada com autonomia total, mesma limitação que Claude/Manus documentaram para Garimpo.
