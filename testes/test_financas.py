import os, tempfile, shutil
import pytest
from finance.storage import Storage
from finance.service import FinanceService
from finance.models import TipoMovimento
from finance.reports import Reports

# ---------- fixture: serviço isolado por teste ----------
@pytest.fixture()
def fresh_service():
    tmp = tempfile.mkdtemp()
    try:
        yield FinanceService(Storage(tmp))
    finally:
        shutil.rmtree(tmp)

# ---------- 1. orçamentos ----------
def test_add_orcamento_mensal(fresh_service):
    s = fresh_service
    orc, status = s.add_orcamento("restaurante", 100, "mensal")
    assert orc.categoria == "restaurante"
    assert orc.limite == 100
    assert orc.periodo == "mensal"
    assert status in ("criado", "atualizado")

def test_add_orcamento_semanal(fresh_service):
    s = fresh_service
    orc, status = s.add_orcamento("supermercado", 40, "semanal")
    assert orc.categoria == "supermercado"
    assert orc.limite == 40
    assert orc.periodo == "semanal"
    assert status in ("criado", "atualizado")

# ---------- 2. movimentos básicos ----------
def test_add_movimento_despesa(fresh_service):
    s = fresh_service
    mov, alerta = s.add_movimento(TipoMovimento.DESPESA, 12.5, "cafes", "cappuccino", "cartao")
    assert mov.id == 1
    assert mov.tipo == TipoMovimento.DESPESA
    assert alerta is None
    assert len(s.listar()) == 1

def test_add_movimento_receita_no_overspend(fresh_service):
    s = fresh_service
    s.add_orcamento("salario", 1_000, "mensal")
    mov, alerta = s.add_movimento(TipoMovimento.RECEITA, 1500, "salario", "Agosto")
    assert mov.tipo == TipoMovimento.RECEITA
    assert alerta is None  # receitas não disparam overspend

# ---------- 3. overspend ----------
def test_overspend_mensal_detection(fresh_service):
    s = fresh_service
    s.add_orcamento("restaurante", 100, "mensal")
    s.add_movimento(TipoMovimento.DESPESA, 60, "restaurante", "almoço")
    _, alerta = s.add_movimento(TipoMovimento.DESPESA, 50, "restaurante", "jantar")
    assert alerta is not None
    assert alerta["periodo"] == "mensal"
    assert alerta["categoria"] == "restaurante"
    # 60 + 50 = 110 → excesso 10
    assert round(alerta["excesso"], 2) == 10.00

def test_overspend_semanal_detection(fresh_service):
    s = fresh_service
    s.add_orcamento("supermercado", 30, "semanal")
    s.add_movimento(TipoMovimento.DESPESA, 20, "supermercado", "compras 1")
    _, alerta = s.add_movimento(TipoMovimento.DESPESA, 15, "supermercado", "compras 2")
    assert alerta is not None
    assert alerta["periodo"] == "semanal"
    assert alerta["categoria"] == "supermercado"
    assert alerta["excesso"] > 0

# ---------- 4. listagem e filtros ----------
def test_listar_filtrado_por_cat_tipo(fresh_service):
    s = fresh_service
    s.add_movimento(TipoMovimento.DESPESA, 10, "transporte", "autocarro")
    s.add_movimento(TipoMovimento.RECEITA, 100, "salario", "bonus")
    r = s.listar_filtrado(cat="transporte", tipo="despesa")
    assert len(r) == 1
    assert r[0].categoria == "transporte"
    assert r[0].tipo == TipoMovimento.DESPESA

# ---------- 5. relatórios + export ----------
def test_relatorio_totais_por_cat_and_export_json(fresh_service, tmp_path=None):
    s = fresh_service
    s.add_movimento(TipoMovimento.DESPESA, 25, "livros", "caderno")
    s.add_movimento(TipoMovimento.RECEITA, 200, "salario", "parcial")
    rep = Reports(s.storage)
    data = rep.totais_por_cat()
    assert any(d["categoria"] == "livros" for d in data)
    path = rep.exportar(data, "totais-por-cat", formato="json")
    assert os.path.exists(path)
    assert path.endswith(".json")

def test_relatorio_cashflow_semanal_and_export_csv(fresh_service):
    s = fresh_service
    s.add_movimento(TipoMovimento.DESPESA, 10, "snacks", "batatas")
    s.add_movimento(TipoMovimento.RECEITA, 50, "freelance", "job")
    rep = Reports(s.storage)
    data = rep.cashflow_semanal()
    assert isinstance(data, list)
    path = rep.exportar(data, "cashflow-semanal", formato="csv")
    assert os.path.exists(path)
    assert path.endswith(".csv")

def test_relatorio_top_categorias_despesa(fresh_service):
    s = fresh_service
    s.add_movimento(TipoMovimento.DESPESA, 30, "supermercado", "compras")
    s.add_movimento(TipoMovimento.DESPESA, 20, "restaurante", "almoço")
    rep = Reports(s.storage)
    top = rep.top_categorias(n=1, tipo="despesa")
    assert len(top) == 1
    assert top[0]["categoria"] in {"supermercado", "restaurante"}
    assert top[0]["total"] > 0

def test_relatorio_alertas_combina_mensal_e_semanal(fresh_service):
    s = fresh_service
    # define ambos períodos para a mesma categoria
    s.add_orcamento("combustivel", 50, "mensal")
    s.add_orcamento("combustivel", 25, "semanal")
    # despesas que excedem pelo menos um dos períodos
    s.add_movimento(TipoMovimento.DESPESA, 20, "combustivel", "semana X - 1")
    _, alerta = s.add_movimento(TipoMovimento.DESPESA, 15, "combustivel", "semana X - 2")
    # pode exceder o semanal já na 2ª compra; o mensal pode ou não, conforme totais
    assert alerta is not None
    rep = Reports(s.storage)
    alerts = rep.alertas()
    assert any(a["categoria"] == "combustivel" for a in alerts)