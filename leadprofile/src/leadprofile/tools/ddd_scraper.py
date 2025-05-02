# ddd_scraper.py
"""
Scrape Claro blog (https://www.claro.com.br/blog/celular/ddd-{dd})            ✓
Retorna estado, lista de cidades e URL-fonte.
"""
import re
import requests
from typing import List, Tuple
# BS4 docs :contentReference[oaicite:1]{index=1}
from bs4 import BeautifulSoup

from functools import lru_cache

# Requests headers :contentReference[oaicite:2]{index=2}
HEADERS = {"User-Agent": "Mozilla/5.0 (LeadProfileHunter/1.0)"}


# def scrape_claro_ddd(ddd: str) -> Tuple[str, List[str], str]:
#     url = f"https://www.claro.com.br/blog/celular/ddd-{ddd}"
#     resp = requests.get(url, headers=HEADERS, timeout=10)
#     resp.raise_for_status()

#     soup = BeautifulSoup(resp.text, "html.parser")
#     # h2 semelhante a “Quais são as Cidades...” :contentReference[oaicite:3]{index=3}
#     h2 = soup.find("h2", string=lambda t: t and "cidades" in t.lower())
#     cities, state = [], ""

#     if h2:
#         ul = h2.find_next("ul")
#         cities = [li.get_text(strip=True)
#                   for li in ul.find_all("li")] if ul else []
#         # Estado aparece em parágrafo anterior
#         prev_p = h2.find_previous("p")
#         if prev_p:
#             m = re.search(r"estado do\s+(.+?)\.", prev_p.text, re.I)
#             if m:
#                 state = m.group(1)

#     return state, cities, url

@lru_cache(maxsize=64)        # evita hit repetido para o mesmo DDD
def scrape_claro_ddd(ddd: str) -> Tuple[str, List[str], str]:
    """
    Raspagem otimizada via CSS‑selector específico:
    • Seleciona o 6.º <section> dentro de #cms-Main-Content
    • Extrai todos os <li> para formar a lista completa de cidades
    • Extrai o estado a partir do texto do <h2> ou <h3> da mesma seção
    """
    url = f"https://www.claro.com.br/blog/celular/ddd-{ddd}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1) Selecionar o 6.º <section>
    target_section = soup.select_one(
        "#cms-Main-Content > section:nth-of-type(6)")
    if not target_section:
        return "", [], url             # layout mudou → devolve vazio

    # 2) Coletar todas as cidades dentro de <li>
    cities = [
        li.get_text(strip=True)
        for li in target_section.select("li")
        if li.get_text(strip=True)
    ]
    cities = sorted(set(cities))       # remove duplicados

    # 3) Tentar extrair o estado do título da seção
    state = ""
    heading = target_section.find(["h2", "h3"])
    if heading:
        m = re.search(
            r"DDD\s+\d+\s*-\s*([^–—\-]+)$", heading.get_text(strip=True))
        if m:
            state = m.group(1).strip()

    # 4) Fallback: usar parágrafo anterior fora da seção
    if not state:
        first_section = soup.select_one(
            "#cms-Main-Content > section:nth-of-type(1)")
        if first_section:
            prev_p = first_section.find_previous("p")
            if prev_p:
                m = re.search(r"estado do\s+(.+?)\.", prev_p.text, re.I)
                if m:
                    state = m.group(1)

    return state, cities, url
