"""Constrói data/espelho_chub.json a partir das medições feitas no CHUB.

As linhas abaixo vieram de consultas ao banco da campanha em 25/08/2026. Ficam
escritas aqui, e não recalculadas, porque a máquina do editor não alcança o
servidor — o espelho tem que chegar pronto junto com o programa, e ser
atualizável depois pelo chub.bat.
"""
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[0]

# ── ganchos: conta, plataforma, família, n, mediana, p90 ──────────────────────
GANCHOS = [
 ("@partidomissao","facebook","tese-provocativa",29,1.050,3.546),
 ("@partidomissao","facebook","outro",4,1.058,4.121),
 ("@partidomissao","facebook","acusacao-direta",3,2.238,19.217),
 ("@partidomissao","facebook","curiosity-gap",3,1.222,1.693),
 ("@partidomissao","instagram","tese-provocativa",24,1.000,3.234),
 ("@partidomissao","instagram","acusacao-direta",9,0.818,1.393),
 ("@partidomissao","instagram","curiosity-gap",5,0.539,2.216),
 ("@partidomissao","instagram","outro",5,2.240,3.461),
 ("@partidomissao","instagram","desafio-ao-espectador",3,2.852,4.696),
 ("@renansantosmbl","facebook","tese-provocativa",347,1.000,3.314),
 ("@renansantosmbl","facebook","acusacao-direta",246,1.093,3.597),
 ("@renansantosmbl","facebook","curiosity-gap",142,0.980,3.228),
 ("@renansantosmbl","facebook","revelacao-de-local",64,1.023,3.051),
 ("@renansantosmbl","facebook","desafio-ao-espectador",54,0.991,2.496),
 ("@renansantosmbl","facebook","news-peg",29,0.968,7.355),
 ("@renansantosmbl","facebook","callback",24,1.086,7.123),
 ("@renansantosmbl","facebook","outro",24,0.674,1.362),
 ("@renansantosmbl","facebook","numero-choque",9,0.571,2.261),
 ("@renansantosmbl","facebook","contraste-regional",3,1.241,1.492),
 ("@renansantosmbl","instagram","tese-provocativa",482,0.980,2.222),
 ("@renansantosmbl","instagram","acusacao-direta",298,1.059,2.459),
 ("@renansantosmbl","instagram","curiosity-gap",192,1.000,2.471),
 ("@renansantosmbl","instagram","revelacao-de-local",82,0.992,2.021),
 ("@renansantosmbl","instagram","desafio-ao-espectador",65,0.916,2.131),
 ("@renansantosmbl","instagram","news-peg",47,1.403,3.178),
 ("@renansantosmbl","instagram","outro",43,0.893,1.722),
 ("@renansantosmbl","instagram","callback",28,1.215,2.791),
 ("@renansantosmbl","instagram","numero-choque",14,0.985,1.701),
 ("@renansantosmbl","instagram","contraste-regional",4,1.192,1.355),
 ("@renansantosmbl","tiktok","tese-provocativa",336,1.000,4.545),
 ("@renansantosmbl","tiktok","acusacao-direta",222,0.974,3.969),
 ("@renansantosmbl","tiktok","curiosity-gap",132,1.000,5.259),
 ("@renansantosmbl","tiktok","revelacao-de-local",64,1.332,4.928),
 ("@renansantosmbl","tiktok","desafio-ao-espectador",46,1.110,3.644),
 ("@renansantosmbl","tiktok","news-peg",36,1.782,3.786),
 ("@renansantosmbl","tiktok","outro",29,0.694,1.144),
 ("@renansantosmbl","tiktok","callback",26,1.398,8.835),
 ("@renansantosmbl","tiktok","numero-choque",11,1.000,1.918),
 ("@renansantosmbl","tiktok","contraste-regional",4,1.652,3.043),
 ("@renansantosreserva","facebook","tese-provocativa",66,0.988,5.710),
 ("@renansantosreserva","facebook","acusacao-direta",29,0.538,12.290),
 ("@renansantosreserva","facebook","outro",13,0.719,25.331),
 ("@renansantosreserva","facebook","curiosity-gap",9,0.120,1.539),
 ("@renansantosreserva","facebook","desafio-ao-espectador",5,0.209,24.934),
 ("@renansantosreserva","facebook","news-peg",4,1.293,1.458),
 ("@renansantosreserva","facebook","callback",4,0.200,28.740),
 ("@renansantosreserva","facebook","revelacao-de-local",3,0.341,1.866),
 ("@renansantosreserva","instagram","tese-provocativa",150,1.000,6.178),
 ("@renansantosreserva","instagram","acusacao-direta",58,0.986,5.546),
 ("@renansantosreserva","instagram","outro",29,0.901,6.965),
 ("@renansantosreserva","instagram","curiosity-gap",21,1.222,4.981),
 ("@renansantosreserva","instagram","news-peg",10,2.186,6.984),
 ("@renansantosreserva","instagram","desafio-ao-espectador",10,0.699,3.827),
 ("@renansantosreserva","instagram","revelacao-de-local",10,0.860,8.108),
 ("@renansantosreserva","instagram","callback",6,1.833,3.738),
]

