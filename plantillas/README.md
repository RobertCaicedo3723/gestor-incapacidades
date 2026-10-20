# Plantillas locales

La aplicación de trabajo utiliza estos archivos, que se excluyen de Git:

- `certificado_sin.docx`: certificado con campos OOXML de sustitución.
- `certificado_con.docx`: variante institucional preparada durante la instalación original.
- `externa_legacy.doc`: remisión externa con campos de sustitución, exportada mediante Word.

No son documentos Word vacíos. Requieren campos compatibles con `motor.py` y una composición autorizada para la organización que use la herramienta. No cambie la extensión de un archivo para intentar convertirlo en una plantilla compatible.

Los recursos originales y sus firmas no forman parte de este repositorio público. Sin ellos puede probar la interfaz y la validación, pero no emitir los documentos de la instalación institucional.
