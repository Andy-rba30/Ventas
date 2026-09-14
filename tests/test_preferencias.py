import json
import os

import pytest

from agro.preferencias import VALORES_DEFECTO, Preferencias


def test_valores_por_defecto_sin_archivo(tmp_path):
    p = Preferencias(str(tmp_path / "negocio.db"))
    assert p.get("apariencia") == "Light" and p.get("geometria") is None and p.get("ultimo_respaldo") is None
    assert not os.path.exists(p.ruta)  # leer no crea el archivo


def test_set_guarda_y_otra_instancia_lo_lee(tmp_path):
    ruta_db = str(tmp_path / "negocio.db")
    p = Preferencias(ruta_db)
    p.set("apariencia", "Dark")
    p.set("geometria", "1300x900+10+20")
    p.set("ultimo_respaldo", {"fecha": "2026-09-14 10:30", "ruta": "/tmp/copia.db"})
    assert os.path.exists(tmp_path / "config.json") and not os.path.exists(tmp_path / "config.json.tmp")
    q = Preferencias(ruta_db)
    assert q.get("apariencia") == "Dark" and q.get("geometria") == "1300x900+10+20"
    assert q.get("ultimo_respaldo")["ruta"] == "/tmp/copia.db"


def test_clave_desconocida_rechazada(tmp_path):
    p = Preferencias(str(tmp_path / "negocio.db"))
    with pytest.raises(KeyError):
        p.set("color_favorito", "verde")


def test_archivo_corrupto_usa_defecto(tmp_path):
    (tmp_path / "config.json").write_text("{esto no es json", encoding="utf-8")
    p = Preferencias(str(tmp_path / "negocio.db"))
    assert p.datos == VALORES_DEFECTO


def test_archivo_con_lista_usa_defecto(tmp_path):
    (tmp_path / "config.json").write_text("[1, 2]", encoding="utf-8")
    assert Preferencias(str(tmp_path / "negocio.db")).datos == VALORES_DEFECTO


def test_claves_desconocidas_en_archivo_se_ignoran(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"apariencia": "System", "otra": 1}), encoding="utf-8")
    p = Preferencias(str(tmp_path / "negocio.db"))
    assert p.get("apariencia") == "System" and "otra" not in p.datos


def test_memoria_no_escribe_archivo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = Preferencias(":memory:")
    p.set("apariencia", "Dark")
    assert p.ruta is None and p.get("apariencia") == "Dark" and list(tmp_path.iterdir()) == []
