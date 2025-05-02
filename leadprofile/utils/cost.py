# cost.py

def gpt4o_mini_cost(usage: dict) -> float:
    """
    Calcula o custo em dólares para GPT-4o-mini.
    usage = {'prompt_tokens': int, 'completion_tokens': int}
    """
    PRICE_PROMPT = 0.0005 / 1000   # USD por token
    PRICE_COMPLETION = 0.0015 / 1000

    prompt_cost = usage["prompt_tokens"] * PRICE_PROMPT
    completion_cost = usage["completion_tokens"] * PRICE_COMPLETION
    return round(prompt_cost + completion_cost, 6)   # 6 casas decimais
