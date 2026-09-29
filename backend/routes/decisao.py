"""
Endpoints GET e POST para a tabela decisao.
"""

from http.client import HTTPException
from backend import schemas
from backend import models
from fastapi import APIRouter, Depends, status # type: ignore
from sqlalchemy.orm import Session

from database import get_db
from models import Decisao
from schemas import DecisaoCreate, DecisaoResponse

router = APIRouter(prefix="/decisoes", tags=["Decisoes"])

@router.get("/", response_model=list[DecisaoResponse])
def listar_decisoes(db: Session = Depends(get_db)):
    return db.query(Decisao).all()



@router.post("/", response_model=DecisaoResponse, status_code=status.HTTP_201_CREATED)
def criar_decisao(dados: DecisaoCreate, db: Session = Depends(get_db)):
    decisao = Decisao(
        nome_decisao=dados.nome_decisao,
        descricao_decisao=dados.descricao_decisao,
        criterio_acionado=dados.criterio_acionado,
        operador=dados.operador,
        limite_referencia=dados.limite_referencia,
        unidade_limite=dados.unidade_limite,
    )
    db.add(decisao)
    db.commit()
    db.refresh(decisao)
    return decisao

# PUT — atualizar (substituição completa)
@router.put("/{decisao_id}", response_model=schemas.DecisaoResponse)
def atualizar_decisao(decisao_id: int,
                      dados: schemas.DecisaoCreate,
                      db: Session = Depends(get_db)):
    decisao = db.query(models.Decisao).filter(models.Decisao.id == decisao_id).first()
    if not decisao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decisão não encontrada"
        )

    for campo, valor in dados.model_dump().items():
        setattr(decisao, campo, valor)

    db.commit()
    db.refresh(decisao)
    return decisao

# DELETE — remover
@router.delete("/{decisao_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_decisao(decisao_id: int, db: Session = Depends(get_db)):
    decisao = db.query(models.Decisao).filter(models.Decisao.id == decisao_id).first()
    if not decisao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decisão não encontrada"
        )

    db.delete(decisao)
    db.commit()
    return None