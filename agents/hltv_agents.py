# furiachat/agents/hltv_agents.py
"""HLTV agents e tasks para o Pantera‑Bot.

• **HLTVScraperTool** – wrapper finíssimo sobre utilitário de raspagem.
• **build_pantera_agent()** – cria o agente principal que usa o scraper
  para responder perguntas factuais sobre a FURIA.
• **run_pantera_task()** – função helper que recebe `question` e retorna
  dicionário {answer, tokens, usd_cost} – pronto p/ UI Streamlit.

O modelo utilizado é gpt‑3.5‑turbo, mas pode ser alterado via kwargs.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any

from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool

from furiachat.src.furiachat.tools.hltv_scraper import (
    fetch_html,
    parse_team_overview,
    parse_match_summary,
)
from furiachat.utils.usage import usage_to_dict
from furiachat.utils.cost import gpt4o_mini_cost

# ─────────────────────  Tool  ────────────────────── #


class HLTVToolInput(BaseModel):
    url: str = Field(..., description="URL pública da HLTV a ser raspada")


class HLTVScraperTool(BaseTool):
    """Tool genérica: baixa URL HLTV e devolve JSON parseado.

    Delega a heurística do parser pela rota da URL.
    """

    name: str = "hltv_scraper"
    description: str = (
        "Raspa páginas da HLTV relacionadas ao time FURIA e devolve JSON com dados estruturados"
    )
    args_schema: type = HLTVToolInput

    def _run(self, url: str) -> str:  # type: ignore[override]
        html = fetch_html(url)
        if "/team/" in url:
            data = parse_team_overview(html, url)
        elif "/matches/" in url:
            data = parse_match_summary(html, url)
        else:
            data = {"url": url, "raw_html": html}
        return json.dumps(data, ensure_ascii=False)


# ─────────────────────  Agent builder  ────────────────────── #

def build_pantera_agent(openai_api_key: str, model: str = "gpt-3.5-turbo") -> Agent:
    """Cria agente com o HLTVScraperTool embutido."""

    os.environ["OPENAI_API_KEY"] = openai_api_key
    return Agent(
        role="Pantera‑Analista",
        goal=(
            "Responder perguntas sobre o time de CS da FURIA usando apenas fatos "
            "raspados da HLTV (roster, partidas, estatísticas, notícias)."
        ),
        backstory=(
            "Você é um bot apaixonado por e‑sports que conhece a estrutura da HLTV. "
            "Quando necessário, chama o HLTVScraperTool para obter dados atualizados."
        ),
        tools=[HLTVScraperTool()],
        allow_delegation=False,
        verbose=False,
        max_iter=4,
        llm_config={
            "model": model,
            "temperature": 0,
        },
    )


# ─────────────────────  Task runner  ────────────────────── #

def run_pantera_task(question: str, openai_api_key: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Executa um único ciclo pergunta→resposta usando CrewAI."""

    agent = build_pantera_agent(openai_api_key, model)

    task = Task(
        description=(
            f"Responda à pergunta a seguir em português, citando a URL de onde o dado foi extraído. "
            f"Pergunta: {question}"
        ),
        expected_output="Resposta curta em Markdown, com link fonte entre parênteses.",
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()

    # Extrair métricas de uso
    tok_dict = usage_to_dict(result.token_usage)
    usd_cost = gpt4o_mini_cost(tok_dict)

    return {
        "answer": str(result),
        "usd_cost": usd_cost,
        "total_tokens": tok_dict["total_tokens"],
    }
