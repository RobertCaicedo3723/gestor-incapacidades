from pathlib import Path
from unittest.mock import patch
from app import Aplicacion
from motor import TIPOS,MODOS_PERIODO
import tempfile

a=Aplicacion()
try:
    data=dict(tipo=TIPOS[0],modo_periodo=MODOS_PERIODO[0],accion='fue valorada en',fecha='14/10/2026',entidad='Hospital de Prueba',medico='Dra. Prueba',tratamiento='a la estudiante',nombre='Estudiante Ficticia',codigo='2000001',inicio='01/10/2026',fin='15/10/2026',especialidad='Medicina General',medico_general='Dra. General',registro='0000')
    for k,v in data.items():a.v[k].set(v)
    a.detail.insert('1.0',', según soporte ficticio')
    a.toggle();a.update()
    for size in ('980x640','1100x760','1280x900'):
        a.geometry(size);a.update()
        for b in (a.generate_button,a.pdf_button,a.save_button,a.new_button):
            assert b.winfo_ismapped()
            assert b.winfo_rooty()+b.winfo_height()<=a.winfo_rooty()+a.winfo_height(),'Botón fuera de la ventana principal'
    for size in ('820x480','820x600','820x700'):
        dialog=a.review();dialog.geometry(size);a.update()
        b=a.accept_button
        assert b.winfo_ismapped()
        assert b.winfo_rooty()+b.winfo_height()<=dialog.winfo_rooty()+dialog.winfo_height()
        with patch.object(a,'start') as start:b.invoke();assert start.called
        dialog.destroy()
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/'original.pdf';source.write_bytes(b'%PDF-prueba')
        target=Path(temp)/'copia.pdf';a.last=(source,source)
        with patch('app.filedialog.asksaveasfilename',return_value=str(target)):a.save_pdf()
        assert target.read_bytes()==source.read_bytes()
    a.v['nombre'].set('Otro caso');assert str(a.save_button.cget('state'))=='disabled'
    print('OK: aceptar visible y operativo a tres alturas, copia PDF e invalidación al editar.')
finally:a.destroy()