# ── temas: conta, slug, dimensão, n, mediana ─────────────────────────────────
TEMAS = [
 ("@partidomissao","corrupcao","issue",14,1.509),
 ("@partidomissao","campanha-e-eleicoes","app_theme",39,1.132),
 ("@partidomissao","eleicao-candidatura","event",26,1.113),
 ("@partidomissao","corrupcao-e-escandalos","app_theme",10,1.017),
 ("@partidomissao","crime-organizado","issue",19,1.000),
 ("@partidomissao","gasto-publico","issue",12,1.000),
 ("@partidomissao","missao","app_theme",13,1.000),
 ("@partidomissao","seguranca-publica","issue",18,0.980),
 ("@partidomissao","crime-e-faccoes","app_theme",17,0.980),
 ("@partidomissao","justica-e-instituicoes","app_theme",8,0.963),
 ("@renansantosmbl","saude","issue",12,2.109),
 ("@renansantosmbl","uf-sp","app_uf",24,2.068),
 ("@renansantosmbl","economia-e-trabalho","app_theme",23,1.265),
 ("@renansantosmbl","corrupcao-e-escandalos","app_theme",66,1.239),
 ("@renansantosmbl","celebridades-influencers","actor",19,1.224),
 ("@renansantosmbl","censura-digital","issue",10,1.145),
 ("@renansantosmbl","pauta-trans","issue",8,1.142),
 ("@renansantosmbl","comportamento-e-familia","app_theme",59,1.128),
 ("@renansantosmbl","energia-tecnologia-e-infra","app_theme",9,1.126),
 ("@renansantosmbl","prefeitura-gestao-local","actor",19,1.112),
 ("@renansantosmbl","municipios-e-federalismo","app_theme",22,1.082),
 ("@renansantosmbl","corrupcao","app_theme",39,1.079),
 ("@renansantosmbl","uf-ce","app_uf",15,1.070),
 ("@renansantosmbl","faccoes-criminosas","actor",21,1.049),
 ("@renansantosmbl","bolsonaro-direita","actor",54,1.045),
 ("@renansantosmbl","valores-liberdade","app_theme",27,1.017),
 ("@renansantosmbl","lula-pt","actor",106,1.009),
 ("@renansantosmbl","sao-paulo","place",9,1.000),
 ("@renansantosmbl","propriedade-invasoes","issue",31,1.000),
 ("@renansantosmbl","emprego-renda","issue",24,1.000),
 ("@renansantosmbl","periferia","constituency",8,1.000),
 ("@renansantosmbl","agro-e-ambiente","app_theme",18,1.000),
 ("@renansantosmbl","campanha-e-eleicoes","app_theme",158,1.000),
 ("@renansantosmbl","corrupcao","issue",144,1.000),
 ("@renansantosmbl","crime-organizado","issue",190,1.000),
 ("@renansantosmbl","debate-cultural","event",83,1.000),
 ("@renansantosmbl","decisao-judicial","event",14,1.000),
 ("@renansantosmbl","agro","issue",35,1.000),
 ("@renansantosmbl","uf-ms","app_uf",8,0.998),
 ("@renansantosmbl","escandalo-investigacao","event",69,0.991),
 ("@renansantosmbl","eleicao-candidatura","event",190,0.986),
 ("@renansantosmbl","uf-rj","app_uf",17,0.986),
 ("@renansantosmbl","seguranca","app_theme",63,0.983),
 ("@renansantosmbl","crime-e-faccoes","app_theme",133,0.981),
 ("@renansantosmbl","impostos","issue",45,0.981),
 ("@renansantosmbl","energia","issue",11,0.954),
 ("@renansantosmbl","nordeste","place",29,0.944),
 ("@renansantosmbl","contas-publicas","app_theme",36,0.944),
 ("@renansantosmbl","jogo-politico","app_theme",59,0.944),
 ("@renansantosmbl","guerra-cultural","app_theme",45,0.931),
 ("@renansantosmbl","liberdade-expressao","issue",15,0.931),
 ("@renansantosmbl","saneamento-moradia","issue",44,0.915),
 ("@renansantosmbl","seguranca-publica","issue",207,0.907),
 ("@renansantosmbl","saude-e-educacao","app_theme",16,0.891),
 ("@renansantosmbl","juventude","constituency",12,0.879),
 ("@renansantosmbl","justica-e-instituicoes","app_theme",60,0.829),
 ("@renansantosmbl","educacao","issue",31,0.829),
 ("@renansantosmbl","gasto-publico","issue",99,0.819),
 ("@renansantosmbl","exterior","place",22,0.799),
 ("@renansantosmbl","cidades","app_theme",8,0.791),
 ("@renansantosmbl","missao","app_theme",39,0.776),
 ("@renansantosmbl","midia-imprensa","actor",10,0.768),
 ("@renansantosmbl","economia","app_theme",10,0.748),
 ("@renansantosmbl","meio-ambiente","issue",21,0.726),
 ("@renansantosmbl","cidades-e-moradia","app_theme",34,0.696),
 ("@renansantosmbl","congresso-centrao","actor",22,0.696),
 ("@renansantosmbl","stf-moraes","actor",38,0.681),
 ("@renansantosmbl","mundo-e-historia","app_theme",33,0.681),
 ("@renansantosmbl","transporte","issue",11,0.530),
 ("@renansantosmbl","uf-pa","app_uf",14,0.465),
 ("@renansantosreserva","municipios-e-federalismo","app_theme",8,3.301),
 ("@renansantosreserva","nordeste","place",10,1.781),
 ("@renansantosreserva","campanha-e-eleicoes","app_theme",66,1.676),
 ("@renansantosreserva","emprego-renda","issue",14,1.284),
 ("@renansantosreserva","debate-cultural","event",16,1.266),
 ("@renansantosreserva","eleicao-candidatura","event",75,1.222),
 ("@renansantosreserva","bolsonaro-direita","actor",37,1.099),
 ("@renansantosreserva","escandalo-investigacao","event",13,1.089),
 ("@renansantosreserva","comportamento-e-familia","app_theme",27,1.087),
 ("@renansantosreserva","contas-publicas","app_theme",17,1.060),
 ("@renansantosreserva","saneamento-moradia","issue",8,1.060),
 ("@renansantosreserva","crime-organizado","issue",54,1.036),
 ("@renansantosreserva","economia-e-trabalho","app_theme",18,1.017),
 ("@renansantosreserva","mundo-e-historia","app_theme",11,1.000),
 ("@renansantosreserva","corrupcao","issue",48,1.000),
 ("@renansantosreserva","gasto-publico","issue",36,0.981),
 ("@renansantosreserva","corrupcao-e-escandalos","app_theme",19,0.971),
 ("@renansantosreserva","lula-pt","actor",39,0.964),
 ("@renansantosreserva","seguranca-publica","issue",52,0.954),
 ("@renansantosreserva","impostos","issue",8,0.754),
 ("@renansantosreserva","crime-e-faccoes","app_theme",35,0.726),
 ("@renansantosreserva","faccoes-criminosas","actor",19,0.607),
 ("@renansantosreserva","justica-e-instituicoes","app_theme",13,0.552),
 ("@renansantosreserva","stf-moraes","actor",12,0.341),
]

