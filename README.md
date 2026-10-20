# Gestor local de incapacidades médicas

Aplicación de escritorio para agilizar la preparación de certificados y remisiones en una ventanilla universitaria. Permite registrar los datos una sola vez, revisar el contenido y generar un PDF para impresión junto con una copia editable en Word.

El proyecto integra una interfaz en Python/Tkinter, edición de documentos OOXML y exportación con Microsoft Word. Opera localmente, sin servicios de IA ni envío de datos a servidores externos.

## Funcionalidades

- Certificados con o sin prórroga y remisiones de incapacidad externa.
- Periodos posteriores independientes, con fechas, institución y médico propios.
- Escuela de texto libre, calendarios y ejemplos breves sobre los campos.
- Sugerencias ortográficas en español mediante clic derecho, con diccionario incluido y aceptación manual.
- Revisión previa, guardado de PDF y Word y comprobación de una sola página antes de publicar los archivos.
- Invalidación del PDF anterior al modificar un caso y limpieza del historial de edición al iniciar otro estudiante.

## Decisiones técnicas

| Componente | Responsabilidad |
| --- | --- |
| `app.py` | Formularios, navegación, calendarios y revisión antes de guardar. |
| `motor.py` | Validaciones, cálculo de días, sustitución de campos OOXML y publicación de archivos. |
| `word_pdf.ps1` | Automatización de Word mediante COM para exportar el PDF con el motor de impresión de escritorio. |
| `edicion_texto.py` y `ortografia.py` | Menú contextual y propuestas ortográficas sin conexión. |
| `spellchecker/` y `ortografia_datos/` | Componentes y diccionario de pyspellchecker, con su licencia MIT. |

La generación se ejecuta fuera del hilo principal para mantener la interfaz disponible. Los documentos se preparan en una carpeta temporal; si falla la exportación o el contenido excede una página, no se publican archivos incompletos. La rueda del ratón desplaza el formulario sin cambiar las opciones de los selectores cerrados.

## Ejecutar la interfaz

Requisitos: Windows 10 u 11 de 64 bits y Python 3.12 con Tkinter. Para emitir documentos también se requiere Microsoft Word de escritorio instalado y activado; Word en el navegador no sustituye esta dependencia.

```powershell
git clone https://github.com/RobertCaicedo3723/gestor-incapacidades.git
cd gestor-incapacidades
py -3.12 app.py
```

No se necesita instalar paquetes de Python para ejecutar el código: el corrector está incluido. La interfaz puede explorarse sin los recursos de impresión. La generación requiere configurar los archivos indicados en [plantillas](plantillas/README.md) y [fuentes](fuentes/README.md).

## Recursos excluidos de la publicación

Este repositorio contiene código y pruebas con datos ficticios. No contiene documentos de estudiantes, historias clínicas, firmas, nombres reales en los valores predeterminados, rutas del equipo de desarrollo ni ejecutables que incorporen recursos privados.

Las plantillas institucionales, logos y archivos de fuentes se mantienen fuera del repositorio. La edición operativa utiliza recursos locales autorizados; no se pueden generar certificados a partir de una descarga de este repositorio sin configurarlos primero. Tampoco se distribuyen los documentos institucionales originales usados durante el desarrollo.

## Verificación

Pruebas que pueden ejecutarse sin plantillas ni Word:

```powershell
py -3.12 verificar_escuela_libre.py
py -3.12 verificar_ortografia.py
py -3.12 verificar_edicion.py
py -3.12 verificar_confirmacion.py
```

Las dos últimas abren ventanas de prueba. La suite de interfaz (`verificar_calidad.py`) comprueba 36 combinaciones de tamaño, formato y periodo, además de calendarios, desplazamiento, modales y recuperación de errores.

Con los recursos de impresión configurados, `self_check.py` y `verificar_portatil.py` permiten comprobar nueve recorridos de generación con datos ficticios. La versión operativa fue verificada extrayendo el paquete en otra carpeta y ejecutándolo sin Python en `PATH`.

## Construir un portátil

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe build_portable.py
```

La construcción requiere las plantillas y fuentes locales. Produce `Incapacidades_UIS_Portatil_Windows_x64.zip`, que se excluye de Git para no publicar recursos institucionales accidentalmente.

## Alcance y licencia

Herramienta administrativa: no diagnostica, prescribe ni decide si corresponde una incapacidad. El operador debe transcribir y verificar el soporte emitido por el profesional de salud.

Proyecto independiente de portafolio; no es una publicación oficial ni implica aval de una universidad. El código se distribuye bajo [licencia MIT](LICENSE). Los componentes del corrector conservan [su licencia](ortografia_datos/pyspellchecker-LICENSE.txt). Las marcas y recursos institucionales no quedan cubiertos por la licencia del código.
