"""
V3 Hook improvements - hook avg 27-32 precisa ir para 60+

Análise: hook detection melhorou 0->40-96 para Renan direct, mas hook avg nos clips ainda 27-32
Porque? Clips são construídos a partir de blocos com score alto mas que podem não ter hook forte no início
Solução: no _build_clips_from_scored_blocks, ordenar por (viral_score + hook_strength*0.5 + context*10) e priorizar blocos com hook forte como início

Também: melhorar synthetic generator para mais hooks, e NLP scoring para dar mais peso hook
"""

import re

path = "modules/clip_selector.py"
content = open(path, encoding="utf-8").read()

# Melhoria: clip building prioriza hook e context
old_build_sort = """        sorted_by_score = sorted(enumerate(scored_blocks), key=lambda x: x[1][1], reverse=True)"""

new_build_sort = """        # V3: Ordena por score + hook + context + coice para priorizar qualidade
        def _enhanced_sort_key(item):
            idx, (block, score) = item
            # Calcula hook e context bonus para ordenação
            try:
                hook_data = self._detect_hook_strength(block.get("text", ""), True)
                hook_bonus = hook_data["normalized"] * 0.3
            except:
                hook_bonus = 0
            try:
                flags = self._editorial_flags(block.get("text", ""), block)
                context_bonus = 15 if flags.get("context_complete") else (8 if not flags.get("starts_mid_sentence") else 0)
                qa_bonus = 10 if flags.get("qa_bridge") else 0
            except:
                context_bonus = 0
                qa_bonus = 0
            # Score final com bônus
            enhanced_score = score + hook_bonus + context_bonus + qa_bonus
            return enhanced_score
        
        sorted_by_score = sorted(enumerate(scored_blocks), key=_enhanced_sort_key, reverse=True)"""

if old_build_sort in content:
    content = content.replace(old_build_sort, new_build_sort)
    open(path, "w", encoding="utf-8").write(content)
    print("OK V3: clip building prioriza hook+context+qa_bridge")
else:
    print("OLD BUILD SORT NOT FOUND")

# Melhoria 2: Aumentar bônus hook no NLP scoring
path2 = "modules/clip_selector.py"
content2 = open(path2, encoding="utf-8").read()

old_hook_bonus = """        # V2 BONUSES - Hook/Context/Coice/Payoff (baseado em 50 ciclos de calibração)
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
            pass"""

new_hook_bonus = """        # V2/V3 BONUSES - Hook/Context/Coice/Payoff (baseado em 50+ ciclos de calibração)
        bonus_v2 = 0
        
        # Hook bonus - se tem hook forte no início - V3 aumentado
        try:
            hook_data = self._detect_hook_strength(original_text, True)
            if hook_data[\"normalized\"] >= 80:
                bonus_v2 += 18
            elif hook_data[\"normalized\"] >= 60:
                bonus_v2 += 14
            elif hook_data[\"normalized\"] >= 40:
                bonus_v2 += 8
            elif hook_data[\"normalized\"] >= 20:
                bonus_v2 += 3
            # Renan direct bonus extra - V3 aumentado
            renan_direct_count = sum(1 for r in hook_data[\"reasons\"] if r.startswith(\"renan_\"))
            if renan_direct_count > 0:
                bonus_v2 += 6 + renan_direct_count * 2
        except:
            pass"""

if old_hook_bonus in content2:
    content2 = content2.replace(old_hook_bonus, new_hook_bonus)
    open(path2, "w", encoding="utf-8").write(content2)
    print("OK V3: hook bonus aumentado 12->18 e Renan direct 5->6+count*2")
else:
    print("OLD HOOK BONUS NOT FOUND")

