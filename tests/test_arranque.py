"""El arranque no debe cargar librerías pesadas: pandas y matplotlib quedaron fuera en la Fase 5."""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _modulos_cargados_al_importar(modulo):
    codigo = (
        "import sys, json\n"
        f"import {modulo}\n"
        "print(json.dumps(sorted(m.split('.')[0] for m in sys.modules)))"
    )
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True)
    import json
    return set(json.loads(salida.stdout.strip().splitlines()[-1]))


def test_capa_de_datos_y_servicios_sin_pandas_ni_matplotlib():
    cargados = _modulos_cargados_al_importar("agro.servicios.reportes")
    assert "pandas" not in cargados and "matplotlib" not in cargados
    assert "openpyxl" not in cargados  # solo se importa al exportar


def test_interfaz_sin_pandas_ni_matplotlib():
    cargados = _modulos_cargados_al_importar("agro.ui.app")
    assert "pandas" not in cargados and "matplotlib" not in cargados
    assert "reportlab" not in cargados and "openpyxl" not in cargados  # solo al imprimir o exportar


def test_requirements_sin_pandas_ni_matplotlib():
    with open(os.path.join(RAIZ, "requirements.txt"), encoding="utf-8") as f:
        contenido = f.read().lower()
    assert "pandas" not in contenido and "matplotlib" not in contenido and "openpyxl" in contenido
