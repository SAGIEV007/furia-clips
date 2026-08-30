"""Training data extracted from Chub for Furia clip selector.

This file contains real patterns from Renan Santos Instagram clips
(@renansantosmbl and @renansantosreserva/@renanvote14)
with actual engagement ratios from Chub MCP.

DO NOT use as volume metric - only for pattern/weight training.
"""

# Hook performance based on real Chub data
# Source: chub_top_posts metric=ratio, 2026-08-29
# Merged from 50 top posts per profile
HOOK_PERFORMANCE = {
    "desafio-ao-espectador": {
        "max_ratio": 4450.0,
        "count": 3,
        "avg_ratio": 1523.93,
        "main": {"max_ratio": 99.79, "count": 1},
        "reserva": {"max_ratio": 4450.0, "count": 2},
    },
    "acusacao-direta": {
        "max_ratio": 679.0,
        "count": 13,
        "avg_ratio": 115.5,
        "main": {"max_ratio": 63.61, "count": 2},
        "reserva": {"max_ratio": 679.0, "count": 11},
    },
    "outro": {
        "max_ratio": 623.0,
        "count": 41,
        "avg_ratio": 50.3,
        "main": {"max_ratio": 99.23, "count": 33},
        "reserva": {"max_ratio": 623.0, "count": 8},
    },
    "tese-provocativa": {
        "max_ratio": 556.0,
        "count": 26,
        "avg_ratio": 98.06,
        "main": {"max_ratio": 76.25, "count": 6},
        "reserva": {"max_ratio": 556.0, "count": 20},
    },
    "curiosity-gap": {
        "max_ratio": 352.0,
        "count": 6,
        "avg_ratio": 82.69,
        "main": {"max_ratio": 41.7, "count": 2},
        "reserva": {"max_ratio": 352.0, "count": 4},
    },
    "revelacao-de-local": {
        "max_ratio": 351.0,
        "count": 4,
        "avg_ratio": 132.72,
        "main": {"max_ratio": 146.86, "count": 2},
        "reserva": {"max_ratio": 351.0, "count": 2},
    },
    "news-peg": {
        "max_ratio": 104.48,
        "count": 3,
        "avg_ratio": 45.19,
        "main": {"max_ratio": 104.48, "count": 2},
        "reserva": {"max_ratio": 10.0, "count": 1},
    },
    "callback": {
        "max_ratio": 47.07,
        "count": 4,
        "avg_ratio": 31.23,
        "main": {"max_ratio": 24.65, "count": 2},
        "reserva": {"max_ratio": 47.07, "count": 2},
    },
}

# Transcript patterns from top clips
# Source: chub_transcript tool, 2026-08-29
TRANSCRIPT_PATTERNS = [
    {
        "url": "https://www.instagram.com/reel/Db_4A6IDX1O/",
        "hook": "desafio-ao-espectador",
        "ratio": 4450.0,
        "duration_s": None,
        "structure": "comparative_contrast",
        "key_phrases": [
            "Enquanto o Renan tá",
            "o Flávio tá",
            "conhecendo essas regiões",
            "brincando de fazer videozinho",
        ],
        "pattern": "Enquanto X [ação positiva], Y [ação negativa/fraca]",
    },
    {
        "url": "https://www.instagram.com/reel/Db-zC7Hj8d1/",
        "hook": "acusacao-direta",
        "ratio": 679.0,
        "duration_s": None,
        "structure": "repetition_emphasis",
        "key_phrases": [
            "favelado com dinheiro",
            "Não seja um favelado de classe média",
        ],
        "pattern": "Repetição do mesmo phrase para impacto + fechamento com lição",
    },
    {
        "url": "https://www.instagram.com/reel/Db8wfUyFHiV/",
        "hook": "outro",
        "ratio": 623.0,
        "duration_s": None,
        "structure": "interview_reaction",
        "key_phrases": [
            "campanha decidiu declinar do convite",
            "comentários feitos pelo Pedro",
        ],
        "pattern": "Jornalista cita Renan entre aspas → Renan reage → payoff por contradição",
    },
    {
        "url": "https://www.instagram.com/reel/Db8tEDiD0eD/",
        "hook": "tese-provocativa",
        "ratio": 556.0,
        "duration_s": None,
        "structure": "conspiracy_narrative",
        "key_phrases": [
            "O sistema está tentando esconder",
            "estou menos conhecido agora",
        ],
        "pattern": "Framing de conspiracy + ironia + hashtag de campanha",
    },
    {
        "url": "https://www.instagram.com/reel/Db9PagNj1QQ/",
        "hook": "acusacao-direta",
        "ratio": 556.0,
        "duration_s": None,
        "structure": "quote_reaction",
        "key_phrases": [
            "Renan Santos afirma que o Brasil precisa ter sua própria Bomba Atômica",
            "jornalistas ficam chocado",
        ],
        "pattern": "Afirmação polêmica direta + reação de choque do jornalista",
    },
    {
        "url": "https://www.instagram.com/reel/Db5igt8mGe8/",
        "hook": "tese-provocativa",
        "ratio": 373.0,
        "duration_s": None,
        "structure": "problem_solution",
        "key_phrases": [
            "o centrão representa esse sistema",
            "problema sistêmico maior do que a esquerda",
        ],
        "pattern": "Problema estrutural (centrão) vs solução proposta",
    },
    {
        "url": "https://www.instagram.com/reel/Db-2Y0OFNtr/",
        "hook": "curiosity-gap",
        "ratio": 352.0,
        "duration_s": None,
        "structure": "personal_journey",
        "key_phrases": [
            "A Missão é inevitável",
            "estava no fundo do poço",
            "grande comeback",
        ],
        "pattern": "Virada pessoal + superação + identidade de missão",
    },
    {
        "url": "https://www.instagram.com/reel/Db8HTYzgTGZ/",
        "hook": "revelacao-de-local",
        "ratio": 351.0,
        "duration_s": None,
        "structure": "scandal_revelation",
        "key_phrases": [
            "escândalo do Banco Master",
            "se batizou agora na lagoinha",
            "clava forte da Lagoinha",
        ],
        "pattern": "Escândalo financeiro + conexão política + revelação de entidade",
    },
    {
        "url": "https://www.instagram.com/p/DOZcLOtEXqr/",
        "hook": "revelacao-de-local",
        "ratio": 146.86,
        "duration_s": 71,
        "structure": "narrative_opening",
        "key_phrases": [
            "Pérola Nepal",
            "Palácio Governamental",
            "revolução liderada por jovens",
        ],
        "pattern": "Abertura comparativa internacional + contexto político + revolução",
    },
    {
        "url": "https://www.instagram.com/p/DPOwX6fEeU7/",
        "hook": "news-peg",
        "ratio": 104.48,
        "duration_s": 151,
        "structure": "narrative_opening",
        "key_phrases": [
            "Tá viralizando agora",
            "favela que foi transformada",
            "refavelizada pelos moradores",
        ],
        "pattern": "News peg local + transformação comunitária + fechamento com frase de impacto",
    },
    {
        "url": "https://www.instagram.com/p/DUohmetkSxx/",
        "hook": "desafio-ao-espectador",
        "ratio": 99.79,
        "duration_s": 152,
        "structure": "direct_challenge",
        "key_phrases": [
            "Se você é mulher",
            "Eu me renão Santos",
            "pré-candidato à presidência",
        ],
        "pattern": "Desafio direto por identidade + apresentação + CTA político",
    },
]

