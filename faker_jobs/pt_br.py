"""
European Portuguese (the ESCO labels) to Brazilian Portuguese, for the
occupations of the `pt_BR` locale: the spelling of the 1990 agreement where
the two differ (consonants Brazil still writes: 'receção' -> 'recepção',
'contacto' -> 'contato'; 'ó' and 'é' before m or n: 'eletrónico' ->
'eletrônico', 'género' -> 'gênero') and common words of everyday and work
vocabulary ('equipa' -> 'equipe', 'registo' -> 'registro', 'autocarro' ->
'ônibus', 'utilizador' -> 'usuário').

Word-based, hand-made, so it leaves European turns of phrase alone; good
enough for job titles, descriptions and skills.
"""
from __future__ import annotations

import re
from functools import lru_cache

# European word -> Brazilian word (lowercase; plurals listed where irregular).
WORDS = {
    "equipa": "equipe", "equipas": "equipes",
    "registo": "registro", "registos": "registros", "registar": "registrar", "registado": "registrado",
    "registada": "registrada", "registados": "registrados", "registadas": "registradas",
    "utilizador": "usuário", "utilizadores": "usuários", "utilizadora": "usuária", "utilizadoras": "usuárias",
    "ficheiro": "arquivo", "ficheiros": "arquivos", "ecrã": "tela", "ecrãs": "telas",
    "telemóvel": "celular", "telemóveis": "celulares",
    "autocarro": "ônibus", "autocarros": "ônibus", "comboio": "trem", "comboios": "trens",
    "camião": "caminhão", "camiões": "caminhões", "camionista": "caminhoneiro", "camionistas": "caminhoneiros",
    "pequeno-almoço": "café da manhã", "frigorífico": "geladeira", "frigoríficos": "geladeiras",
    "talho": "açougue", "talhos": "açougues", "talhante": "açougueiro", "talhantes": "açougueiros",
    "canalizador": "encanador", "canalizadores": "encanadores", "canalizadora": "encanadora",
    "canalização": "encanamento", "canalizações": "encanamentos",
    "contabilista": "contador", "contabilistas": "contadores",
    "desporto": "esporte", "desportos": "esportes", "desportivo": "esportivo", "desportiva": "esportiva",
    "desportivos": "esportivos", "desportivas": "esportivas", "desportista": "esportista",
    "desportistas": "esportistas",
    "facto": "fato", "factos": "fatos", "contacto": "contato", "contactos": "contatos",
    "contactar": "contatar", "secção": "seção", "secções": "seções",
    "receção": "recepção", "receções": "recepções", "rececionista": "recepcionista",
    "rececionistas": "recepcionistas", "perceção": "percepção", "perceções": "percepções",
    "conceção": "concepção", "conceções": "concepções", "deteção": "detecção", "deteções": "detecções",
    "detetar": "detectar", "detetor": "detector", "detetores": "detectores", "aceção": "acepção",
    "ótico": "óptico", "ótica": "óptica", "óticos": "ópticos",
    "óticas": "ópticas", "betão": "concreto", "guarda-redes": "goleiro", "relvado": "gramado",
    "ementa": "cardápio", "ementas": "cardápios", "montra": "vitrine", "montras": "vitrines",
    "empregado de mesa": "garçom", "empregada de mesa": "garçonete", "empregados de mesa": "garçons",
    "casa de banho": "banheiro", "casas de banho": "banheiros", "infantário": "creche",
    "controlo": "controle", "controlos": "controles",
    "aspeto": "aspecto", "aspetos": "aspectos", "respetivo": "respectivo", "respetiva": "respectiva",
    "respetivos": "respectivos", "respetivas": "respectivas", "carácter": "caráter",
    "utente": "usuário", "utentes": "usuários", "faturação": "faturamento", "habilitações": "escolaridade",
    "call centre": "call center", "call centres": "call centers",
    # Spelling before 1990, still in the NACE labels.
    "actividade": "atividade", "actividades": "atividades", "acto": "ato", "actos": "atos",
    "direcção": "direção", "projecto": "projeto", "projectos": "projetos", "colectivo": "coletivo",
    "colectiva": "coletiva", "colectivos": "coletivos", "colectivas": "coletivas", "efectivo": "efetivo",
    "electricidade": "eletricidade", "eléctrico": "elétrico", "eléctrica": "elétrica", "eléctricos": "elétricos",
    "eléctricas": "elétricas", "electrónico": "eletrônico", "electrónica": "eletrônica",
    "planear": "planejar", "planeamento": "planejamento", "planeado": "planejado", "planeada": "planejada",
    "planeados": "planejados", "planeadas": "planejadas", "planeie": "planeje",
    "selecção": "seleção", "protecção": "proteção", "objecto": "objeto", "objectos": "objetos",
}
# Turns of phrase of the posting texts (faker_jobs/posting_text.py), applied first.
PHRASES = {
    "está a recrutar": "está contratando", "Como candidatar-se": "Como se candidatar",
    "Envie a sua candidatura a": "Envie sua candidatura para", "Contacte": "Entre em contato com",
    "através do": "pelo", "referência da oferta": "referência da vaga", "Oferta publicada a": "Vaga publicada em",
    "teletrabalho parcial": "home office parcial", "Regime de teletrabalho a 100 % (remoto)": "Trabalho 100 % remoto",
}
_PHRASES = {phrase.lower(): replacement for phrase, replacement in PHRASES.items()}
_PHRASE = re.compile("|".join(map(re.escape, sorted(PHRASES, key=len, reverse=True))), re.IGNORECASE)
_WORD = re.compile(r"(?<![\w-])(" + "|".join(sorted(map(re.escape, WORDS), key=len, reverse=True)) + r")(?![\w-])",
                   re.IGNORECASE)
# 'ó' / 'é' stressed before m or n and a vowel: closed in Brazil ('económico' -> 'econômico').
_ACCENTS = re.compile(r"[óé](?=[mn][aeiouáéíóúâêôãõ])")


def _keep_case(original: str, replacement: str) -> str:
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


@lru_cache(maxsize=65536)
def to_brazilian(text: str) -> str:
    """`text` in European Portuguese, in Brazilian spelling and vocabulary."""
    text = _PHRASE.sub(lambda m: _keep_case(m.group(0), _PHRASES[m.group(0).lower()]), text)
    text = _WORD.sub(lambda m: _keep_case(m.group(0), WORDS[m.group(0).lower()]), text)
    return _ACCENTS.sub(lambda m: {"ó": "ô", "é": "ê"}[m.group(0)], text)
