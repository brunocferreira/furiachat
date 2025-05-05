# furiachat/tools/hltv_scraper.py
"""
Scraper utilitário dedicado ao FuriaChat 🐾 que coleta dados das páginas
públicas da HLTV relacionadas ao time FURIA (Team‑ID 8297).

Funções exportadas (interface estável para `HLTVScraperTool`):
------------------------------------------------------------
• `fetch_html(url)` – download robusto + cache em memória
• `discover_links(html=None, url=None)` – encontra links internos úteis
• `parse_team_overview(url=...)` – roster, próximos jogos, resultados
• `parse_stats_team(url=...)` **(alias** `parse_team_stats`) – rating & mapas
• `parse_match_summary(url)` **(alias** `parse_match_page`) – placar & veto
• `parse_news(url)` – título, data, autor e corpo em Markdown

Assim qualquer agente pode importar:
```python
from furiachat.tools.hltv_scraper import (
    fetch_html, discover_links, parse_team_overview,
    parse_stats_team, parse_match_summary, parse_news,
)
```
Todas as funções usam *requests* + *BeautifulSoup*.  Não há state global.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, List, Set

import requests
from bs4 import BeautifulSoup, Tag

__all__ = [
    "HEADERS",
    "HLTV_BASE",
    "fetch_html",
    "discover_links",
    "parse_team_overview",
    "parse_stats_team",
    "parse_team_stats",  # alias
    "parse_match_summary",
    "parse_match_page",  # alias
    "parse_news",
]

HLTV_BASE = "https://www.hltv.org"
TEAM_ID = 8297  # FURIA
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36 (FuriaChat/1.0)"
)
HEADERS = {"User-Agent": USER_AGENT}


# ─────────────────────────── CORE HELPERS ────────────────────────────── #

def _request_with_retry(url: str, max_retries: int = 3, timeout: int = 15) -> requests.Response:
    delay = 1.5
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2


@lru_cache(maxsize=128)
def fetch_html(url: str) -> str:
    """Baixa HTML bruto com cache em memória."""
    resp = _request_with_retry(url)
    return resp.text


def _parse_datetime_ms(timestamp_ms: str | None) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc)
    except (ValueError, TypeError):
        return None


# ─────────────────────── TEAM OVERVIEW PAGE ──────────────────────────── #

def parse_team_overview(url: str = f"{HLTV_BASE}/team/{TEAM_ID}/furia") -> Dict:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    # Roster
    roster: List[Dict] = []
    for player_tag in soup.select(".player-holder .flagCon"):
        name_span = player_tag.select_one("span.name")
        if name_span:
            nickname = name_span.get_text(strip=True)
            country = player_tag.find_next("img", class_="flag").get(
                "title", "") if player_tag.find_next("img", class_="flag") else ""
            roster.append({"nickname": nickname, "country": country})

    # Próximos jogos
    next_matches: List[Dict] = []
    for row in soup.select("div.upcoming-match .matchList"):
        link = row.find("a", class_="match")
        if not link:
            continue
        match_url = HLTV_BASE + link.get("href", "")
        vs_team = link.select_one(".opponent div").get_text(
            strip=True) if link.select_one(".opponent div") else "TBD"
        event = link.select_one(".matchInfoEmpty span").get_text(
            strip=True) if link.select_one(".matchInfoEmpty span") else ""
        time_ms = link.get("data-zonedgrouping-entry-unix")
        match_time = _parse_datetime_ms(time_ms)
        next_matches.append({"opponent": vs_team, "event": event,
                            "datetime_utc": match_time, "url": html})

    # Resultados recentes
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

    return {"roster": roster, "next_matches": next_matches, "recent_results": recent_results, "source": url}


# ───────────────────────── TEAM STATS PAGE ───────────────────────────── #

def parse_stats_team(url: str = f"{HLTV_BASE}/stats/teams/{TEAM_ID}/furia") -> Dict:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    rating = soup.select_one("div.standard-box span.rating")
    kd = soup.select_one("div.standard-box span.kd")
    maps_played = soup.select_one("div.standard-box span.maps")

    top_maps: List[Dict] = []
    for tr in soup.select("table.stats-table tbody tr")[:7]:
        cols = [c.get_text(strip=True) for c in tr.select("td")]
        if len(cols) >= 5:
            top_maps.append({"map": cols[0], "times_played": int(
                cols[1]), "win_pct": cols[2], "kd_diff": cols[3], "rating": cols[4]})

    return {"rating": rating.get_text(strip=True) if rating else None, "kd": kd.get_text(strip=True) if kd else None, "maps_played": maps_played.get_text(strip=True) if maps_played else None, "top_maps": top_maps, "source": url}


# Alias para compatibilidade
parse_team_stats = parse_stats_team

# ───────────────────────── MATCH PAGE ─────────────────────────────────── #


def parse_match_summary(url: str) -> Dict:
    """Resumo de partida: placar, veto de mapas, MVP."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    team_elems = soup.select("div.teamName")
    score_elems = soup.select("div.score")
    if len(team_elems) >= 2 and len(score_elems) >= 2:
        team1, team2 = [t.get_text(strip=True) for t in team_elems[:2]]
        score1, score2 = [int(s.get_text(strip=True)) for s in score_elems[:2]]
    else:
        team1 = team2 = ""
        score1 = score2 = 0

    veto: List[str] = [li.get_text(strip=True) for li in soup.select(
        "div.round-history-con")] or [li.get_text(strip=True) for li in soup.select("div.veto-box ul li")]

    mvp = soup.select_one("div.highlighted-player div.name")

    return {"teams": [team1, team2], "score": [score1, score2], "veto": veto, "mvp": mvp.get_text(strip=True) if mvp else None, "source": url}


# Alias
parse_match_page = parse_match_summary

# ───────────────────────── NEWS PAGE ──────────────────────────────────── #


def parse_news(url: str) -> Dict:
    """Extrai título, autor, data UTC e corpo em Markdown de uma notícia."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    title = soup.select_one(
        "h1.newsline-title").get_text(strip=True) if soup.select_one("h1.newsline-title") else ""
    author = soup.select_one("span.author a").get_text(
        strip=True) if soup.select_one("span.author a") else ""
    date_elem = soup.select_one("span.date")
    date_utc = _parse_datetime_ms(date_elem.get(
        "data-unix")) if date_elem and date_elem.get("data-unix") else None

    paragraphs = [p.get_text(strip=True) for p in soup.select(
        "div.newsline-body p") if p.get_text(strip=True)]
    body_md = "\n\n".join(paragraphs)

    return {"title": title, "author": author, "datetime_utc": date_utc, "body_md": body_md, "source": url}

# ─────────────────────── DISCOVER INTERNAL LINKS ─────────────────────── #


def _is_hltv_internal(href: str | None) -> bool:
    return bool(href and (href.startswith("/news/") or href.startswith("/matches/") or href.startswith("/stats/")))


def discover_links(html: str | None = None, url: str | None = None) -> Set[str]:
    """Retorna conjunto de links internos relevantes encontrados no HTML."""
    if html is None and url:
        html = fetch_html(url)
    soup = BeautifulSoup(html or "", "lxml")
    links: Set[str] = set()
    for a in soup.find_all("a", href=True):
        if _is_hltv_internal(a["href"]):
            full = a["href"] if a["href"].startswith(
                "http") else HLTV_BASE + a["href"]
            links.add(full)
    return links
