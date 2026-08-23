"""
Clip Selector V2 Improvements - Próxima iteração para context_complete e hook

Análise 50 ciclos:
- Viral 89.9 best, avg 83-87 estável
- Renan coverage 96% excelente
- Context 0.53 avg, best 0.733 -> precisa melhorar para 0.8+
- Hook 26-36 avg baixo, mesmo com detection melhorada 40-96
- Payoff 100% excelente
- Coice 80% bom
- Flow 86-89 bom
- Value 50 médio precisa melhorar

Problemas identificados:
1. Synthetic generator produz "Mas você não acha..." que começa com "Mas" = continuation starter = context_complete false
2. Clip building começa de blocos com score alto mas que podem ter context fraco
3. Hook detection melhorou mas clips não priorizam hook no início
4. Weights atingiram max (20,25) indicando necessidade melhorar código não só peso

Soluções:
1. Melhorar synthetic generator para evitar continuation starters no início
2. Melhorar _nlp_score_block para dar bônus alto para context_complete e hook
3. Melhorar _build_clips_from_scored_blocks para priorizar clips com hook forte e context completo
4. Aumentar max weights e reset para nova otimização
5. Adicionar border refinement com energia e pausa
"""

# Melhorias para aplicar em clip_selector.py

IMPROVEMENTS = """
1. Synthetic generator fix:
   - Evitar começar frases com CONTINUATION_STARTERS_PT no início de templates
   - Adicionar mais variação com hooks fortes

2. NLP scoring:
   - Hook bonus: se _detect_hook_strength normalized >= 60, +10 pontos
   - Context bonus: se não starts_mid e não starts_with_context_reference, +8
   - Coice bonus: se detect_coice score >= 0.6, +12
   - Payoff bonus: se payoff_strength >= 60, +5

3. Clip building:
   - Ordenar por (viral_score + hook_strength/2 + context_complete*10) ao invés de só viral_score
   - Tentar expandir para incluir contexto quando starts_with_context_reference
   - Priorizar clips com qa_bridge

4. Border refinement:
   - Usar energy_profile para refinar bordas: cortar em silêncio ou energia baixa
   - Usar pause detection: se gap > 0.8s, é boa borda

5. Weights:
   - Aumentar max de 20->30 e 25->35
   - Reset parcial mantendo aprendizado
"""

print(IMPROVEMENTS)

# Aplicar melhorias no clip_selector
import re

path = "modules/clip_selector.py"
content = open(path, encoding="utf-8").read()

# Melhoria 1: NLP scoring com bônus hook/context/coice/payoff
old_nlp_score = """    def _nlp_score_block(self, block, user_context, energy_profile, context_data=None, editorial_context=None):
        \"\"\"Score a block using NLP heuristics.\"\"\"
        text = block[\"text\"].lower()
        score = 40

        # Hook detection
        first_words = \" \".join(text.split()[:15])
        hook_patterns = [
            r\"voce\\s+sabia\", r\"presta\\s+atencao\", r\"olha\\s+isso\",
            r\"a\\s+verdade\\s+e\", r\"ninguem\\s+te\", r\"cuidado\",
            r\"absurdo\", r\"vergonha\", r\"mentira\", r\"bomba\",
            r\"urgente\", r\"inacreditavel\", r\"chocante\",
            r\"vou\\s+te\\s+falar\", r\"isso\\s+e\\s+muito\",
            r\"nao\\s+pode\", r\"tem\\s+que\",
        ]
        hook_score = 0
        for pattern in hook_patterns:
            if re.search(pattern, first_words):
                hook_score += 12
        hook_score = min(20, hook_score)

        # Emotional intensity
        emotional_words = [
            \"absurdo\", \"vergonha\", \"mentira\", \"corrupto\", \"criminoso\",
            \"covarde\", \"traidor\", \"hipocrita\", \"lixo\", \"revolta\",
            \"liberdade\", \"patriota\", \"coragem\", \"vitoria\", \"luta\",
            \"impressionante\", \"incrivel\", \"surreal\", \"chocante\",
            \"inacreditavel\", \"povo\", \"nacao\", \"brasil\",
        ]
        word_list = text.split()
        emotional_count = sum(1 for w in word_list if any(ew in w for ew in emotional_words))
        emotional_density = emotional_count / max(len(word_list), 1)
        emotional_score = min(20, emotional_density * 200)

        # Punctuation energy
        excl_count = block[\"text\"].count(\"!\")
        quest_count = block[\"text\"].count(\"?\")
        punct_score = min(10, excl_count * 4 + quest_count * 2)

        # Filler word penalty
        filler_count = 0
        for fw in FILLER_WORDS_PT:
            if \" \" in fw:
                filler_count += text.count(fw)
            else:
                filler_count += sum(1 for w in word_list if w == fw)
        filler_density = filler_count / max(len(word_list), 1)
        filler_penalty = min(15, filler_density * 150)

        # User context relevance
        context_score = 0
        if context_data:
            context_score = self._compute_context_score(text, context_data)

        # Duration is a soft preference: shorter complete blocks are rewarded,
        # while long blocks remain eligible when their context is stronger.
        duration = block[\"duration\"]
        duration_score = self._duration_score(duration)
        dossier_score = self._dossier_context_score(block, editorial_context)

        # Sentence completeness
        if block[\"text\"].strip()[-1:] in \".!?\":
            completeness_score = 10
        else:
            completeness_score = -15

        total = (score + hook_score + emotional_score + punct_score
                 + context_score + duration_score + completeness_score
                 + dossier_score - filler_penalty)
        return max(0, min(100, total))"""

