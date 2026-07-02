"""Tests de `query_production_db`: la validación de solo-lectura (lista blanca
de comandos + lista negra de palabras) es la superficie de seguridad más crítica.
"""
from types import SimpleNamespace

import pytest

from chatbot.tools import db_tools
from chatbot.tools.db_tools import query_production_db


# --- Helpers para mockear SessionLocal (sin MySQL real) ---

class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchmany(self, n):
        return self._rows[:n]


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, stmt):
        return _FakeResult(self._rows)


def _mock_db(monkeypatch, rows):
    """Hace que SessionLocal() devuelva una sesión falsa con esas filas."""
    monkeypatch.setattr(db_tools, "SessionLocal", lambda: _FakeSession(rows))


# --- Rechazos: no deberían tocar la DB siquiera ---

@pytest.mark.parametrize("sql", [
    "DELETE FROM employees",
    "UPDATE employees SET salary = 0",
    "DROP TABLE employees",
    "INSERT INTO t VALUES (1)",
    "TRUNCATE employees",
    "  CREATE TABLE x (id int)",
])
async def test_rechaza_comandos_que_no_empiezan_permitidos(sql):
    res = await query_production_db(sql)
    assert res.startswith("Error: La consulta debe empezar")


@pytest.mark.parametrize("sql", [
    "SELECT * FROM t; DROP TABLE t",
    "WITH x AS (SELECT 1) DELETE FROM t",
    "SELECT * FROM t WHERE id IN (SELECT id FROM t); UPDATE t SET a=1",
])
async def test_rechaza_palabras_prohibidas_aunque_empiece_permitido(sql):
    res = await query_production_db(sql)
    assert "palabras prohibidas" in res


# --- Casos permitidos: llegan a la DB (mockeada) ---

async def test_select_valido_devuelve_filas(monkeypatch):
    _mock_db(monkeypatch, [SimpleNamespace(_mapping={"emp_no": 1, "name": "Ana"})])
    res = await query_production_db("SELECT * FROM employees LIMIT 1")
    assert "emp_no" in res and "Ana" in res


async def test_select_sin_resultados(monkeypatch):
    _mock_db(monkeypatch, [])
    res = await query_production_db("SELECT * FROM employees WHERE 1=0")
    assert res == "No se encontraron resultados."


async def test_palabra_peligrosa_dentro_de_comillas_no_bloquea(monkeypatch):
    # 'DELETE' va como literal entre comillas: se ignora y la query es válida.
    _mock_db(monkeypatch, [])
    res = await query_production_db("SELECT * FROM t WHERE nombre = 'DELETE'")
    assert res == "No se encontraron resultados."


async def test_solo_lectura_show_y_describe_permitidos(monkeypatch):
    _mock_db(monkeypatch, [SimpleNamespace(_mapping={"Tables_in_db": "employees"})])
    res = await query_production_db("SHOW TABLES")
    assert "employees" in res
