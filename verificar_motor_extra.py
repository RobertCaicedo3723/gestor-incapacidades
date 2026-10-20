import tempfile
from pathlib import Path
from unittest.mock import patch
from motor import validar,TIPOS,publicar
from self_check import run

# Validaciones de entradas que antes podían convertirse en errores internos.
data=dict(tipo=TIPOS[2],facultad='Facultad de Salud',escuela='Medicina',fecha='14/10/2026',entidad='Entidad de Prueba',medico='Dr. Médico de Prueba',tratamiento='al estudiante',nombre='Estudiante de Prueba',codigo='2000001',diagnostico='Diagnóstico ficticio',inicio='01/10/2026',fin='30/10/2026',folios='2',prorroga=False)
for key,value in [('codigo','٢٠٠٠٠٠١'),('diagnostico','...'),('folios','²'),('folios','9'*5000),('nombre','{{codigo}}')]:
    case=dict(data);case[key]=value
    try:validar(case)
    except ValueError:pass
    else:raise AssertionError('Entrada inválida aceptada: '+key)
with tempfile.TemporaryDirectory(prefix='uis_publicacion_') as temp:
    root=Path(temp);source=root/'fuente';source.mkdir();out=root/'destino';out.mkdir()
    docx=source/'prueba.docx';pdf=source/'prueba.pdf';docx.write_bytes(b'docx');pdf.write_bytes(b'pdf')
    old=out/'anterior.pdf';old.write_bytes(b'conservar')
    import motor
    rename=motor.os.rename
    def fail_second(src,dst):
        if str(dst).endswith('.pdf'):raise OSError('Fallo simulado de publicación')
        return rename(src,dst)
    with patch('motor.os.rename',side_effect=fail_second):
        try:publicar(docx,pdf,out)
        except OSError:pass
        else:raise AssertionError('No ocurrió el fallo simulado')
    assert set(out.iterdir())=={old} and old.read_bytes()==b'conservar'
    publicar(docx,pdf,out)
    assert (out/docx.name).read_bytes()==b'docx' and (out/pdf.name).read_bytes()==b'pdf'
print('OK: validaciones especiales y publicación sin archivos parciales ni pérdida de documentos anteriores.')
