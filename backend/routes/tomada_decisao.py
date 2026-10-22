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