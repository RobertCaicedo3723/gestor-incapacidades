"""Sugerencias locales en español; nunca modifica el texto del operador."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
import sys
import unicodedata

try:
    from spellchecker import SpellChecker
except ImportError:
    SpellChecker = None


_PALABRA = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)
_TILDES = str.maketrans("áéíóúü", "aeiouu")
_ABREVIATURAS = frozenset({"dr", "dra", "sr", "sra", "srta", "ing", "lic", "prof", "ud", "uds", "etc"})
_PRIORIDAD = frozenset({
    "incapacidad", "incapacidades", "prórroga", "prórrogas", "médico", "médica",
    "certificado", "certificación", "biología", "física", "matemáticas", "química",
    "ingeniería", "geología", "enfermería", "fisioterapia", "nutrición", "dietética",
    "hospitalización", "cirugía", "quirúrgico", "estudiante", "universidad",
    "valoración", "atención", "rehabilitación", "diagnóstico", "remisión",
})


def _sin_tildes(palabra: str) -> str:
    # La ñ es una letra distinta, no una n a la que falte o sobre una tilde.
    return palabra.translate(_TILDES)


def _mayusculas(original: str, sugerencia: str) -> str:
    if original.isupper():
        return sugerencia.upper()
    if original.istitle():
        return sugerencia.capitalize()
    return sugerencia


class CorrectorEspanol:
    """Diccionario distribuido con la aplicación, sin servicios ni instalaciones.

    El vocabulario completo y las frecuencias proceden de pyspellchecker. Se
    buscan errores de una edición y se recuperan sus variantes acentuadas; esto
    permite corregir simultáneamente una letra y una tilde sin la explosión de
    combinaciones de una búsqueda de distancia dos. Números, códigos y siglas
    cortas se omiten. Las propuestas solo se aplican si el usuario las elige.
    """

    def __init__(self, directorio: str | Path | None = None):
        self.disponible = False
        self.error = ""
        self._spell = None
        self._acentos: dict[str, tuple[str, ...]] = {}
        if SpellChecker is None:
            self.error = "No se encontró el componente local de ortografía."
            return
        base = (Path(directorio) if directorio is not None else
                Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
                else Path(__file__).resolve().parent)
        try:
            self._spell = SpellChecker(
                language=None, local_dictionary=base / "ortografia_datos/es.json.gz",
                distance=1,
            )
            # Añadir vocabulario administrativo y clínico de uso habitual que
            # puede faltar en el corpus de frecuencias general del proveedor.
            self._spell.word_frequency.load_words(_PRIORIDAD)
            grupos: dict[str, list[str]] = {}
            for palabra in self._spell.word_frequency.dictionary:
                if _PALABRA.fullmatch(palabra):
                    grupos.setdefault(_sin_tildes(palabra), []).append(palabra)
            self._acentos = {clave: tuple(palabras) for clave, palabras in grupos.items()}
            self.disponible = True
        except (OSError, ValueError, EOFError, UnicodeError) as exc:
            self.error = f"No fue posible cargar el diccionario español local: {exc}"

    def sugerencias(self, palabra: str) -> list[str]:
        """Devuelve hasta seis propuestas; entrada correcta/siglas/códigos: []."""
        if not self.disponible or not isinstance(palabra, str):
            return []
        original = unicodedata.normalize("NFC", palabra)
        if not (3 <= len(original) <= 40) or not _PALABRA.fullmatch(original):
            return []
        if original.isupper() and len(original) <= 5:
            return []
        if original.lower() in _ABREVIATURAS:
            return []
        return [_mayusculas(original, opcion) for opcion in self._sugerencias(original.lower())]

    @lru_cache(maxsize=512)
    def _sugerencias(self, palabra: str) -> tuple[str, ...]:
        spell = self._spell
        normal = _sin_tildes(palabra)
        mismos = set(self._acentos.get(normal, ()))
        if palabra in spell:
            # Una palabra válida no necesita vecinos. Para "medico" se permite
            # elegir "médico", pero jamás se propone quitar tildes a "médico".
            candidatos = {p for p in mismos if p != palabra and
                          sum(c in "áéíóúü" for c in p) > sum(c in "áéíóúü" for c in palabra)}
        else:
            candidatos = mismos | spell.known(spell.edit_distance_1(palabra))
            for variante in spell.edit_distance_1(normal):
                candidatos.update(self._acentos.get(variante, ()))
        candidatos.discard(palabra)
        candidatos = {p for p in candidatos if _PALABRA.fullmatch(p) and len(p) >= 3}
        ordenados = sorted(candidatos, key=lambda p: (
            _sin_tildes(p) != normal,
            p not in _PRIORIDAD,
            -spell[p],
            p,
        ))
        return tuple(ordenados[:6])
