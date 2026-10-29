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



@router.get("/{id_decisao}", response_model=schemas.DecisaoResponse)
def buscar_decisao(id_decisao: int, db: Session = Depends(get_db)):
    decisao = db.get(models.Decisao, id_decisao)
    if decisao is None:
        raise HTTPException(status_code=404, detail="Decisão não encontrada.")
    return decisao
 
 
@router.put("/{id_decisao}", response_model=schemas.DecisaoResponse)
def atualizar_decisao(id_decisao: int, dados: schemas.DecisaoCreate, db: Session = Depends(get_db)):
    decisao = db.get(models.Decisao, id_decisao)
    if decisao is None:
        raise HTTPException(status_code=404, detail="Decisão não encontrada.")
    for campo, valor in dados.model_dump().items():
        setattr(decisao, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível salvar a decisão.")
    db.refresh(decisao)
    return decisao
 
 
@router.delete("/{id_decisao}", status_code=204)
def excluir_decisao(id_decisao: int, db: Session = Depends(get_db)):
    decisao = db.get(models.Decisao, id_decisao)
    if decisao is None:
        raise HTTPException(status_code=404, detail="Decisão não encontrada.")
    # A FK de tomada_decisao não tem ondelete: se a decisão já foi usada, o banco recusaria.
    em_uso = (
        db.query(models.TomadaDecisao)
        .filter(models.TomadaDecisao.id_decisao == id_decisao)
        .first()
    )
    if em_uso is not None:
        raise HTTPException(
            status_code=409,
            detail="Esta decisão já foi usada em tomadas de decisão e não pode ser excluída.",
        )
    db.delete(decisao)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível excluir a decisão.")
    return Response(status_code=204)
 