# ── papéis: nome bruto, papel, n ─────────────────────────────────────────────
PAPEIS = [
 ("Renan Santos","ally",1472),("Lula","villain",1012),("Renan Santos","protagonist",546),
 ("Flávio Bolsonaro","villain",491),("Renan","ally",478),("Renan Santos","candidate",450),
 ("Comando Vermelho","villain",317),("Bolsonaro","villain",284),("PCC","villain",181),
 ("crime organizado","villain",181),("PT","villain",167),("Jair Bolsonaro","villain",158),
 ("Lula / PT","villain",142),("Lula","ally",140),("Alexandre de Moraes","villain",138),
 ("Daniel Vorcaro","villain",121),("Kim Kataguiri","ally",118),("Bolsonaro","ally",106),
 ("esquerda","villain",99),("Renan","protagonist",91),("Flávio Bolsonaro","ally",85),
 ("facções criminosas","villain",76),("Erika Hilton","villain",73),("Lula/PT","villain",72),
 ("Ciro Nogueira","villain",72),("Flávio","villain",65),("MBL","ally",64),
 ("Janja","villain",63),("Jair Bolsonaro","ally",52),("Dias Toffoli","villain",48),
 ("Centrão","villain",48),("Lula","opponent",46),("faccoes-criminosas","villain",43),
 ("Tarcísio","ally",42),("Donald Trump","villain",41),("STF","villain",39),
 ("Renan","candidate",39),("Zema","ally",38),("Flavio Bolsonaro","villain",38),
 ("Zema","villain",37),("Renato Santos","ally",36),("Tarcísio","villain",36),
 ("Dilma Rousseff","villain",36),("Haddad","villain",35),("faccoes criminosas","villain",35),
 ("bandido","villain",35),("Valdemar da Costa Neto","villain",35),("Kim","ally",34),
 ("traficantes","villain",34),("Eduardo Bolsonaro","villain",33),("Neymar","villain",33),
 ("Gilmar Mendes","villain",33),("Facções criminosas","villain",32),("Guilherme Boulos","villain",32),
 ("André Valadão","villain",32),("Fabiano Zettel","villain",31),("governo federal","villain",31),
 ("Guido Mantega","villain",30),("João Campos","villain",30),("Donald Trump","ally",30),
 ("Alcolumbre","villain",30),("PSOL","villain",29),("Nayib Bukele","ally",29),
 ("Marcinho VP","villain",28),("Jerônimo Rodrigues","villain",28),("Nicolas Ferreira","villain",28),
 ("Janja","ally",28),("família Bolsonaro","villain",28),("Pablo Marçal","villain",27),
 ("Wesley Safadão","villain",26),("Jacques Wagner","villain",26),("Tabata Amaral","villain",26),
 ("Caiado","ally",25),("políticos corruptos","villain",25),("Governo Federal","villain",25),
 ("Vorcaro","villain",25),("Romeu Zema","villain",25),("Fernando Haddad","villain",25),
 ("Flávio Dino","villain",24),("Ciro Nogueira","ally",24),("Bolsonaro / direita","villain",24),
 ("facções","villain",23),("Milei","ally",23),("Renan Santos","villain",23),
 ("Luiz Inácio Lula da Silva","villain",23),("bandidos","villain",23),("Bukele","ally",23),
 ("Daniel Vorkaro","villain",22),("Romeu Zema","ally",22),("Guido Mantega","ally",22),
 ("Javier Milei","ally",22),("Virginia","villain",22),("Toffoli","villain",22),
 ("China","villain",21),("Arthur Lira","villain",21),("Tarcísio de Freitas","ally",21),
 ("Partido dos Trabalhadores (PT)","villain",21),("Jerônimo","villain",21),("centrão","villain",21),
 ("Lulinha","villain",20),("Caiado","villain",20),("criminosos","villain",20),("Dilma","villain",20),
 ("Ricardo Lewandowski","villain",19),("Eduardo Bolsonaro","ally",19),("Erika Hilton","ally",19),
 ("Trump","ally",19),("Tarcísio de Freitas","villain",18),("Barbalho","villain",18),
 ("Helder Barbalho","villain",18),("Maduro","villain",18),("Rui Costa","villain",18),
 ("a esquerda","villain",18),("PCC (Primeiro Comando da Capital)","villain",18),
 ("Everton Rocha","villain",17),("Nicolas","villain",17),("Trump","villain",17),
 ("facção criminosa","villain",17),("Ratinho","villain",17),("Flávio Bolsonaro","opponent",17),
 ("Nicolás Ferreira","villain",17),("Queiroz","villain",17),("ONGs","villain",16),
 ("traficante","villain",16),("Governador do Ceará","villain",16),
 ("Valdemar da Costa Neto","ally",16),("classe política","villain",16),("Neymar","ally",16),
 ("Sérgio Moro","villain",16),("Dilma Rousseff","ally",16),("Família Bolsonaro","villain",15),
 ("George Soros","villain",15),("Flávio","ally",15),("Wesley Safadão","ally",15),
 ("Marina Silva","villain",15),("Bacelar","villain",14),("prefeito","villain",14),
 ("tráfico","villain",14),("Crime organizado","villain",14),("Eduardo Paes","villain",14),
 ("TCP","villain",14),("governador do Ceará","villain",13),("MST","villain",13),
 ("Felipe Neto","villain",13),("Flávio (Bolsonaro)","villain",13),("bolsonarismo","villain",13),
 ("Deolane","villain",13),("Kassab","villain",13),("Rede Globo","villain",13),
 ("Banco Master","villain",13),("Ronaldo Caiado","villain",13),("Jacques Wagner","ally",13),
 ("Haddad","ally",13),("Nicolás Maduro","villain",13),("Tarcísio Gomes de Freitas","villain",12),
 ("imprensa","villain",12),("Oruam","villain",12),("MC Rian","villain",12),
 ("Ratinho Júnior","villain",12),("Cláudio Castro","villain",12),("Flávio Dino","ally",12),
 ("Rui Costa","ally",12),("Adriano da Nóbrega","villain",11),("Pablo Marçal","ally",11),
 ("Valdemar Costa Neto","villain",11),("milícia","villain",11),("Gilmar Mendes","ally",11),
 ("oligarquias","villain",11),("Eduardo Paes","ally",11),("Nicolas Ferreira","ally",11),
 ("Guilherme Boulos","ally",10),("Lewandowski","villain",10),("Silas Malafaia","villain",10),
 ("Flávio","opponent",10),("Davi Alcolumbre","villain",10),("Hugo Mota","villain",10),
 ("Virgínia","villain",10),("Globo","villain",9),("Carlos Bolsonaro","villain",9),
 ("Renan Calheiros","villain",9),("Sérgio Moro","ally",9),("Ricardo Nunes","villain",9),
 ("Jair Bolsonaro","target",9),("Roberto Campos Neto","villain",9),("Wagner Moura","villain",9),
 ("Joesley Batista","villain",9),("Michel Temer","villain",7),("Marcola","villain",7),
 ("Zé Dirceu","villain",8),("Gilberto Kassab","villain",8),("Hamas","villain",8),
 ("Nikolas Ferreira","villain",8),("Boulos","villain",7),("Carla Zambelli","villain",6),
 ("Barroso","villain",6),("Anitta","villain",6),("Elon Musk","ally",6),
 ("Michele Bolsonaro","villain",6),("Kim Kataguiri","villain",6),("Flávio Bolsonaro","target",6),
 ("Caiado","opponent",7),("Dilma Rousseff","target",7),("Vinícius Júnior","villain",7),
 ("Eduardo Leite","villain",7),("Marçal","villain",7),("Sarney","villain",7),
 ("Anielle Franco","villain",5),("Renan Calheiros","ally",8),("Alckmin","ally",6),
 ("Ministério Público","villain",6),("Partido Novo","villain",6),("Romário","villain",6),
]

