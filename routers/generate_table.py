from fastapi import APIRouter
from graphs.models import GenerateTableRequest

router = APIRouter(tags=["generate-table"])

@router.post("/api/generate-table")
def generate_tables(body: GenerateTableRequest):
    return {"table_html": f"Here will be the tables for rule {body.grammar_rule_id}"}
