"""Rotas do PAINEL e RELATÓRIOS: indicadores calculados com os dados reais.

Regras de cálculo:
  • Cada consumo é contado no dia em que começa (data_inicio), uma única vez.
  • Custo estimado = consumo (kWh) × tarifa da empresa (R$/kWh). Sem tarifa,
    o custo não é calculado e a resposta traz um aviso.
  • Comparação: período anterior com a mesma quantidade de dias.
  • Pico (kWh/h) = maior média horária entre os registros de consumo do período.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query

from database import executar
from models.relatorio import RelatorioResponse
from seguranca import Contexto, usuario_atual

router = APIRouter(prefix="/relatorios", tags=["Painel e Relatórios"])

FUSO = ZoneInfo("America/Sao_Paulo")


def _consumos(contexto: Contexto, inicio: date, fim: date) -> list[dict]:
    return executar(contexto.db.table("consumo").select("id_consumo,data_inicio,data_fim,consumo_kwh,id_maquina")
                    .gte("data_inicio", datetime.combine(inicio, time.min).isoformat())
                    .lte("data_inicio", datetime.combine(fim, time.max).isoformat()))


@router.get("/resumo", response_model=RelatorioResponse, summary="Indicadores do período (padrão: mês atual)")
def resumo(inicio: date | None = Query(default=None, description="AAAA-MM-DD (padrão: 1º dia do mês atual)"),
           fim: date | None = Query(default=None, description="AAAA-MM-DD (padrão: hoje)"),
           contexto: Contexto = Depends(usuario_atual)):
    hoje = datetime.now(FUSO).date()
    fim = fim or hoje
    inicio = inicio or fim.replace(day=1)
    if fim < inicio:
        raise HTTPException(status_code=422, detail="A data final deve ser igual ou posterior à data inicial.")
    dias = (fim - inicio).days + 1
    if dias > 366:
        raise HTTPException(status_code=422, detail="Escolha um período de até 366 dias.")

    tarifa = contexto.tarifa_kwh
    consumos = _consumos(contexto, inicio, fim)
    anterior = _consumos(contexto, inicio - timedelta(days=dias), inicio - timedelta(days=1))
    maquinas = executar(contexto.db.table("maquina").select("id_maquina,nome_maquina,id_setor"))
    setores = {s["id_setor"]: s["nome_setor"] for s in executar(contexto.db.table("setor").select("id_setor,nome_setor"))}
    sensores = executar(contexto.db.table("sensor").select("id_sensor,status_conexao"))
    leituras = (contexto.db.table("leitura").select("id_leitura", count="exact")
                .gte("data_leitura", datetime.combine(inicio, time.min).isoformat())
                .lte("data_leitura", datetime.combine(fim, time.max).isoformat()).limit(1).execute())
    pendentes = (contexto.db.table("tomada_decisao").select("id_tomada_decisao", count="exact")
                 .eq("status_execucao", "pendente").limit(1).execute())
    recentes = executar(contexto.db.table("tomada_decisao")
                        .select("id_tomada_decisao,data_tomada_decisao,valor_referencia,status_execucao,id_decisao")
                        .order("data_tomada_decisao", desc=True).limit(5))
    nomes_regras = {r["id_decisao"]: r["nome_decisao"] for r in executar(contexto.db.table("decisao").select("id_decisao,nome_decisao"))}

    info_maquina = {m["id_maquina"]: m for m in maquinas}
    custo = (lambda kwh: round(kwh * tarifa, 2)) if tarifa is not None else (lambda kwh: None)

    total = 0.0
    picos = []
    por_maquina: dict[int, dict] = {}
    por_setor: dict[int, dict] = {}
    por_dia = {inicio + timedelta(days=i): 0.0 for i in range(dias)}
    for c in consumos:
        kwh = float(c["consumo_kwh"])
        total += kwh
        ini, fim_c = datetime.fromisoformat(c["data_inicio"]), datetime.fromisoformat(c["data_fim"])
        horas = (fim_c - ini).total_seconds() / 3600
        if horas > 0:
            picos.append(kwh / horas)
        por_dia[ini.date()] = por_dia.get(ini.date(), 0.0) + kwh
        m = info_maquina.get(c["id_maquina"], {"nome_maquina": f"Máquina #{c['id_maquina']}", "id_setor": None})
        item = por_maquina.setdefault(c["id_maquina"], {"id": c["id_maquina"], "nome": m["nome_maquina"],
                                                        "grupo": setores.get(m["id_setor"]), "consumo_kwh": 0.0, "registros": 0})
        item["consumo_kwh"] += kwh
        item["registros"] += 1
        if m.get("id_setor") is not None:
            s = por_setor.setdefault(m["id_setor"], {"id": m["id_setor"], "nome": setores.get(m["id_setor"], "Setor"),
                                                     "consumo_kwh": 0.0, "registros": 0})
            s["consumo_kwh"] += kwh
            s["registros"] += 1

    def finalizar(itens: dict) -> list[dict]:
        lista = sorted(itens.values(), key=lambda i: i["consumo_kwh"], reverse=True)
        for i in lista:
            i["consumo_kwh"] = round(i["consumo_kwh"], 2)
            i["custo_estimado"] = custo(i["consumo_kwh"])
        return lista

    total_anterior = round(sum(float(c["consumo_kwh"]) for c in anterior), 2)
    total = round(total, 2)
    return {
        "inicio": inicio, "fim": fim, "dias": dias, "tarifa_kwh": tarifa,
        "consumo_total_kwh": total, "custo_estimado": custo(total),
        "media_diaria_kwh": round(total / dias, 2),
        "pico_kwh_h": round(max(picos), 2) if picos else None,
        "periodo_anterior_kwh": total_anterior,
        "variacao_percentual": round((total - total_anterior) / total_anterior * 100, 1) if total_anterior > 0 else None,
        "registros_consumo": len(consumos),
        "leituras_no_periodo": leituras.count or 0,
        "total_setores": len(setores), "total_maquinas": len(maquinas), "total_sensores": len(sensores),
        "sensores_online": sum(1 for s in sensores if s["status_conexao"] == "online"),
        "alertas_pendentes": pendentes.count or 0,
        "por_maquina": finalizar(por_maquina), "por_setor": finalizar(por_setor),
        "por_dia": [{"data": d, "consumo_kwh": round(v, 2)} for d, v in sorted(por_dia.items()) if inicio <= d <= fim],
        "alertas_recentes": [{**t, "nome_decisao": nomes_regras.get(t["id_decisao"])} for t in recentes],
        "aviso": None if tarifa is not None else "Defina a tarifa de energia (R$/kWh) em Empresa para calcular custos.",
    }
