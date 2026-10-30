"""Rotas de USUARIO (equipe da empresa).

O administrador cadastra Operadores e Visualizadores: a API registra um convite
no banco e cria a conta no Supabase Auth; o trigger vincula a conta à empresa.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase_auth.errors import AuthError

from controller.auth import URL_ENTRAR, erro_auth
from database import cliente_publico, executar, um_registro
from models.usuario import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from seguranca import Contexto, exigir_admin, usuario_atual

router = APIRouter(prefix="/usuarios", tags=["Usuário"])

COLUNAS = "id_usuario,nome_usuario,email_usuario,tipo_usuario,id_empresa,ativo"


@router.get("", response_model=list[UsuarioResponse], summary="Listar usuários da empresa")
def listar_usuarios(contexto: Contexto = Depends(usuario_atual)):
    return executar(contexto.db.table("usuario").select(COLUNAS).order("nome_usuario"))


@router.get("/{id_usuario}", response_model=UsuarioResponse, summary="Consultar usuário por ID")
def buscar_usuario(id_usuario: int, contexto: Contexto = Depends(usuario_atual)):
    return um_registro(executar(contexto.db.table("usuario").select(COLUNAS).eq("id_usuario", id_usuario)), "Usuário")


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED,
             summary="Cadastrar membro da equipe (somente administrador)")
def criar_usuario(usuario: UsuarioCreate, contexto: Contexto = Depends(exigir_admin)):
    convite = um_registro(executar(contexto.db.table("convite_usuario").insert({
        "email": usuario.email_usuario, "nome_usuario": usuario.nome_usuario, "tipo_usuario": usuario.tipo_usuario,
    }).select("id_convite,codigo")), "Convite")

    def desfazer_convite():
        executar(contexto.db.table("convite_usuario").delete().eq("id_convite", convite["id_convite"]))

    try:
        resposta = cliente_publico().auth.sign_up({
            "email": usuario.email_usuario,
            "password": usuario.senha,
            "options": {"email_redirect_to": URL_ENTRAR,
                        "data": {"kv_cadastro": "convite", "codigo": convite["codigo"]}},
        })
    except AuthError as erro:
        desfazer_convite()
        raise erro_auth(erro) from erro
    criado = executar(contexto.db.table("usuario").select(COLUNAS).eq("email_usuario", usuario.email_usuario))
    if not criado:
        desfazer_convite()
        raise HTTPException(status_code=409, detail="Este e-mail já possui conta no sistema.")
    return {**criado[0], "confirmacao_pendente": resposta.session is None}


@router.put("/{id_usuario}", response_model=UsuarioResponse, summary="Atualizar nome, perfil ou situação")
def atualizar_usuario(id_usuario: int, usuario: UsuarioUpdate, contexto: Contexto = Depends(exigir_admin)):
    if id_usuario == contexto.id_usuario and (usuario.tipo_usuario != "Administrador" or not usuario.ativo):
        raise HTTPException(status_code=422, detail="Você não pode remover o seu próprio acesso de administrador.")
    linhas = executar(contexto.db.table("usuario").update(usuario.model_dump()).eq("id_usuario", id_usuario).select(COLUNAS))
    return um_registro(linhas, "Usuário")


@router.delete("/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover usuário da empresa")
def excluir_usuario(id_usuario: int, contexto: Contexto = Depends(exigir_admin)):
    if id_usuario == contexto.id_usuario:
        raise HTTPException(status_code=422, detail="Você não pode remover a sua própria conta.")
    linhas = executar(contexto.db.table("usuario").delete().eq("id_usuario", id_usuario).select("id_usuario"),
                      vinculo="Este usuário é responsável por setores. Troque o responsável antes de removê-lo.")
    um_registro(linhas, "Usuário")
    return None
