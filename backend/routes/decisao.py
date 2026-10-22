from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/decisoes",
    tags=["Decisão"]
)


@router.post(
    "",
    response_model=schemas.DecisaoResponse
)
def criar_decisao(
    decisao: schemas.DecisaoCreate,
    db: Session = Depends(get_db)
):
    nova_decisao = models.Decisao(
        nome_decisao=decisao.nome_decisao,
        descricao_decisao=decisao.descricao_decisao,
        criterio_acionado=decisao.criterio_acionado,
        operador=decisao.operador,
        limite_referencia=decisao.limite_referencia,
        unidade_limite=decisao.unidade_limite
    )
    
    db.add(nova_decisao)
    db.commit()
    db.refresh(nova_decisao)

    return nova_decisao


@router.get(
    "",
    response_model=list[schemas.DecisaoResponse]
)
def listar_decisoes(
    db: Session = Depends(get_db)
):
    return db.query(models.Decisao).all() 
