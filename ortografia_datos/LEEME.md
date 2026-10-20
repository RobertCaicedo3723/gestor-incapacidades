El corrector funciona completamente en el computador y no envía textos a internet.

Se incluyen los módulos Python sin modificar y el diccionario español completo
`es.json.gz` de pyspellchecker 0.9.0. Se distribuyen bajo licencia MIT; el aviso
de copyright y el texto de licencia están en `pyspellchecker-LICENSE.txt`.
El diccionario contiene frecuencias de palabras y sirve para proponer alternativas;
no sustituye la revisión del operador ni interpreta el contexto clínico. Solo se
aplica una sugerencia cuando el operador la selecciona.

Fuentes del proyecto y documentación primaria:

- https://github.com/barrust/pyspellchecker
- https://github.com/barrust/pyspellchecker/blob/master/LICENSE
- https://pyspellchecker.readthedocs.io/en/latest/
- https://pypi.org/project/pyspellchecker/0.9.0/

El paquete se obtuvo de la rueda oficial de PyPI
`pyspellchecker-0.9.0-py3-none-any.whl`. Se conservaron únicamente
`spellchecker/__init__.py`, `info.py`, `spellchecker.py`, `utils.py`, el diccionario
español y la licencia. Los demás idiomas no son necesarios para esta aplicación.
La rueda descargada se eliminó después de extraer los recursos. Huellas SHA-256:

- Rueda original: `97eaed776e0854f69aafb723f6962b403099e50c9a1d9c05525c819f4b0f5d54`
- Diccionario español: `60d27fd15ee2a99e679f6da511d8a141941f270537dee34448d1c51279175171`

El envoltorio `ortografia.py` añade recuperación de tildes, límites de longitud y
candidatos, tratamiento de siglas y prioridad a términos habituales del formulario.

Para distribuir el ejecutable, PyInstaller recoge `ortografia` y `spellchecker`
como módulos importados. Junto al ejecutable deben copiarse estos recursos:

- `ortografia_datos/es.json.gz`
- `ortografia_datos/pyspellchecker-LICENSE.txt`
- `ortografia_datos/LEEME.md`
