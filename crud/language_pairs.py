from sqlalchemy.orm import Session
from models.language_pairs import LanguagePair
from models.language import Language


def get_language_code(db: Session, language_id: str) -> str:
    """Get language code by language ID"""
    language = db.query(Language).filter(Language.id == language_id).first()
    return language.code if language else "Unknown"


def get_language_pairs(db: Session) -> list[dict]:
    pairs = db.query(LanguagePair).all()
    result = []
    for p in pairs:
        native = db.query(Language).filter(Language.id == p.native_language_id).first()
        target = db.query(Language).filter(Language.id == p.target_language_id).first()
        result.append({
            "pair_id": str(p.pair_id),
            "native_name": native.name if native else "Unknown",
            "native_code": get_language_code(db, p.native_language_id),
            "target_name": target.name if target else "Unknown",
            "target_code": get_language_code(db, p.target_language_id),
        })
    return result


def pair_exists(db: Session, native_id: str, target_id: str) -> bool:
    return (
        db.query(LanguagePair.pair_id)
        .filter(
            LanguagePair.native_language_id == native_id,
            LanguagePair.target_language_id == target_id,
        )
        .first()
        is not None
    )


def create_language_pair(db: Session, native_id: str, target_id: str) -> dict:
    if native_id == target_id:
        raise ValueError("Native and studied language must be different")

    if pair_exists(db, native_id, target_id):
        raise ValueError("This language pair already exists")

    pair = LanguagePair(native_language_id=native_id, target_language_id=target_id)
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return {"pair_id": str(pair.pair_id)}

def delete_language_pair_by_id(db: Session, pair_id: str) -> bool:
    pair = db.query(LanguagePair).filter(LanguagePair.pair_id == pair_id).first()
    if pair is None:
        return False

    db.delete(pair)
    db.commit()
    return True