# Nomes que o extrator escreve de várias maneiras. Sem isto, "Flávio Bolsonaro"
# com 491 marcações e "Flavio Bolsonaro" com 38 viram duas pessoas diferentes.
APELIDOS = {
 "flavio bolsonaro": "Flávio Bolsonaro", "flavio": "Flávio Bolsonaro",
 "lula": "Lula", "lula pt": "Lula / PT", "luiz inacio lula da silva": "Lula",
 "lulinha": "Lulinha", "pt": "PT", "partido dos trabalhadores pt": "PT",
 "jair bolsonaro": "Jair Bolsonaro", "bolsonaro": "Jair Bolsonaro",
 "bolsonaro jair": "Jair Bolsonaro", "bolsonaro jair bolsonaro": "Jair Bolsonaro",
 "familia bolsonaro": "família Bolsonaro", "bolsonaro familia": "família Bolsonaro",
 "romeu zema": "Romeu Zema", "zema": "Romeu Zema",
 "tarcisio": "Tarcísio de Freitas", "tarcisio de freitas": "Tarcísio de Freitas",
 "tarcisio gomes de freitas": "Tarcísio de Freitas",
 "renan santos": "Renan Santos", "renan": "Renan Santos",
 "renan santos mbl": "Renan Santos", "renan orador": "Renan Santos",
 "renan speaker": "Renan Santos", "renan pre candidato": "Renan Santos",
 "renan palestrante": "Renan Santos", "renan santos arroba renansantosmbl": "Renan Santos",
 "daniel vorcaro": "Daniel Vorcaro", "vorcaro": "Daniel Vorcaro",
 "daniel vorkaro": "Daniel Vorcaro", "daniel vorcar": "Daniel Vorcaro",
 "toffoli": "Dias Toffoli", "dias toffoli": "Dias Toffoli",
 "haddad": "Fernando Haddad", "fernando haddad": "Fernando Haddad",
 "dilma": "Dilma Rousseff", "dilma rousseff": "Dilma Rousseff",
 "centrao": "Centrão", "caiado": "Ronaldo Caiado", "ronaldo caiado": "Ronaldo Caiado",
 "kim": "Kim Kataguiri", "kim kataguiri": "Kim Kataguiri",
 "trump": "Donald Trump", "donald trump": "Donald Trump",
 "milei": "Javier Milei", "javier milei": "Javier Milei",
 "bukele": "Nayib Bukele", "nayib bukele": "Nayib Bukele",
 "lewandowski": "Ricardo Lewandowski", "ricardo lewandowski": "Ricardo Lewandowski",
 "nicolas ferreira": "Nikolas Ferreira", "nicolas": "Nikolas Ferreira",
 "nikolas ferreira": "Nikolas Ferreira",
 "faccoes criminosas": "facções criminosas", "faccoes": "facções criminosas",
 "faccao criminosa": "facções criminosas", "crime organizado": "crime organizado",
 "governo federal": "governo federal", "esquerda": "esquerda", "a esquerda": "esquerda",
 "pcc primeiro comando da capital": "PCC", "pcc": "PCC",
 "sergio moro": "Sérgio Moro", "marcal": "Pablo Marçal", "pablo marcal": "Pablo Marçal",
 "renan calheiros": "Renan Calheiros", "boulos": "Guilherme Boulos",
 "guilherme boulos": "Guilherme Boulos", "alcolumbre": "Davi Alcolumbre",
 "davi alcolumbre": "Davi Alcolumbre", "kassab": "Gilberto Kassab",
 "gilberto kassab": "Gilberto Kassab", "virginia": "Virgínia",
 "ciro nogueira": "Ciro Nogueira", "erika hilton": "Erika Hilton",
 "ratinho junior": "Ratinho Júnior", "ratinho": "Ratinho Júnior",
 "valdemar costa neto": "Valdemar da Costa Neto",
 "valdemar da costa neto": "Valdemar da Costa Neto", "valdemar": "Valdemar da Costa Neto",
}

