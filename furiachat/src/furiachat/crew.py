# leadprofile/src/leadprofile/crew.py

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel
from typing import List, Dict

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

# Pydantic esquema para validar a resposta JSON ----------------------------


class LocationResult(BaseModel):
    state: str
    cities: List[str]
    url: str

# --------------------------------------------------------------------------


@CrewBase
class Leadprofile():
    """
    Crew responsável apenas pelo passo de Identificação de Localidade.
    """

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools

    @agent
    def location_identifier(self) -> Agent:
        return Agent(
            config=self.agents_config['location_identifier'],
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task

    @task
    def ddd_task(self) -> Task:
        return Task(
            config=self.tasks_config['ddd_task'],
            # output_file='relatorio.md'
            output_json=LocationResult
        )

    # ---------------- Crew --------------------
    @crew
    def crew(self) -> Crew:
        """Creates the Leadprofile crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )

    # ---------------- Helper: imprime fluxo ----
#     def print_flow(self) -> str:
#         """
#         Retorna um diagrama Mermaid do fluxo da crew — útil para README.
#         """
#         return """
# ```mermaid
# flowchart TD
#     A((Start)) --> B[Extrair DDD<br/>(regex no telefone)]
#     B --> C[Tool: ddd_scraper<br/>raspa blog Claro]
#     C --> D[Location Identifier<br/>(LLM valida JSON)]
#     D --> E((End))
# ```"""