# Content themes that perform well
# Source: chub_top_posts metric=ratio, 2026-08-29
THEME_PERFORMANCE = {
    "crime-organizado": {"avg_ratio": 99.79, "count": 1, "source": "main"},
    "seguranca-publica": {"avg_ratio": 70.74, "count": 2, "source": "main"},
    "saneamento-moradia": {"avg_ratio": 104.48, "count": 1, "source": "main"},
    "propriedade-invasoes": {"avg_ratio": 104.48, "count": 1, "source": "main"},
    "liberdade-expressao": {"avg_ratio": 67.9, "count": 1, "source": "main"},
    "censura-digital": {"avg_ratio": 67.9, "count": 1, "source": "main"},
    "debate-cultural": {"avg_ratio": 56.27, "count": 5, "source": "main"},
    "igrejas-pastores": {"avg_ratio": 55.02, "count": 1, "source": "main"},
    "impostos": {"avg_ratio": 35.18, "count": 1, "source": "main"},
    "corrupcao": {"avg_ratio": 33.82, "count": 3, "source": "main"},
    "lula-pt": {"avg_ratio": 49.39, "count": 2, "source": "reserva"},
    "gasto-publico": {"avg_ratio": 43.9, "count": 2, "source": "reserva"},
    "escandalo-investigacao": {"avg_ratio": 38.05, "count": 2, "source": "reserva"},
    "bolsonaro-direita": {"avg_ratio": 26.36, "count": 2, "source": "reserva"},
    "juventude": {"avg_ratio": 24.25, "count": 1, "source": "reserva"},
    "nordeste": {"avg_ratio": 24.25, "count": 1, "source": "reserva"},
    "congresso-centrao": {"avg_ratio": 24.19, "count": 1, "source": "reserva"},
    "eleicao-candidatura": {"avg_ratio": 23.54, "count": 4, "source": "reserva"},
    "agro": {"avg_ratio": 22.04, "count": 1, "source": "reserva"},
    "emprego-renda": {"avg_ratio": 22.04, "count": 1, "source": "reserva"},
    "exterior": {"avg_ratio": 20.47, "count": 1, "source": "reserva"},
    "stf-moraes": {"avg_ratio": 18.64, "count": 1, "source": "reserva"},
    "eleicoes-2026": {"avg_ratio": 298.0, "count": 1, "source": "reserva"},
    "partido-missao": {"avg_ratio": 556.0, "count": 1, "source": "reserva"},
    "bomba-atomica": {"avg_ratio": 556.0, "count": 1, "source": "reserva"},
    "centrao": {"avg_ratio": 373.0, "count": 1, "source": "reserva"},
    "comeback": {"avg_ratio": 352.0, "count": 1, "source": "reserva"},
    "escandalo-financeiro": {"avg_ratio": 351.0, "count": 1, "source": "reserva"},
}

# Caption patterns
CAPTION_PATTERNS = [
    "Hashtags: #RenanSantos #mbl #PartidoMissao #Eleições2026",
    "Hook na primeira linha",
    "Call-to-action implícito (pergunta/desafio)",
    "Emojis estratégicos (🤔)",
]

# Hook multipliers derived from Chub engagement data
# Based on 65 real posts from @renansantosmbl + @renansantosreserva
# Calculated using median ratio / baseline median (32.51x)
# Updated: 2026-08-30
CHUB_HOOK_MULTIPLIERS = {
    "desafio-ao-espectador": 3.07,  # median=99.79x, n=3
    "acusacao-direta": 3.55,        # mean=115.50x, n=13 (high count)
    "tese-provocativa": 3.01,       # mean=98.06x, n=26 (highest count)
    "revelacao-de-local": 2.60,     # median=84.45x, n=4
    "outro": 1.04,                  # median=33.93x, n=6
    "curiosity-gap": 0.96,          # median=31.08x, n=6
    "callback": 0.83,               # median=26.82x, n=4
    "news-peg": 0.65,               # median=21.09x, n=3
}
