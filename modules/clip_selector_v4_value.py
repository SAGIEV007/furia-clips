"""
V4 Value improvements - value avg 52-56 precisa 60+

Value = insight, dado, história útil, bastidor, tese forte
Atualmente: 52-56 avg, precisa 60+
Solução: dar bônus maior para storytelling, dados concretos, tese forte, bastidor
"""

path = "modules/clip_selector.py"
content = open(path, encoding="utf-8").read()

old_value_bonus = """        # Payoff bonus - se tem payoff forte
        try:
            payoff_data = self._detect_payoff_strength(original_text)
            if payoff_data[\"normalized\"] >= 60:
                bonus_v2 += 6
            elif payoff_data[\"normalized\"] >= 40:
                bonus_v2 += 3
        except:
            pass"""

new_value_bonus = """        # Payoff bonus - se tem payoff forte - V4 aumentado
        try:
            payoff_data = self._detect_payoff_strength(original_text)
            if payoff_data[\"normalized\"] >= 80:
                bonus_v2 += 10
            elif payoff_data[\"normalized\"] >= 60:
                bonus_v2 += 8
            elif payoff_data[\"normalized\"] >= 40:
                bonus_v2 += 4
        except:
            pass
        
        # Value bonus - storytelling, dados, bastidor, tese forte - V4 novo
        try:
            lower = text
            value_bonus = 0
            # Dados concretos
            import re as re_local
            if re_local.search(r'\\b\\d+[%]?\\b', lower) or re_local.search(r'\\b\\d+\\s*(mil|milhão|bilhão)\\b', lower):
                value_bonus += 6
            # Storytelling / bastidor
            if any(w in lower for w in [\"vou contar\", \"bastidor\", \"ontem\", \"quando eu\", \"eu vi\", \"aconteceu\", \"vou te contar um segredo\", \"ninguém te conta\"]):
                value_bonus += 8
            # Tese forte
            if any(w in lower for w in [\"problema é\", \"solução é\", \"por isso\", \"é simples\", \"na verdade\", \"o que ninguém te conta\", \"a verdade é\"]):
                value_bonus += 5
            # Polêmica / confronto
            if any(w in lower for w in [\"absurdo\", \"vergonha\", \"mentira\", \"corrupto\", \"escândalo\", \"porcaria\"]):
                value_bonus += 4
            # História pessoal
            if any(w in lower for w in [\"eu vim da periferia\", \"eu sei o que é\", \"quando eu era\", \"eu já passei\"]):
                value_bonus += 7
            
            bonus_v2 += min(15, value_bonus)
        except:
            pass"""

if old_value_bonus in content:
    content = content.replace(old_value_bonus, new_value_bonus)
    open(path, "w", encoding="utf-8").write(content)
    print("OK V4: value bonus + payoff aumentado, storytelling/dados/tese/bastidor")
else:
    print("OLD VALUE BONUS NOT FOUND")
    # try find
    idx = content.find("Payoff bonus")
    print(content[idx-100:idx+1000])

