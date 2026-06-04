from typing import Annotated
from typing_extensions import TypedDict
import operator


class ResearchState(TypedDict):
    question: str
    search_results: Annotated[list[dict], operator.add]
    summary: str
    critique: str
    final_response: str