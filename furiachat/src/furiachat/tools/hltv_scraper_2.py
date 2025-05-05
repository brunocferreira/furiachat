# furiachat/tools/hltv_scraper.py
"""
Scraper utilitário dedicado ao FuriaChat 🐾 que coleta dados das páginas
públicas da HLTV relacionadas ao time FURIA (Team‑ID 8297).

Principais responsabilidades
---------------------------
1. `fetch_html(url)` – faz download robusto com cabeçalho de navegador.
2. `parse_team_overview()` – extrai escalação, próximos jogos, últimos
   resultados da página / team / 8297 / furia.
3. `parse_team_stats()` – coleta rating, mapas mais jogados, etc.
4. `parse_match_page()` – captura placar final, veto de mapas e destaques
   de um jogo específico.
5. `discover_links()` – descobre URLs internas úteis para crawler.

Todas as funções utilizam *BeautifulSoup*.
Não há state global; cache opcional pelo decorator `lru_cache`.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, List, Tuple, Iterable, Set

import requests
from bs4 import BeautifulSoup, Tag

__all__ = [
    "HEADERS",
    "HLTV_BASE",
    "fetch_html",
    "parse_team_overview",
    "parse_team_stats",
    "parse_match_page",
    "discover_links",
]

HLTV_BASE = "https://www.hltv.org"
TEAM_ID = 8297  # FURIA ‑ usado em vários seletores
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36 (FuriaChat/1.0)"
)
HEADERS = {"User-Agent": USER_AGENT}


def _request_with_retry(url: str, max_retries: int = 3, timeout: int = 15) -> requests.Response:
    """Faz requisição GET com back‑off exponencial simples."""
    delay = 1.5
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:  # pragma: no cover
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2


@lru_cache(maxsize=128)
def fetch_html(url: str) -> str:
    """Baixa HTML bruto de *url* com cache em memória."""
    resp = _request_with_retry(url)
    return resp.text

# ---------------------------------------------------------------------------
# 1. Team overview page – https://www.hltv.org/team/8297/furia
# ---------------------------------------------------------------------------


def _parse_datetime_ms(timestamp_ms: str) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc)
    except (ValueError, TypeError):
        return None


def parse_team_overview(url: str = f"{HLTV_BASE}/team/{TEAM_ID}/furia") -> Dict:
    """Retorna dicionário com *roster*, *next_matches* e *recent_results*."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    # --- roster
    roster: List[Dict] = []
    for player_tag in soup.select(".player-holder .flagCon"):
        # Estrutura <div class="flagCon"><span class="name">KSCERATO</span> ...</span>
        name_span = player_tag.select_one("span.name")
        if name_span:
            nickname = name_span.get_text(strip=True)
            country = (
                player_tag.find_next("img", class_="flag")
                .get("title")
                if player_tag.find_next("img", class_="flag")
                else ""
            )
            roster.append({"nickname": nickname, "country": country})

    # --- próximos jogos (tabela "Upcoming matches")
    next_matches: List[Dict] = []
    for row in soup.select("div.upcoming-match .matchList"):  # lista curta
        link = row.find("a", class_="match")
        if not link:
            continue
        match_url = HLTV_BASE + link.get("href", "")
        vs_team = link.select_one(".opponent div").get_text(
            strip=True) if link.select_one(".opponent div") else "TBD"
        event = link.select_one(".matchInfoEmpty span").get_text(
            strip=True) if link.select_one(".matchInfoEmpty span") else ""
        time_ms = link.get(
            "data-zonedgrouping-entry-unix" or link.get("data-zonedgrouping-entry-unix"))
        match_time = _parse_datetime_ms(time_ms) if time_ms else None
        next_matches.append(
            {
                "opponent": vs_team,
                "event": event,
                "datetime_utc": match_time,
                "url": match_url,
            }
        )

    # --- resultados recentes
    recent_results: List[Dict] = []
    for row in soup.select("div.results-holder .results-sublist a"):
        res_url = HLTV_BASE + row.get("href", "")
        score = row.select_one(
            ".result-score").get_text(strip=True) if row.select_one(".result-score") else ""
        opponent = row.select_one(".team").get_text(
            strip=True) if row.select_one(".team") else ""
        event = row.select_one(".event").get_text(
            strip=True) if row.select_one(".event") else ""
        recent_results.append(
            {"score": score, "opponent": opponent, "event": event, "url": res_url})

    return {
        "roster": roster,
        "next_matches": next_matches,
        "recent_results": recent_results,
        "source": url,
    }

# ---------------------------------------------------------------------------
# 2. Team stats page – https://www.hltv.org/stats/teams/8297/furia
# ---------------------------------------------------------------------------


def parse_team_stats(url: str = f"{HLTV_BASE}/stats/teams/{TEAM_ID}/furia") -> Dict:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    rating = soup.select_one("div.standard-box span.rating")
    kd = soup.select_one("div.standard-box span.kd")
    maps_played = soup.select_one("div.standard-box span.maps")

    top_maps: List[Dict] = []
    for tr in soup.select("table.stats-table tbody tr")[:7]:  # máx 7 mapas
        cols = [c.get_text(strip=True) for c in tr.select("td")]
        if len(cols) >= 5:
            top_maps.append(
                {
                    "map": cols[0],
                    "times_played": int(cols[1]),
                    "win_pct": cols[2],
                    "kd_diff": cols[3],
                    "rating": cols[4],
                }
            )

    return {
        "rating": rating.get_text(strip=True) if rating else None,
        "kd": kd.get_text(strip=True) if kd else None,
        "maps_played": maps_played.get_text(strip=True) if maps_played else None,
        "top_maps": top_maps,
        "source": url,
    }

# ---------------------------------------------------------------------------
# 3. Match page – /matches/<id>/<teams>
# ---------------------------------------------------------------------------


def parse_match_page(url: str) -> Dict:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    # placar geral
    team_elems = soup.select("div.teamName")
    score_elems = soup.select("div.score")
    if len(team_elems) >= 2 and len(score_elems) >= 2:
        team1, team2 = [t.get_text(strip=True) for t in team_elems[:2]]
        score1, score2 = [int(s.get_text(strip=True)) for s in score_elems[:2]]
    else:
        team1 = team2 = ""
        score1 = score2 = 0

    # veto de mapas
    veto: List[str] = [li.get_text(strip=True) for li in soup.select(
        "div.round-history-con")]  # fallback
    if not veto:
        veto = [li.get_text(strip=True)
                for li in soup.select("div.veto-box ul li")]

    # jogador destaque (MVP) se existir
    mvp = soup.select_one("div.highlighted-player div.name")

    return {
        "teams": [team1, team2],
        "score": [score1, score2],
        "veto": veto,
        "mvp": mvp.get_text(strip=True) if mvp else None,
        "source": url,
    }

# ---------------------------------------------------------------------------
# 4. Descoberta de links internos
# ---------------------------------------------------------------------------


def _is_hltv_internal(href: str | None) -> bool:
    if not href:
        return False
    return href.startswith("/news/") or href.startswith("/matches/") or href.startswith("/stats/")


def discover_links(html: str | None = None, url: str | None = None) -> Set[str]:
    """Retorna conjunto de links internos relevantes encontrados no HTML."""
    if html is None and url:
        html = fetch_html(url)
    soup = BeautifulSoup(html or "", "lxml")
    links: Set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if _is_hltv_internal(href):
            full = href if href.startswith("http") else HLTV_BASE + href
            links.add(full)
    return links
