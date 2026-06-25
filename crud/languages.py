import pycountry
from sqlalchemy.orm import Session
from models.language import Language

# get the language record
def get_languages(db: Session) -> list[dict]:
    rows = db.query(Language.id, Language.name, Language.code).all()
    return [{"id": str(r.id), "name": r.name, "code": r.code} for r in rows]

# check if language exists
def language_exists(db: Session, name: str) -> bool:
    return db.query(Language.id).filter(Language.name.ilike(name)).first() is not None

# create new record in languages table
def create_language(db: Session, name: str) -> dict:
    if language_exists(db, name):
        raise ValueError(f"Language '{name}' already exists")

    lang = pycountry.languages.get(name=name)
    if not lang:
        raise ValueError(f"Could not resolve ISO code for language: {name}")

    new_lang = Language(name=name, code=lang.alpha_2)
    db.add(new_lang)
    db.commit()
    db.refresh(new_lang)
    return {"id": str(new_lang.id), "name": new_lang.name, "code": new_lang.code}