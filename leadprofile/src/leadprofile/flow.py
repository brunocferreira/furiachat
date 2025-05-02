"""
LeadProfileFlow ― orquestra todo o pipeline em passos declarativos.
"""
from crewai import Flow
from crewai.flow.flow import start, listen
from typing import List, Dict
from leadprofile.crew import Leadprofile
from leadprofile.src.leadprofile.crew import Leadprofile
from leadprofile.utils.cost import gpt4o_mini_cost
from leadprofile.utils.usage import usage_to_dict

# ─────────────────────────────── FLOW ──────────────────────────────────────


class LeadProfileFlow(Flow):

    # 1) INPUT -----------------------------------------------------------------
    @start()
    def receive_leads(self) -> List[Dict]:
        """
        Recebe (ou simula) leads em formato [{name, phone}].
        Em produção, você pode trocar por leitura de fila/DB/HTTP.
        """
        return [
            {"name": "Maria Silva", "phone": "31988775544"},
            {"name": "Carlos Souza", "phone": "67987654321"},
        ]

    # 2) RUN CREW FOR EACH LEAD ------------------------------------------------
    @listen(receive_leads)
    def identify_location(self, leads: List[Dict]):
        """
        Executa o Leadprofile crew para cada lead.
        Retorna lista de objetos CrewOutput.
        """
        crew = Leadprofile().crew()
        results = crew.kickoff_for_each(inputs_list=[
            {"name": lead["name"], "phone": lead["phone"]}
            for lead in leads
        ])
        return results

    # 3) POST‑PROCESS: custo + estrutura dict ----------------------------------
    @listen(identify_location)
    def enrich_results(self, crew_outputs):
        enriched = []
        for out in crew_outputs:
            data = out.to_dict()            # state, cities, url
            tok_dict = usage_to_dict(out.token_usage)
            usd_cost = gpt4o_mini_cost(tok_dict)

            enriched.append({
                "name":        out.inputs["name"],
                "phone":       out.inputs["phone"],
                "ddd":         data["url"].split("ddd-")[1],
                "state":       data["state"],
                "cities":      data["cities"],
                "url":         data["url"],
                "usd_cost":    usd_cost,
                "total_tokens": tok_dict["total_tokens"]
            })
        self.state["results"] = enriched
        return enriched

    # 4) ARMAZENAR (exemplo simples) ------------------------------------------
    @listen(enrich_results)
    def store(self, enriched):
        """
        Aqui você salvava no banco; por enquanto só devolve.
        """
        return enriched
