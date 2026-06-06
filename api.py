
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from agent import graph

load_dotenv()

app = FastAPI(title="Research Workflow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    question: str
    thread_id: str 

STAGE_LABELS = {
    "search_node":     "Searching the web...",
    "summarizer_node": "Summarizing results...",
    "critic_node":     "Critiquing & refining...",
}


async def stream_pipeline(question: str, thread_id: str):
    initial_state = {"question": question, "search_results": []}
    config = {"configurable": {"thread_id": thread_id}}

    try:
        for chunk in graph.stream(initial_state, config=config):
            node_name = list(chunk.keys())[0]
            node_output = chunk[node_name]

            # Stage start event — tells UI which node just completed
            yield json.dumps({
                "type": "stage",
                "stage": node_name,
                "label": STAGE_LABELS.get(node_name, node_name),
            }) + "\n"

            # Node-specific data events
            if node_name == "search_node":
                results = node_output.get("search_results", [])
                yield json.dumps({
                    "type": "results",
                    "search_results": [
                        {"title": r["title"], "url": r["url"]}
                        for r in results
                    ],
                }) + "\n"

            elif node_name == "summarizer_node":
                yield json.dumps({
                    "type": "summary",
                    "content": node_output.get("summary", ""),
                }) + "\n"

            elif node_name == "critic_node":
                yield json.dumps({
                    "type": "critique",
                    "content": node_output.get("critique", ""),
                }) + "\n"
                yield json.dumps({
                    "type": "final",
                    "content": node_output.get("final_response", ""),
                }) + "\n"

    except Exception as e:
        yield json.dumps({"type": "error", "content": str(e)}) + "\n"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/research")
async def research(request: ResearchRequest):
    return StreamingResponse(
        stream_pipeline(request.question, request.thread_id), 
        media_type="text/plain"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)