from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from crud.rules import get_grammar_rule_by_id, append_rule_description, append_translation_description
from models.language import Language
from graphs.llm import llm
from langchain_core.prompts import PromptTemplate

router = APIRouter(tags=["save-rule"])

translate_content_prompt = PromptTemplate.from_template(
    "Translate the following grammar rule content into {target_language}:\n\n{content}"
)

class AppendContentRequest(BaseModel):
    content: str

@router.post("/api/grammar-rules/{grammar_rule_id}/append-content")
async def append_rule_content(
    grammar_rule_id: str,
    body: AppendContentRequest,
    db: Annotated[Session, Depends(get_db)],
):
    rule = get_grammar_rule_by_id(db, grammar_rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Grammar rule not found")

    # Append raw content to rule description (content is in native language,
    # same as the existing description field)
    append_rule_description(db, grammar_rule_id, body.content)

    # Look up target language name for LLM translation
    target_language = db.query(Language).filter(Language.id == rule.language_id).first()
    if target_language is None:
        raise HTTPException(status_code=404, detail="Target language not found")

    # Translate content from native → target language
    chain = translate_content_prompt | llm
    result = chain.invoke({
        "target_language": target_language.name,
        "content": body.content,
    })

    # Append translated content to translation description
    append_translation_description(db, grammar_rule_id, result.content)

    return {"success": True}
