from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/tomadas-decisao",
    tags=["Tomada de Decisão"]
)


@router.post(
    "",
    response_model=schemas.TomadaDecisaoResponse
)
def criar_tomada_decisao(
    tomada: schemas.TomadaDecisaoCreate,
    db: Session = Depends(get_db)
):
    # Antes de inserir, confere se a decisão informada existe
    decisao = (
        db.query(models.Decisao)
        .filter(models.Decisao.id_decisao == tomada.id_decisao)
        .first()
    )

    if decisao is None:
        raise HTTPException(
            status_code=404,
            detail="Decisão não encontrada"
        )

    nova_tomada = models.TomadaDecisao(
        id_decisao=tomada.id_decisao,
        valor_referencia=tomada.valor_referencia,
        status_execucao=tomada.status_execucao,
        observacao=tomada.observacao,
        id_leitura=tomada.id_leitura,
        id_consumo=tomada.id_consumo
    )

    db.add(nova_tomada)
    db.commit()
    db.refresh(nova_tomada)

    return {
        "id_tomada_decisao": nova_tomada.id_tomada_decisao,
        "data_tomada_decisao": nova_tomada.data_tomada_decisao,
        "decisao": decisao.nome_decisao,
        "valor_referencia": nova_tomada.valor_referencia,
        "status_execucao": nova_tomada.status_execucao,
        "observacao": nova_tomada.observacao,
        "id_leitura": nova_tomada.id_leitura,
        "id_consumo": nova_tomada.id_consumo
    }


@router.get(
    "",
    response_model=list[schemas.TomadaDecisaoResponse]
)
def listar_tomadas_decisao(
    db: Session = Depends(get_db)
):
    tomadas = db.query(models.TomadaDecisao).all()

    return [
        {
            "id_tomada_decisao": t.id_tomada_decisao,
            "data_tomada_decisao": t.data_tomada_decisao,
            "decisao": t.decisao.nome_decisao,
            "valor_referencia": t.valor_referencia,
            "status_execucao": t.status_execucao,
            "observacao": t.observacao,
            "id_leitura": t.id_leitura,
            "id_consumo": t.id_consumo
        }
        for t in tomadas
    ]


@router.get("/{id_tomada_decisao}", response_model=schemas.TomadaDecisaoResponse)
def buscar_tomada_decisao(id_tomada_decisao: int, db: Session = Depends(get_db)):
    tomada = buscar_ou_404(db, models.TomadaDecisao, id_tomada_decisao, "Tomada de decisão")
    return _resposta_tomada(tomada)
 
 
@router.put("/{id_tomada_decisao}", response_model=schemas.TomadaDecisaoResponse)
def atualizar_tomada_decisao(id_tomada_decisao: int, dados: schemas.TomadaDecisaoCreate, db: Session = Depends(get_db)):
    tomada = buscar_ou_404(db, models.TomadaDecisao, id_tomada_decisao, "Tomada de decisão")
    buscar_ou_404(db, models.Decisao, dados.id_decisao, "Decisão")  # a decisão escolhida precisa existir
    for campo, valor in dados.model_dump().items():
        setattr(tomada, campo, valor)
    salvar_ou_409(db, "A leitura ou o consumo informado não existe.")
    db.refresh(tomada)
    return _resposta_tomada(tomada)
 
 
@router.delete("/{id_tomada_decisao}", status_code=204)
def excluir_tomada_decisao(id_tomada_decisao: int, db: Session = Depends(get_db)):
    tomada = buscar_ou_404(db, models.TomadaDecisao, id_tomada_decisao, "Tomada de decisão")
    db.delete(tomada)
    salvar_ou_409(db, "Não foi possível excluir a tomada de decisão.")
    return Response(status_code=204)
 