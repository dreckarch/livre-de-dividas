from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/income", tags=["income"])


@router.get("/", response_model=list[schemas.IncomeOut])
def list_income(db: Session = Depends(get_db)):
    return db.query(models.IncomeSource).all()


@router.post("/", response_model=schemas.IncomeOut)
def create_income(payload: schemas.IncomeCreate, db: Session = Depends(get_db)):
    item = models.IncomeSource(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{income_id}")
def delete_income(income_id: str, db: Session = Depends(get_db)):
    item = db.query(models.IncomeSource).filter(models.IncomeSource.id == income_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Renda não encontrada")
    db.delete(item)
    db.commit()
    return {"ok": True}