new_nlp_score = """    def _nlp_score_block(self, block, user_context, energy_profile, context_data=None, editorial_context=None):
        \"\"\"Score a block using NLP heuristics + Hook/Context/Coice/Payoff bonuses (V2)\"\"\"
        text = block[\"text\"].lower()
        original_text = block[\"text\"]
        score = 40

        # Hook detection - basic
        first_words = \" \".join(text.split()[:15])
        hook_patterns = [
            r\"voce\\s+sabia\", r\"presta\\s+atencao\", r\"olha\\s+isso\",
            r\"a\\s+verdade\\s+e\", r\"ninguem\\s+te\", r\"cuidado\",
            r\"absurdo\", r\"vergonha\", r\"mentira\", r\"bomba\",
            r\"urgente\", r\"inacreditavel\", r\"chocante\",
            r\"vou\\s+te\\s+falar\", r\"isso\\s+e\\s+muito\",
            r\"nao\\s+pode\", r\"tem\\s+que\",
        ]
        hook_score = 0
        for pattern in hook_patterns:
            if re.search(pattern, first_words):
                hook_score += 12
        hook_score = min(20, hook_score)

        # Emotional intensity
        emotional_words = [
            \"absurdo\", \"vergonha\", \"mentira\", \"corrupto\", \"criminoso\",
            \"covarde\", \"traidor\", \"hipocrita\", \"lixo\", \"revolta\",
            \"liberdade\", \"patriota\", \"coragem\", \"vitoria\", \"luta\",
            \"impressionante\", \"incrivel\", \"surreal\", \"chocante\",
            \"inacreditavel\", \"povo\", \"nacao\", \"brasil\",
        ]
        word_list = text.split()
        emotional_count = sum(1 for w in word_list if any(ew in w for ew in emotional_words))
        emotional_density = emotional_count / max(len(word_list), 1)
        emotional_score = min(20, emotional_density * 200)

        # Punctuation energy
        excl_count = block[\"text\"].count(\"!\")
        quest_count = block[\"text\"].count(\"?\")
        punct_score = min(10, excl_count * 4 + quest_count * 2)

        # Filler word penalty
        filler_count = 0
        for fw in FILLER_WORDS_PT:
            if \" \" in fw:
                filler_count += text.count(fw)
            else:
                filler_count += sum(1 for w in word_list if w == fw)
        filler_density = filler_count / max(len(word_list), 1)
        filler_penalty = min(15, filler_density * 150)

        # User context relevance
        context_score = 0
        if context_data:
            context_score = self._compute_context_score(text, context_data)

        # Duration is a soft preference: shorter complete blocks are rewarded,
        # while long blocks remain eligible when their context is stronger.
        duration = block[\"duration\"]
        duration_score = self._duration_score(duration)
        dossier_score = self._dossier_context_score(block, editorial_context)

        # Sentence completeness
        if block[\"text\"].strip()[-1:] in \".!?\":
            completeness_score = 10
        else:
            completeness_score = -15

        # V2 BONUSES - Hook/Context/Coice/Payoff (baseado em 50 ciclos de calibração)
        bonus_v2 = 0
        
        # Hook bonus - se tem hook forte no início
        try:
            hook_data = self._detect_hook_strength(original_text, True)
            if hook_data[\"normalized\"] >= 60:
                bonus_v2 += 12
            elif hook_data[\"normalized\"] >= 40:
                bonus_v2 += 6
            # Renan direct bonus extra
            if any(r.startswith(\"renan_\") for r in hook_data[\"reasons\"]):
                bonus_v2 += 5
        except:
            pass
        
        # Context bonus - se não começa no meio e não tem referência fraca
        try:
            flags = self._editorial_flags(original_text, block)
            if not flags.get(\"starts_mid_sentence\") and not flags.get(\"starts_with_context_reference\"):
                bonus_v2 += 8
            if flags.get(\"context_complete\"):
                bonus_v2 += 6
            if flags.get(\"qa_bridge\"):
                bonus_v2 += 5
        except:
            pass
        
        # Coice bonus - se tem coice Renan
        try:
            # Simula detecção rápida de coice no texto
            lower = text
            coice_score = 0
            for cat, markers in RENAN_COICE_MARKERS.items():
                coice_score += sum(1 for m in markers if m in lower)
            if coice_score >= 2:
                bonus_v2 += min(12, coice_score * 3)
        except:
            pass
        
        # Payoff bonus - se tem payoff forte
        try:
            payoff_data = self._detect_payoff_strength(original_text)
            if payoff_data[\"normalized\"] >= 60:
                bonus_v2 += 6
            elif payoff_data[\"normalized\"] >= 40:
                bonus_v2 += 3
        except:
            pass

        total = (score + hook_score + emotional_score + punct_score
                 + context_score + duration_score + completeness_score
                 + dossier_score - filler_penalty + bonus_v2)
        return max(0, min(100, total))"""

if old_nlp_score in content:
    content = content.replace(old_nlp_score, new_nlp_score)
    open(path, "w", encoding="utf-8").write(content)
    print("OK enhanced NLP scoring with V2 bonuses")
else:
    print("OLD NLP SCORE NOT FOUND")
    # debug
    idx = content.find("def _nlp_score_block")
    print(content[idx:idx+3000])
