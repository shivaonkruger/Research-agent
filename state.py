from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator

class ResearchState(TypedDict):
    question: str
    search_results: Annotated[list[dict], operator.add]
    summary: str
    critique: str
    final_response: str
    messages: Annotated[list[BaseMessage], add_messages]
