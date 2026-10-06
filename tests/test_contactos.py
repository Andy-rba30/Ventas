"""Repositorio de contactos (v2: notas) y deuda por cliente."""
from agro.db.contactos import Contacto
from tests.conftest import carrito


def test_agregar_con_notas_y_obtener(db):
    assert db.contactos.agregar("cliente", "ANA", "123", "999", notas="Paga los viernes")
    c = db.contactos.obtener("cliente", "ANA")
    assert c == Contacto(c.id, "ANA", "123", "999", "Paga los viernes", True)
    assert db.contactos.obtener("cliente", "NADIE") is None
    assert db.contactos.listar("cliente")[0][1:] == ("ANA", "123", "999", "Paga los viernes")


def test_proveedor_usa_columna_contacto(db):
    assert db.contactos.agregar("proveedor", "AGROSUR", "Pedro", "888")
    p = db.contactos.obtener("proveedor", "AGROSUR")
    assert p.documento == "Pedro" and p.notas == ""
    assert db.contactos.listar("proveedor") == [(p.id, "AGROSUR", "Pedro", "888", "")]


def test_modificar_datos_y_nombre(con_datos):
    assert con_datos.contactos.modificar("cliente", "JUAN", "JUAN PEREZ", "87654321", "111", "vecino")
    assert con_datos.contactos.obtener("cliente", "JUAN") is None
    c = con_datos.contactos.obtener("cliente", "JUAN PEREZ")
    assert (c.documento, c.telefono, c.notas) == ("87654321", "111", "vecino")


def test_modificar_a_nombre_existente_falla(con_datos):
    con_datos.contactos.agregar("cliente", "ANA", "", "")
    assert con_datos.contactos.modificar("cliente", "ANA", "JUAN", "", "") is False
    assert con_datos.contactos.obtener("cliente", "ANA") is not None


def test_publico_general_no_se_renombra_pero_acepta_notas(db):
    assert db.contactos.modificar("cliente", "PÚBLICO GENERAL", "OTRO", "", "") is False
    assert db.contactos.modificar("cliente", "PÚBLICO GENERAL", "PÚBLICO GENERAL", "-", "-", "ventas sin nombre")
    assert db.contactos.obtener("cliente", "PÚBLICO GENERAL").notas == "ventas sin nombre"


def test_modificar_inexistente(db):
    assert db.contactos.modificar("proveedor", "NADIE", "NADIE", "", "") is False


def test_reactivar_conserva_id_y_actualiza_notas(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-01", "Administradora", "JUAN")
    id_juan = con_datos.contactos.id_de("cliente", "JUAN")
    assert con_datos.contactos.eliminar("cliente", "JUAN")  # con historial: se desactiva
    assert con_datos.contactos.obtener("cliente", "JUAN").activo is False
    assert con_datos.contactos.obtener("cliente", "JUAN", incluir_inactivos=False) is None
    assert con_datos.contactos.agregar("cliente", "JUAN", "1", "2", notas="volvió")
    c = con_datos.contactos.obtener("cliente", "JUAN")
    assert c.id == id_juan and c.activo and c.notas == "volvió"


def test_total_por_cobrar_por_cliente(con_datos, ops):
    con_datos.contactos.agregar("cliente", "ANA", "", "")
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-01", "Administradora", "JUAN", fiado=True)
    ops.registrar_venta(carrito(("FOSFATO", 90, 2)), "2026-09-02", "Administradora", "ANA", fiado=True)
    assert con_datos.boletas.total_por_cobrar() == 300
    assert con_datos.boletas.total_por_cobrar("JUAN") == 120
    assert con_datos.boletas.total_por_cobrar("ANA") == 180
    assert con_datos.boletas.total_por_cobrar("NADIE") == 0
    ops.cobrar_fiado(con_datos.boletas.deudas_pendientes("JUAN")[0].id, "Administradora", monto=20)
    assert con_datos.boletas.total_por_cobrar("JUAN") == 100
