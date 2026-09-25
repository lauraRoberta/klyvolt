"""
Endpoints GET e POST para a tabela decisao.
"""

from fastapi import APIRouter, Depends, status
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