# furiachat/utils/usage.py
from typing import Union, Dict, TYPE_CHECKING, Any

if TYPE_CHECKING:
    # forward‑ref para tipagem – não carrega nada em runtime
    from openai.types import CompletionUsage as UsageMetrics
else:
    UsageMetrics = Any  # type: ignore


def usage_to_dict(usage_obj: Union[dict, "UsageMetrics"]) -> Dict[str, int]:
    ...

    """
    Converte UsageMetrics ou dict para um dicionário padrão
    {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int}
    """
    if isinstance(usage_obj, dict):
        return usage_obj

    # Versão nova (UsageMetrics) → tem atributos
    return {
        "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0),
        "completion_tokens": getattr(usage_obj, "completion_tokens", 0),
        "total_tokens": getattr(usage_obj, "total_tokens", 0),
    }
