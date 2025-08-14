# tests/test_cli.py
import os
import re
import json
from pathlib import Path
import importlib

import pytest

def _run(cli, args, capsys):
    """Executa finance.cli.main(args) e devolve (stdout, stderr)."""
    cli.main(args)
    captured = capsys.readouterr()
    return captured.out, captured.err

@pytest.fixture()
def cli_in_tmpdir(tmp_path, monkeypatch):
    """
    Importa finance.cli e redireciona BASE_DATA para uma pasta temporária única por teste.
    Garante que data/ existe para a CLI escrever os JSONs.
    """
    # importa finance.cli’ sempre “fresco” para evitar estado compartilhado
    import finance.cli as cli
    importlib.reload(cli)

    base = tmp_path
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # injeta o diretório temporário como BASE_DATA da CLI
    monkeypatch.setattr(cli, "BASE_DATA", str(data_dir), raising=False)

    return cli, data_dir

def test_add_mov_e_list(cli_in_tmpdir, capsys):
    cli, data_dir = cli_in_tmpdir

    # add-mov
    out, err = _run(cli, [
        "add-mov",
        "--tipo", "despesa",
        "--valor", "12.50",
        "--cat", "supermercado",
        "--metodo", "MBWay",
        "--desc", "Leite e pão"
    ], capsys)
    assert "Criado movimento #1" in out

    # list-mov
    out, err = _run(cli, ["list-mov"], capsys)
    # Deve conter a linha formatada da listagem
    assert "#1" in out
    assert "DESPESA" in out
    assert "supermercado" in out
    assert "MBWay" in out
    assert "Leite e pão" in out

    # JSON gravado
    mov_path = data_dir / "movimentos.json"
    assert mov_path.exists()
    data = json.loads(mov_path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["tipo"] == "despesa"

def test_add_orc_e_overspend_alert(cli_in_tmpdir, capsys):
    cli, data_dir = cli_in_tmpdir

    # add-orc mensal
    out, err = _run(cli, [
        "add-orc",
        "--cat", "restaurante",
        "--limite", "100",
        "--periodo", "mensal"
    ], capsys)
    assert "Orçamento" in out
    assert "restaurante" in out

    # 1ª despesa (sem overspend)
    out, err = _run(cli, [
        "add-mov",
        "--tipo", "despesa",
        "--valor", "60",
        "--cat", "restaurante",
        "--desc", "almoço"
    ], capsys)
    assert "Criado movimento #1" in out
    assert "Orçamento EXCEDIDO" not in out

    # 2ª despesa (deve ultrapassar e imprimir alerta)
    out, err = _run(cli, [
        "add-mov",
        "--tipo", "despesa",
        "--valor", "50",
        "--cat", "restaurante",
        "--desc", "jantar"
    ], capsys)
    assert "Criado movimento #2" in out
    assert "Orçamento EXCEDIDO" in out or "⚠️" in out

def test_relatorios_export_json_csv(cli_in_tmpdir, capsys):
    cli, data_dir = cli_in_tmpdir

    # cria dados
    _run(cli, ["add-mov", "--tipo", "receita", "--valor", "500", "--cat", "salario", "--desc", "agosto"], capsys)
    _run(cli, ["add-mov", "--tipo", "despesa", "--valor", "40", "--cat", "supermercado", "--desc", "compras"], capsys)
    _run(cli, ["add-mov", "--tipo", "despesa", "--valor", "20", "--cat", "transporte", "--desc", "passe"], capsys)
    _run(cli, ["add-orc", "--cat", "supermercado", "--limite", "30", "--periodo", "semanal"], capsys)

    # totais-por-cat (JSON)
    out, _ = _run(cli, [
        "relatorio",
        "--tipo", "totais-por-cat",
        "--saida", "json"
    ], capsys)
    assert "Ficheiro exportado:" in out
    m = re.search(r"Ficheiro exportado:\s+(.+\.json)\s*$", out, re.MULTILINE)
    assert m, f"não encontrou caminho JSON no output: {out}"
    json_path = Path(m.group(1).strip())
    assert json_path.exists() and json_path.suffix == ".json"

    # cashflow-semanal (CSV)
    out, _ = _run(cli, [
        "relatorio",
        "--tipo", "cashflow-semanal",
        "--saida", "csv"
    ], capsys)
    m = re.search(r"Ficheiro exportado:\s+(.+\.csv)\s*$", out, re.MULTILINE)
    assert m, f"não encontrou caminho CSV no output: {out}"
    csv_path = Path(m.group(1).strip())
    assert csv_path.exists() and csv_path.suffix == ".csv"

    # top-categorias despesas (CSV)
    out, _ = _run(cli, [
        "relatorio",
        "--tipo", "top-categorias",
        "--mov-tipo", "despesa",
        "--top", "2",
        "--saida", "csv"
    ], capsys)
    m = re.search(r"Ficheiro exportado:\s+(.+\.csv)\s*$", out, re.MULTILINE)
    assert m
    assert Path(m.group(1).strip()).exists()

    # alertas (JSON) — deve existir ficheiro, mesmo se vazio
    out, _ = _run(cli, [
        "relatorio",
        "--tipo", "alertas",
        "--saida", "json"
    ], capsys)
    m = re.search(r"Ficheiro exportado:\s+(.+\.json)\s*$", out, re.MULTILINE)
    assert m
    assert Path(m.group(1).strip()).exists()