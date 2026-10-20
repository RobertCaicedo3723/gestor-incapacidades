"""Pruebas del diccionario local, correcciones útiles y tiempo de respuesta."""
import json
import tempfile
from pathlib import Path
from time import perf_counter

from ortografia import CorrectorEspanol


def run():
    inicio = perf_counter()
    corrector = CorrectorEspanol()
    carga = perf_counter() - inicio
    assert corrector.disponible, corrector.error
    casos = {
        "incapasidad": "incapacidad", "biolgia": "biología", "medcio": "médico",
        "prorroga": "prórroga", "hospitalizacion": "hospitalización",
        "Ingenieria": "Ingeniería", "INCAPASIDAD": "INCAPACIDAD",
        "Medcio": "Médico", "biologia": "biología", "geologia": "geología",
    }
    resultados = {}
    tiempos = []
    for entrada, esperado in casos.items():
        inicio = perf_counter()
        propuestas = corrector.sugerencias(entrada)
        tiempos.append(perf_counter() - inicio)
        assert esperado in propuestas, (entrada, propuestas, esperado)
        assert len(propuestas) <= 6
        resultados[entrada] = propuestas
    for ignorada in ("UIS", "EPS", "IPS", "Dr", "Dra", "CC", "1234567", "A1234", "16/10/2026", "", "\n", "@escuela", "a" * 10000):
        assert corrector.sugerencias(ignorada) == [], ignorada
    for correcta in ("incapacidad", "médico", "prórroga", "universidad", "estudiante", "fisioterapia"):
        assert corrector.sugerencias(correcta) == [], correcta
    assert corrector.sugerencias("incapasidad") is not corrector.sugerencias("incapasidad")
    assert corrector.sugerencias("hospitalizacio\u0301n") == []
    with tempfile.TemporaryDirectory() as directorio:
        ausente = CorrectorEspanol(Path(directorio))
        assert not ausente.disponible and ausente.error
        assert ausente.sugerencias("incapasidad") == []
    inicio = perf_counter()
    corrector.sugerencias("electroencefalograficamenteequivocada")
    larga = perf_counter() - inicio
    assert max(tiempos + [larga]) < .5, (tiempos, larga)
    informe = {
        "estado": "correcto", "diccionario_palabras": len(corrector._spell.word_frequency.dictionary),
        "carga_segundos": round(carga, 4), "peor_consulta_segundos": round(max(tiempos + [larga]), 4),
        "sugerencias": resultados,
    }
    print(json.dumps(informe, ensure_ascii=False, indent=2))
    return informe


if __name__ == "__main__":
    run()
