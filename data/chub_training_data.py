"""Training data extracted from Chub for Furia clip selector.

This file contains real patterns from Renan Santos Instagram clips
(@renansantosmbl and @renansantosreserva/@renanvote14)
with actual engagement ratios from Chub MCP.

DO NOT use as volume metric - only for pattern/weight training.
"""

# Hook performance based on real Chub data
# Source: chub_top_posts metric=ratio, 2026-08-29
HOOK_PERFORMANCE = {
    # @renansantosreserva / @renanvote14 (legacy)
    "desafio-ao-espectador": {"max_ratio": 4450.0, "count": 1, "source": "reserva"},
    "acusacao-direta": {"max_ratio": 679.0, "count": 2, "source": "reserva"},
    "outro": {"max_ratio": 623.0, "count": 1, "source": "reserva"},
    "tese-provocativa": {"max_ratio": 556.0, "count": 2, "source": "reserva"},
    "curiosity-gap": {"max_ratio": 352.0, "count": 1, "source": "reserva"},
    "revelacao-de-local": {"max_ratio": 351.0, "count": 1, "source": "reserva"},
    
    # @renansantosmbl (main)
    "revelacao-de-local": {"max_ratio": 146.9, "count": 1, "source": "main"},
    "news-peg": {"max_ratio": 104.5, "count": 1, "source": "main"},
    "desafio-ao-espectador": {"max_ratio": 99.8, "count": 1, "source": "main"},
    "acusacao-direta": {"max_ratio": 63.6, "count": 1, "source": "main"},
    "tese-provocativa": {"max_ratio": 76.3, "count": 3, "source": "main"},
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
]

# Content themes that perform well
THEME_PERFORMANCE = {
    "crime-organizado": {"avg_ratio": 99.8, "source": "main"},
    "seguranca-publica": {"avg_ratio": 99.8, "source": "main"},
    "saneamento-moradia": {"avg_ratio": 104.5, "source": "main"},
    "propriedade-invasoes": {"avg_ratio": 104.5, "source": "main"},
    "eleicoes-2026": {"avg_ratio": 298.0, "source": "reserva"},
    "partido-missao": {"avg_ratio": 556.0, "source": "reserva"},
    "bomba-atomica": {"avg_ratio": 556.0, "source": "reserva"},
    "centrao": {"avg_ratio": 373.0, "source": "reserva"},
    "comeback": {"avg_ratio": 352.0, "source": "reserva"},
    "escandalo-financeiro": {"avg_ratio": 351.0, "source": "reserva"},
}

# Caption patterns
CAPTION_PATTERNS = [
    "Hashtags: #RenanSantos #mbl #PartidoMissao #Eleições2026",
    "Hook na primeira linha",
    "Call-to-action implícito (pergunta/desafio)",
    "Emojis estratégicos (🤔)",
]

# Hook multipliers derived from Chub engagement data
# Used by modules.clip_selector for viral_score weighting
CHUB_HOOK_MULTIPLIERS = {
    "desafio-ao-espectador": 1.50,
    "acusacao-direta": 1.35,
    "tese-provocativa": 1.30,
    "revelacao-de-local": 1.25,
    "news-peg": 1.20,
    "outro": 1.10,
    "curiosity-gap": 1.05,
}
