"""Rotas de EMPRESA.

POST cria a empresa e a conta do administrador no Supabase Auth (cadastro
público). As demais rotas exigem login e só enxergam a empresa do usuário.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase_auth.errors import AuthError

from controller.auth import URL_ENTRAR, carregar_perfil, erro_auth, montar_sessao
from database import cliente_publico, executar, um_registro
from models.empresa import CadastroEmpresaResponse, EmpresaCreate, EmpresaResponse, EmpresaUpdate
from seguranca import Contexto, exigir_admin, usuario_atual

router = APIRouter(prefix="/empresas", tags=["Empresa"])

COLUNAS = "id_empresa,cnpj,nome_empresa,email_empresa,telefone_empresa,tarifa_kwh"


@router.post("", response_model=CadastroEmpresaResponse, status_code=status.HTTP_201_CREATED,
             summary="Cadastrar empresa e administrador")
def criar_empresa(empresa: EmpresaCreate):
    publico = cliente_publico()
    situacao = executar(publico.rpc("kv_verificar_cadastro", {"p_cnpj": empresa.cnpj, "p_email": empresa.email}))
    if situacao.get("cnpj_em_uso"):
        raise HTTPException(status_code=409, detail="Este CNPJ já está cadastrado.")
    if situacao.get("email_em_uso"):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    try:
        resposta = publico.auth.sign_up({
            "email": empresa.email,
            "password": empresa.senha,
            "options": {
                "email_redirect_to": URL_ENTRAR,
                # o trigger kv_handle_new_user cria a empresa e o administrador com estes dados
                "data": {
                    "kv_cadastro": "empresa", "cnpj": empresa.cnpj, "nome_empresa": empresa.nome_empresa,
                    "nome_usuario": empresa.nome_usuario, "telefone": empresa.telefone,
                },
            },
        })
    except AuthError as erro:
        raise erro_auth(erro) from erro
    usuario = resposta.user
    if usuario is not None and getattr(usuario, "identities", None) == []:
        # com confirmação de e-mail ativa, o Supabase não informa e-mail repetido
        raise HTTPException(status_code=409, detail="Este e-mail já possui conta.")
    if resposta.session:
        sessao = montar_sessao(resposta.session, carregar_perfil(resposta.session.access_token))
        return CadastroEmpresaResponse(confirmacao_pendente=False, mensagem="Empresa cadastrada.", sessao=sessao)
    return CadastroEmpresaResponse(
        confirmacao_pendente=True,
        mensagem=f"Empresa cadastrada! Enviamos um link de confirmação para {empresa.email}.",
    )


@router.get("", response_model=list[EmpresaResponse], summary="Listar empresas (somente a sua)")
def listar_empresas(contexto: Contexto = Depends(usuario_atual)):
    return executar(contexto.db.table("empresa").select(COLUNAS).order("id_empresa"))


@router.get("/{id_empresa}", response_model=EmpresaResponse, summary="Consultar empresa por ID")
def buscar_empresa(id_empresa: int, contexto: Contexto = Depends(usuario_atual)):
    return um_registro(executar(contexto.db.table("empresa").select(COLUNAS).eq("id_empresa", id_empresa)), "Empresa")


@router.put("/{id_empresa}", response_model=EmpresaResponse, summary="Atualizar dados e tarifa da empresa")
def atualizar_empresa(id_empresa: int, empresa: EmpresaUpdate, contexto: Contexto = Depends(exigir_admin)):
    linhas = executar(contexto.db.table("empresa").update(empresa.model_dump(mode="json"))
                      .eq("id_empresa", id_empresa).select(COLUNAS))
    return um_registro(linhas, "Empresa")


@router.delete("/{id_empresa}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Excluir a empresa e todos os seus dados")
def excluir_empresa(id_empresa: int, contexto: Contexto = Depends(exigir_admin)):
    um_registro(executar(contexto.db.table("empresa").delete().eq("id_empresa", id_empresa).select("id_empresa")), "Empresa")
    return None
