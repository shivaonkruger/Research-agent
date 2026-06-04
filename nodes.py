
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from tavily import TavilyClient

from state import ResearchState
from prompts import SUMMARIZER_PROMPT, CRITIC_PROMPT

load_dotenv()

# =============================================================================
# CLIENTS
# =============================================================================

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1,
)

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# =============================================================================
# NODE 1: search_node
# =============================================================================

def search_node(state: ResearchState) -> dict:
    # CONCEPT: A node that calls an external API, not the LLM
    # ---------------------------------------------------------
    # Nodes don't have to call the LLM. They can do anything:
    # query a database, call an API, run a script, read a file.
    # The graph doesn't care what happens inside a node — it only
    # cares about what the node returns to state.
    #
    # Tavily's search() returns a list of result dicts, each with:
    #   - title: page title
    #   - url: source URL
    #   - content: extracted text snippet (Tavily optimizes this for LLMs)
    #
    # max_results=6 gives the summarizer enough material without overwhelming
    # the context window. Adjust based on question complexity.

    question = state["question"]

    response = tavily.search(
        query=question,
        max_results=6,
        search_depth="advanced",   # "advanced" = Tavily fetches full page content
                                   # "basic" = just snippets, faster but thinner
    )

    results = response.get("results", [])

    # Normalize to only the fields we need — avoids passing raw Tavily
    # response structure (which has extra fields) into our clean state
    cleaned = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        }
        for r in results
    ]

    return {"search_results": cleaned}


# =============================================================================
# NODE 2: summarizer_node
# =============================================================================

def summarizer_node(state: ResearchState) -> dict:
    question = state["question"]
    search_results = state["search_results"]

    # Format search results into a readable block for the LLM
    # Each result gets its source labelled so the model can cite it
    formatted_results = ""
    for i, result in enumerate(search_results, 1):
        formatted_results += (
            f"[Source {i}] {result['title']}\n"
            f"URL: {result['url']}\n"
            f"Content: {result['content']}\n\n"
        )

    user_message = (
        f"Research Question: {question}\n\n"
        f"Search Results:\n{formatted_results}\n"
        f"Write a comprehensive summary of these search results."
    )

    response = llm.invoke([
        SystemMessage(content=SUMMARIZER_PROMPT),
        HumanMessage(content=user_message),
    ])

    return {"summary": response.content}


# =============================================================================
# NODE 3: critic_node
# =============================================================================

def critic_node(state: ResearchState) -> dict:
    # CONCEPT: A node that reads multiple upstream fields
    # ----------------------------------------------------
    # The critic needs three things from state: the original question,
    # the search results (to check the summary's accuracy), and the
    # summary itself. This is why named state fields matter — if
    # everything was in a messages list, this node would have to parse
    # message content to find each piece.

    question = state["question"]
    search_results = state["search_results"]
    summary = state["summary"]

    formatted_results = ""
    for i, result in enumerate(search_results, 1):
        formatted_results += (
            f"[Source {i}] {result['title']}\n"
            f"Content: {result['content'][:500]}\n\n"  # truncated for context efficiency
        )

    user_message = (
        f"Original Question: {question}\n\n"
        f"Search Results (for accuracy checking):\n{formatted_results}\n"
        f"Summary to critique:\n{summary}\n\n"
        f"Provide your critique and then write the improved final response."
    )

    response = llm.invoke([
        SystemMessage(content=CRITIC_PROMPT),
        HumanMessage(content=user_message),
    ])

    raw = response.content

    # Parse the two sections out of the critic's response
    # The prompt enforces "CRITIQUE:\n...\nFINAL RESPONSE:\n..." structure
    critique = ""
    final_response = ""

    if "FINAL RESPONSE:" in raw:
        parts = raw.split("FINAL RESPONSE:", 1)
        critique = parts[0].replace("CRITIQUE:", "").strip()
        final_response = parts[1].strip()
    else:
        # Fallback: if the model didn't follow the format, treat all as final
        critique = "Could not parse critique section."
        final_response = raw.strip()

    return {
        "critique": critique,
        "final_response": final_response,
    }