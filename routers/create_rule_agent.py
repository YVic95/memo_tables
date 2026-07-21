import json
import uuid
import datetime
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from crud.language_pairs import get_language_pair_by_id
from graphs.suggest_rules_graph import graph as propose_rules_graph
from graphs.initial_rule_graph import graph as initial_rule_graph

router = APIRouter(tags=["create-rule-agent"])

NODE_ORDER = ["categorize", "persist_rule", "translate_rule", "persist_translation", "generate_content"]

def json_safe(obj):
    """Recursively convert non-JSON-serializable objects (UUID, datetime, date)
    into JSON-safe equivalents so they can be passed to json.dumps."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {key: json_safe(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_safe(item) for item in obj]
    return obj

def sse_event(event_type: str, data: dict) -> str:
    """Format a single Server-Sent Event, ensuring the payload is JSON-safe."""
    return f"event: {event_type}\ndata: {json.dumps(json_safe(data))}\n\n"


class AgentRequest(BaseModel):
    type: str
    language_pair_id: str
    title: Optional[str] = None
    explanation: Optional[str] = None

@router.post("/api/create-rule-agent")
async def call_agent(
    body: AgentRequest,
    db: Annotated[Session, Depends(get_db)],
):
    pair = get_language_pair_by_id(db, body.language_pair_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Language pair not found")

    if body.type == "propose_missing_rules":
        result = propose_rules_graph.invoke({
            "native_language": pair["native_name"],
            "target_language": pair["target_name"],
            "proposed_rules": [],
        })
        return {"rules": result["proposed_rules"]}

    if body.type == "initial_rule":
        if not body.title or not body.explanation:
            raise HTTPException(status_code=400, detail="title and explanation are required")

        pair_data = {
            "native_language": pair["native_name"],
            "target_language": pair["target_name"],
            "native_language_id": pair["native_language_id"],
            "target_language_id": pair["target_language_id"],
        }

        def event_stream():
            session = SessionLocal()
            try:
                graph_input = {
                    "db": session,
                    "rule_title": body.title,
                    "rule_explanation": body.explanation,
                    **pair_data,
                }

                completed = set()
                generate_content_result = {}

                yield sse_event("node_start", {"node": NODE_ORDER[0]})

                for chunk in initial_rule_graph.stream(graph_input, stream_mode="updates"):
                    for node_name, state_update in chunk.items():
                        if node_name == "generate_content":
                            generate_content_result = state_update or {}

                        yield sse_event("node_complete", {"node": node_name})
                        completed.add(node_name)

                        next_idx = NODE_ORDER.index(node_name) + 1
                        if next_idx < len(NODE_ORDER):
                            yield sse_event("node_start", {"node": NODE_ORDER[next_idx]})

                yield sse_event("done", {
                    "grammar_rule_id": generate_content_result.get("grammar_rule_id", ""),
                    "full_content": generate_content_result.get("full_content", ""),
                })
                
            except Exception:
                yield sse_event("error", {
                    "message": "Something went wrong while generating the rule. Please try again.",
                })
            finally:
                session.close()

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported request type: {body.type}",
        )