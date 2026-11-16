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


def buscar_leitura_ou_404(db: Session, id_leitura: int) -> models.Leitura:
    obj = db.get(models.Leitura, id_leitura)
    if obj is None:
        raise HTTPException(status_code=404, detail="Leitura não encontrado(a)")
    return obj
 
 
@router.get("/{id_leitura}", response_model=schemas.LeituraResponse)
def obter_leitura(id_leitura: int, db: Session = Depends(get_db)):
    return buscar_leitura_ou_404(db, id_leitura)
 
 
@router.put("/{id_leitura}", response_model=schemas.LeituraResponse)
def atualizar_leitura(id_leitura: int, dados: schemas.LeituraCreate, db: Session = Depends(get_db)):
    obj = buscar_leitura_ou_404(db, id_leitura)
    for campo, valor in dados.model_dump().items():
        if campo == "data_leitura" and valor is None:
            continue  # coluna obrigatória: mantém a data atual
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj
