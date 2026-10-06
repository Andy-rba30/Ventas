"""Ubicación de los datos por plataforma y traslado de la BD que antes vivía junto al programa."""
import os

import pytest

from agro import rutas
from agro.config import NOMBRE_BD


@pytest.fixture
def casa(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv(rutas.VARIABLE_ENTORNO, raising=False)
    return tmp_path


def test_carpeta_por_plataforma(casa):
    assert rutas.carpeta_datos("win32", {"APPDATA": r"C:\Users\ana\AppData\Roaming"}) == os.path.join(r"C:\Users\ana\AppData\Roaming", "AgroNegocio")
    assert rutas.carpeta_datos("win32", {}) == os.path.join(str(casa), "AppData", "Roaming", "AgroNegocio")
    assert rutas.carpeta_datos("darwin", {}) == os.path.join(str(casa), "Library", "Application Support", "AgroNegocio")
    assert rutas.carpeta_datos("linux", {}) == os.path.join(str(casa), ".local", "share", "agro-negocio")
    assert rutas.carpeta_datos("linux", {"XDG_DATA_HOME": "/datos"}) == os.path.join("/datos", "agro-negocio")


def test_variable_de_entorno_manda(casa, monkeypatch):
    monkeypatch.setenv(rutas.VARIABLE_ENTORNO, str(casa / "usb"))
    assert rutas.carpeta_datos("win32", os.environ) == str(casa / "usb")
    ruta = rutas.ruta_bd()
    assert ruta == str(casa / "usb" / NOMBRE_BD) and os.path.isdir(casa / "usb")  # crea la carpeta, no la BD
    assert not os.path.exists(ruta)


def test_ruta_recurso_desde_el_codigo():
    assert os.path.isfile(rutas.ruta_recurso(os.path.join("assets", "icono.png")))
    assert os.path.isfile(rutas.ruta_recurso(os.path.join("assets", "icono.ico")))


def test_carpeta_ejecutable_sin_empaquetar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert rutas.carpeta_ejecutable() == str(tmp_path)


def _bd_vieja(carpeta, extras=()):
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / NOMBRE_BD).write_bytes(b"sqlite")
    for e in extras:
        if e.endswith("/"):
            (carpeta / e.rstrip("/")).mkdir()
            (carpeta / e.rstrip("/") / "x.db").write_bytes(b"copia")
        else:
            (carpeta / e).write_text("{}")


def test_traslada_bd_y_acompanantes_la_primera_vez(tmp_path):
    origen, destino = tmp_path / "programa", tmp_path / "datos"
    _bd_vieja(origen, extras=[NOMBRE_BD + "-wal", "config.json", "backups/", "otro.txt"])
    movidos = rutas.trasladar_datos_antiguos(str(origen), str(destino))
    assert sorted(os.path.basename(m) for m in movidos) == sorted([NOMBRE_BD, NOMBRE_BD + "-wal", "config.json", "backups"])
    assert (destino / NOMBRE_BD).read_bytes() == b"sqlite" and (destino / "backups" / "x.db").exists()
    assert not (origen / NOMBRE_BD).exists() and (origen / "otro.txt").exists()  # lo ajeno se queda
    # segunda vez: ya no hay nada que mover
    assert rutas.trasladar_datos_antiguos(str(origen), str(destino)) == []


def test_no_pisa_una_bd_ya_existente_en_destino(tmp_path):
    origen, destino = tmp_path / "programa", tmp_path / "datos"
    _bd_vieja(origen)
    destino.mkdir()
    (destino / NOMBRE_BD).write_bytes(b"nueva")
    assert rutas.trasladar_datos_antiguos(str(origen), str(destino)) == []
    assert (destino / NOMBRE_BD).read_bytes() == b"nueva" and (origen / NOMBRE_BD).exists()


def test_sin_bd_vieja_o_misma_carpeta_no_hace_nada(tmp_path):
    assert rutas.trasladar_datos_antiguos(str(tmp_path / "nada"), str(tmp_path / "datos")) == []
    _bd_vieja(tmp_path / "misma")
    assert rutas.trasladar_datos_antiguos(str(tmp_path / "misma"), str(tmp_path / "misma")) == []
    assert (tmp_path / "misma" / NOMBRE_BD).exists()
