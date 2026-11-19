from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from schemas_update import EmpresaUpdate
from seguranca import Sessao, exigir_funcao, sessao_atual

router = APIRouter(
    prefix="/empresas",
    tags=["Empresa"]
)


# O cadastro de empresa agora é público e fica em POST /auth/registrar
# (cria a empresa e o primeiro administrador). Aqui ele fica fechado.
@router.post("")
def criar_empresa():
    raise HTTPException(
        status_code=403,
        detail="Novas empresas são cadastradas na tela pública (Cadastrar empresa)."
    )


@router.get("", response_model=list[schemas.EmpresaResponse])
def listar_empresas(
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db)
):
    # cada empresa enxerga só a própria
    empresa = db.get(models.Empresa, sessao.id_empresa)
    return [empresa] if empresa is not None else []


def buscar_empresa_ou_404(db: Session, id_empresa: int, sessao: Sessao) -> models.Empresa:
    obj = db.get(models.Empresa, id_empresa)
    if obj is None or obj.id_empresa != sessao.id_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrado(a)")
    return obj


@router.get("/{id_empresa}", response_model=schemas.EmpresaResponse)
def obter_empresa(
    id_empresa: int,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db)
):
    return buscar_empresa_ou_404(db, id_empresa, sessao)


@router.put("/{id_empresa}", response_model=schemas.EmpresaResponse)
def atualizar_empresa(
    id_empresa: int,
    dados: EmpresaUpdate,
    sessao: Sessao = Depends(exigir_funcao("Administrador")),
    db: Session = Depends(get_db)
):
    obj = buscar_empresa_ou_404(db, id_empresa, sessao)
    valores = dados.model_dump()
    valores.pop("cnpj", None)           # o CNPJ não pode ser alterado
    valores.pop("senha_empresa", None)  # a senha é a do usuário (tela Usuário), não a da empresa
    for campo, valor in valores.items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj