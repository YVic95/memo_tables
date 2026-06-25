from sqlalchemy.orm import Session
from models.language_pairs import LanguagePair
from models.language import Language


def get_language_pairs(db: Session) -> list[dict]:
    pairs = db.query(LanguagePair).all()
    result = []
    for p in pairs:
        native = db.query(Language).filter(Language.id == p.native_language_id).first()
        target = db.query(Language).filter(Language.id == p.target_language_id).first()
        result.append({
            "pair_id": str(p.pair_id),
            "native_name": native.name if native else "Unknown",
            "target_name": target.name if target else "Unknown",
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