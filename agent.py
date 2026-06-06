from langgraph.graph import StateGraph, END
from state import ResearchState
from nodes import search_node, summarizer_node, critic_node
from langgraph.checkpoint.memory import MemorySaver  # NEW


def build_graph():
    graph = StateGraph(ResearchState)

    # Register nodes
    graph.add_node("search_node", search_node)
    graph.add_node("summarizer_node", summarizer_node)
    graph.add_node("critic_node", critic_node)

    # Entry point
    graph.set_entry_point("search_node")

    # Fixed linear edges — no conditionals
    graph.add_edge("search_node", "summarizer_node")
    graph.add_edge("summarizer_node", "critic_node")
    graph.add_edge("critic_node", END)
    
    checkpointer = MemorySaver()                  
    return graph.compile(checkpointer=checkpointer)   


graph = build_graph()