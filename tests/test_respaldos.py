"""Respaldo automático al cerrar: nombre con marca de tiempo, copia consistente y rotación."""
import datetime
import os
import sqlite3

from agro.servicios import respaldos
from agro.servicios.formato import tamano_archivo


def _crear_falsos(carpeta, nombres):
    os.makedirs(carpeta, exist_ok=True)
    for n in nombres:
        with open(os.path.join(carpeta, n), "wb") as f:
            f.write(b"x" * 10)


def test_respaldo_automatico_crea_copia_valida(db_archivo, tmp_path):
    db_archivo.productos.agregar("UREA", 1, 1, 1)
    ruta = respaldos.respaldar_automatico(db_archivo, ahora=datetime.datetime(2026, 9, 14, 8, 30, 5))
    assert ruta == str(tmp_path / "backups" / "negocio_20260914_083005.db")
    assert os.path.exists(ruta) and not os.path.exists(ruta + "-wal")
    copia = sqlite3.connect(ruta)
    try:
        assert copia.execute("SELECT nombre FROM productos").fetchall() == [("UREA",)]
        assert copia.execute("PRAGMA user_version").fetchone()[0] == db_archivo.version_esquema()
    finally:
        copia.close()


def test_dos_respaldos_en_el_mismo_segundo_no_se_pisan(db_archivo, tmp_path):
    momento = datetime.datetime(2026, 9, 14, 8, 30, 5)
    primera = respaldos.respaldar_automatico(db_archivo, ahora=momento)
    db_archivo.productos.agregar("UREA", 1, 1, 1)
    segunda = respaldos.respaldar_automatico(db_archivo, ahora=momento)
    assert segunda.endswith("negocio_20260914_083005_1.db") and primera != segunda
    con = sqlite3.connect(primera)
    try:
        assert con.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0  # la primera quedó intacta
    finally:
        con.close()
    lista = respaldos.listar_respaldos(str(tmp_path / "backups"))
    assert [r.automatico for r in lista] == [True, True] and lista[0].ruta == segunda


def test_bd_en_memoria_no_se_respalda(db):
    assert respaldos.carpeta_de(":memory:") is None
    assert respaldos.respaldar_automatico(db) is None


def test_rotacion_conserva_los_mas_recientes_y_respeta_otras_copias(db_archivo, tmp_path):
    carpeta = str(tmp_path / "backups")
    viejos = [f"negocio_202601{d:02d}_120000.db" for d in range(1, 13)]        # 12 automáticos
    otros = ["negocio_pre_migracion_v2_20260101_000000.db", "copia_manual.db", "notas.txt"]
    _crear_falsos(carpeta, viejos + otros)

    ruta = respaldos.respaldar_automatico(db_archivo, conservar=10, ahora=datetime.datetime(2026, 2, 1, 9, 0, 0))

    quedan = sorted(os.listdir(carpeta))
    automaticos = [n for n in quedan if respaldos._PATRON_AUTOMATICO.match(n)]
    assert len(automaticos) == 10 and os.path.basename(ruta) in automaticos
    # se borraron los 3 más antiguos (01, 02 y 03 de enero)
    assert not {viejos[0], viejos[1], viejos[2]} & set(quedan) and viejos[3] in quedan
    assert set(otros) <= set(quedan)


def test_listar_ordena_del_mas_reciente_al_mas_antiguo(tmp_path):
    carpeta = str(tmp_path / "backups")
    _crear_falsos(carpeta, ["negocio_20260105_100000.db", "negocio_20260301_100000.db", "negocio_pre_migracion_v1_x.db", "leeme.txt"])
    # la copia pre-migración toma la fecha del archivo: la hacemos vieja
    antigua = datetime.datetime(2025, 1, 1).timestamp()
    os.utime(os.path.join(carpeta, "negocio_pre_migracion_v1_x.db"), (antigua, antigua))
    lista = respaldos.listar_respaldos(carpeta)
    assert [r.nombre for r in lista] == ["negocio_20260301_100000.db", "negocio_20260105_100000.db", "negocio_pre_migracion_v1_x.db"]
    assert [r.automatico for r in lista] == [True, True, False]
    assert lista[0].fecha == datetime.datetime(2026, 3, 1, 10) and lista[0].tamano == 10
    assert respaldos.listar_respaldos(str(tmp_path / "no_existe")) == []
    assert respaldos.listar_respaldos(None) == []


def test_rotar_sin_carpeta_no_falla(tmp_path):
    assert respaldos.rotar(str(tmp_path / "nada")) == []


def test_tamano_archivo():
    assert tamano_archivo(0) == "0 B" and tamano_archivo(850) == "850 B"
    assert tamano_archivo(12 * 1024 + 300) == "12.3 KB" and tamano_archivo(4 * 1024 ** 2) == "4.0 MB"
    assert tamano_archivo(3 * 1024 ** 3) == "3.0 GB"
