# furiachat/agents/hltv_agents.py
"""HLTV agents e tasks para o Pantera‑Bot.
Corrige import para o utilitário de scraping e garante que TODAS as
funções existam antes de importar.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any

from crewai import Agent, Task, Crew
from crewai.tools import BaseTool

from furiachat.src.furiachat.tools.hltv_scraper import (
fetch_html,
discover_links,
parse_team_overview,
parse_stats_team,
parse_match_summary,
parse_news,
)

    from furiachat.utils.cost import gpt4o_mini_cost
    from furiachat.utils.usage import usage_to_dict

    # ─────────────────────────────── Tool ──────────────────────────────── #

    class HLTVInput(BaseTool.args_schema):  # type: ignore[attr-defined]
    endpoint: str
    url: str | None = None  # opcional para match_summary / news

    class HLTVScraperTool(BaseTool):
    """Wrapper thin sobre funções de scraping/parse."""

    name: str = "hltv_scraper"
    description: str = (
"Coleta dados de HLTV.org sobre a FURIA. Endpoints: "
"team_overview | stats_team | match_summary | news"
)
    args_schema = HLTVInput  # type: ignore[assignment]

    def _run(self, endpoint: str, url: str | None = None) -> str:  # noqa: N802
        match endpoint:
            case "team_overview":
                data = parse_team_overview()
            case "stats_team":
                data = parse_stats_team()
            case "match_summary":
                if not url:
                    raise ValueError("url requerido para match_summary")
                data = parse_match_summary(url)
            case "news":
                if not url:
                    raise ValueError("url requerido para news")
                data = parse_news(url)
            case _:
                raise ValueError(f"endpoint desconhecido: {endpoint}")

        return json.dumps(data, ensure_ascii=False)

# ─────────────────────────── Agent builder ─────────────────────────── #


def build_pantera_agent(openai_api_key: str) -> Agent:
    os.environ["OPENAI_API_KEY"] = openai_api_key

    return Agent(
role="Especialista HLTV / FURIA",
goal="Responder perguntas objetivas sobre o time FURIA usando HLTV",
backstory=(
    "Você acompanha todas as notícias, estatísticas e jogos da FURIA na HLTV "
    "e utiliza seu scraper para trazer informações atualizadas."
),
tools=[HLTVScraperTool()],
max_iter=3,
temperature=0,
 verbose=True,
  )

   # ────────────────── Task wrapper para usar no Streamlit ──────────────── #


   def run_pantera_task(question: str, openai_api_key: str) -> Dict[str, Any]:
   """Executa um crew único com uma task e devolve dict para UI."""
        agent= build_pantera_agent(openai_api_key)

        task= Task(
   description = question,
    expected_output = "Resposta em português, clara e direta.",
    agent = agent,
    )

        crew= Crew(agents=[agent], tasks=[task], verbose=True)
        output= crew.kickoff()

        tok_dict= usage_to_dict(output.token_usage)
        return {
    "answer": str(output),
    "usd_cost": gpt4o_mini_cost(tok_dict),
    "total_tokens": tok_dict["total_tokens"],
    }
