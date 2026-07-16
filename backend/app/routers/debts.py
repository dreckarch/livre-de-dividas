from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/debts", tags=["debts"])


@router.get("/", response_model=list[schemas.DebtOut])
def list_debts(db: Session = Depends(get_db)):
    return db.query(models.DebtRecord).all()


@router.post("/", response_model=schemas.DebtOut)
def create_debt(payload: schemas.DebtCreate, db: Session = Depends(get_db)):
    item = models.DebtRecord(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{debt_id}", response_model=schemas.DebtOut)
def update_debt(debt_id: str, payload: schemas.DebtCreate, db: Session = Depends(get_db)):
    item = db.query(models.DebtRecord).filter(models.DebtRecord.id == debt_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Dívida não encontrada")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{debt_id}")
def delete_debt(debt_id: str, db: Session = Depends(get_db)):
    item = db.query(models.DebtRecord).filter(models.DebtRecord.id == debt_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Dívida não encontrada")
    db.delete(item)
    db.commit()
    return {"ok": True}
