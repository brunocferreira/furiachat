# location_agent.py
"""
Agent & Task CrewAI que chama o ddd_scraper                                     ✓
"""
import os
import re
import json
# CrewAI docs :contentReference[oaicite:4]{index=4}
from typing import Dict, Any, List
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from leadprofile.utils.cost import gpt4o_mini_cost
from leadprofile.utils.usage import usage_to_dict

from leadprofile.src.leadprofile.tools.ddd_scraper import scrape_claro_ddd


class LocationResult(BaseModel):
    state: str
    cities: List[str]
    url: str

# ─────────────────────  Custom Tool  ───────────────────── #


class DDDScraperInput(BaseModel):
    ddd: str = Field(..., description="Código DDD brasileiro de 2 dígitos")


class DDDScraperTool(BaseTool):
    name: str = "ddd_scraper"
    description: str = "Retorna estado e cidades atendidas pelo DDD"
    # ou: args_schema: DDDScraperInput = DDDScraperInput
    args_schema: type = DDDScraperInput

    def _run(self, ddd: str) -> str:
        state, cities, url = scrape_claro_ddd(ddd)
        return json.dumps(
            {"state": state, "cities": cities, "url": url},
            ensure_ascii=False,
        )

# ─────────────────────  Funções públicas  ───────────────────── #


def _extract_ddd(phone: str) -> str:
    m = re.search(r"\(?0?(\d{2})\)?", phone)
    if not m:
        raise ValueError("Telefone inválido – DDD não encontrado")
    return m.group(1)


# --- Agent ---------------------------------------------------------------- #


def build_location_agent(openai_api_key: str):
    os.environ["OPENAI_API_KEY"] = openai_api_key
    locator = Agent(
        role="Identificador de Localidade",
        goal="Descobrir estado e cidades de um telefone brasileiro a partir do DDD",
        backstory=("Você é especialista em telefonia brasileira e usa o blog da Claro "
                   "para obter a lista oficial de cidades de cada DDD."),
        tools=[DDDScraperTool()],
        allow_delegation=False,
        verbose=False,
        # CrewAI param :contentReference[oaicite:5]{index=5}
        max_iter=3
    )
    return locator

# --- Tarefa & Execução ----------------------------------------------------- #


def run_location_task(name: str, phone: str, openai_api_key: str) -> Dict[str, Any]:
    os.environ["OPENAI_API_KEY"] = openai_api_key

    locator = Agent(
        role="Identificador de Localidade",
        goal="Descobrir estado e cidades de um DDD brasileiro",
        backstory=("Você é especialista em telefonia brasileira e usa o "
                   "blog da Claro para obter informações oficiais de DDD."),
        tools=[DDDScraperTool()],
        max_iter=3,
        verbose=False,
        allow_delegation=False,
    )

    # locator = build_location_agent(openai_api_key)
    # Regex phone → DDD :contentReference[oaicite:6]{index=6}
    # ddd_match = re.search(r"\(?0?(\d{2})\)?", phone)
    # if not ddd_match:
    #     raise ValueError("Telefone inválido para extrair DDD.")

    # ddd = ddd_match.group(1)
    ddd = _extract_ddd(phone)

    task = Task(
        description=(f"Extraia estado e lista de cidades do DDD {ddd}. "
                     "Devolva saída JSON com chaves state, cities, url."),
        expected_output="JSON válido com state, cities e url",
        agent=locator,
        output_json=LocationResult
    )

    crew = Crew(agents=[locator], tasks=[task], verbose=True)
    crew_output = crew.kickoff(inputs={"name": name, "phone": phone})
    # --------------------------------------------------------------
    # 3 formas válidas – escolha UMA:
    # --------------------------------------------------------------
    # 1)  usar .json()
    # json_str = crew_output.json()

    # 2) se não houver .json() disponível (versão antiga → use str)
    # json_str = str(crew_output)

    # 3) ou converter direto p/ dict
    data = crew_output.to_dict()
    # --------------------------------------------------------------
    # data = json.loads(json_str)

    # 4. Uso de tokens e o custo ─────────────────────────────────────────
    tok_dict = usage_to_dict(crew_output.token_usage)
    usd_cost = gpt4o_mini_cost(tok_dict)
    total_tokens = tok_dict["total_tokens"]

    # Relatório Markdown simples
    md_report = f"""
### Identificação de Localidade

* **Nome:** {name}
* **Telefone:** {phone}
* **DDD:** {ddd}
* **Estado:** {data['state']}
* **Cidades ({len(data['cities'])}):** {", ".join(data['cities'])}

_Fonte:_ {data['url']}
"""
    return {
        "markdown": md_report,
        "ddd": ddd,
        "data": data,
        "usd_cost": usd_cost,
        "total_tokens": total_tokens
    }