# Vocabulário genérico: útil como sinal de assunto, inútil como pessoa.
GENERICOS = {
 "bandido","bandidos","traficante","traficantes","criminosos","criminoso",
 "políticos","políticos corruptos","classe política","prefeito","prefeita",
 "prefeitos","governador","governadores","juiz","juízes","juíza","deputados",
 "imprensa","ONGs","oligarquias","elite política","assaltante","ladrão",
 "tráfico","milícia","facção criminosa","governo federal","esquerda",
 "crime organizado","facções criminosas","bolsonarismo","indígenas",
 "influenciadores","policiais","polícia","policial",
}

FORMATOS = [
 ("analise_estudio", 91, "Renan sozinho em estúdio; enquadramento fechado costuma servir."),
 ("evento", 5, "Palco e plateia; muitas vozes, e quase nunca a dele."),
 ("coletiva", 4, "Pergunta e resposta com imprensa; a pergunta faz parte do corte."),
 ("irl_live", 3, "Rua, deslocamento, áudio difícil."),
]


def chave(nome: str) -> str:
    sem_parenteses = re.sub(r"\([^)]*\)", " ", str(nome or ""))
    plano = unicodedata.normalize("NFKD", sem_parenteses.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", plano).split())


def canonico(nome: str) -> str:
    return APELIDOS.get(chave(nome), str(nome).strip())


def montar_papeis():
    """Junta os apelidos e decide o papel por dominância, guardando a dúvida.

    A mesma pessoa aparece nos dois lados: Flávio Bolsonaro tem 491 marcações
    como adversário e 85 como aliado; Zema tem 38 e 37. O primeiro é claro, o
    segundo não é, e tratar os dois igual seria inventar uma certeza que o dado
    não tem. Por isso cada nome carrega a proporção, e quem chegar perto do
    empate sai marcado como indefinido.
    """
    juntos = defaultdict(lambda: defaultdict(int))
    # As grafias como o extrator escreveu viram termos de busca. Sem isto o
    # espelho guarda "Romeu Zema" e o trecho que diz só "Zema" passa batido —
    # que é exatamente a forma como ele aparece falado.
    variantes = defaultdict(set)
    genericos = {chave(g) for g in GENERICOS}
    for nome, papel, n in PAPEIS:
        if chave(nome) in genericos:
            continue
        alvo = canonico(nome)
        juntos[alvo][papel] += n
        variantes[alvo].add(nome.strip())
    for apelido, alvo in APELIDOS.items():
        if alvo in juntos:
            variantes[alvo].add(apelido)

    adversarios = {"villain", "opponent", "target"}
    saida = []
    for nome, contagem in juntos.items():
        total = sum(contagem.values())
        contra = sum(n for papel, n in contagem.items() if papel in adversarios)
        a_favor = sum(n for papel, n in contagem.items() if papel in {"ally", "protagonist", "candidate"})
        decisivo = contra + a_favor
        if decisivo < 12:
            continue
        proporcao = contra / decisivo
        if proporcao >= 0.70:
            lado, confianca = "adversario", round(proporcao, 3)
        elif proporcao <= 0.30:
            lado, confianca = "aliado", round(1 - proporcao, 3)
        else:
            lado, confianca = "indefinido", round(max(proporcao, 1 - proporcao), 3)
        saida.append({
            "nome": nome,
            "lado": lado,
            "confianca": confianca,
            "marcacoes": total,
            "contra": contra,
            "a_favor": a_favor,
            "variantes": sorted({v for v in variantes[nome] if len(chave(v)) >= 4}),
        })
    saida.sort(key=lambda item: -item["marcacoes"])
    return saida


def main():
    papeis = montar_papeis()
    espelho = {
        "schema": "espelho-chub-v1",
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origem": "consulta ao banco do Campaign Hub",
        "fonte": {
            "posts_com_desempenho": 29596,
            "cortes_publicados": 5339,
            "cortes_com_transcricao": 3946,
            "cortes_com_gancho_rotulado": 4480,
            "blocos_do_acervo": 17673,
            "momentos_fortes": 35410,
            "temas_controlados": 100,
            "marcacoes_de_papel": 11535,
        },
        "ganchos": [
            {"conta": c, "plataforma": p, "familia": f, "n": n,
             "mediana": m, "p90": q}
            for c, p, f, n, m, q in GANCHOS
        ],
        "temas": [
            {"conta": c, "slug": s, "dimensao": d, "n": n, "mediana": m}
            for c, s, d, n, m in TEMAS
        ],
        "papeis": papeis,
        "formatos": [
            {"nome": nome, "videos": n, "nota": nota} for nome, n, nota in FORMATOS
        ],
        "portoes": {
            "pergunta_e_resposta_completas": 14,
            "comeca_no_meio_da_frase": -28,
            "termina_sem_fechar": -18,
            "duracao_e_preferencia_suave": True,
        },
        "minimo_de_observacoes": 3,
    }

    destino = Path("data/espelho_chub.json")
    destino.write_text(json.dumps(espelho, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{destino}  {destino.stat().st_size/1024:.1f} KB")
    print(f"  ganchos: {len(espelho['ganchos'])}")
    print(f"  temas:   {len(espelho['temas'])}")
    print(f"  papéis:  {len(papeis)}")
    print()
    for item in papeis[:14]:
        print(f"  {item['nome']:<26} {item['lado']:<12} conf={item['confianca']:.2f}  "
              f"({item['contra']} contra / {item['a_favor']} a favor)")
    print()
    indefinidos = [i for i in papeis if i["lado"] == "indefinido"]
    print(f"  indefinidos ({len(indefinidos)}): " + ", ".join(i["nome"] for i in indefinidos))


if __name__ == "__main__":
    main()
