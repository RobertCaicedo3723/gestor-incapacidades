"""Autoprueba del paquete instalado; crea únicamente casos ficticios identificados."""
from pathlib import Path
import sys,json,hashlib,zipfile,datetime

def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    report={'ejecutable_portatil':bool(getattr(sys,'frozen',False)),'fecha':datetime.datetime.now().isoformat(),'estado':'en curso'}
    try:
        from verificar_calidad import check_ui
        from verificar_edicion import check_edicion
        from motor import ROOT,TIPOS,MODOS_PERIODO,generar,validar
        report['edicion']=check_edicion()
        report['interfaz']=check_ui();report['documentos']=[]
        for i,(kind,mode) in enumerate([(kind,mode) for kind in TIPOS for mode in MODOS_PERIODO]):
            extension=mode==MODOS_PERIODO[1]
            data=dict(tipo=kind,accion='fue valorada en',facultad='Facultad de Salud',escuela='Medicina',fecha='14/10/2026',entidad='Hospital de Prueba',medico='Dra. Médica de Prueba',tratamiento='a la estudiante',nombre='Estudiante Ficticia de Prueba',codigo='2000001',diagnostico=', según soporte clínico de prueba' if i<2 else 'DIAGNÓSTICO FICTICIO DE PRUEBA',inicio='01/10/2026',fin='30/10/2026',folios='2',hasta='14/11/2026',medico_prorroga='Dr. Médico de Prueba',entidad_prorroga='Entidad de Prueba',especialidad='Medicina General',medico_general='Dr. Médico General de Prueba',registro='0000',prorroga=extension)
            data.update(modo_periodo=mode,inicio_adicional='31/10/2026')
            if kind==TIPOS[2]:data['escuela']='Esc. de Tecnologías Emergentes (E.T.E.)'
            docx,pdf=generar(data,output/'documentos_ficticios')
            assert pdf.read_bytes().startswith(b'%PDF-')
            with zipfile.ZipFile(docx) as z:
                assert z.testzip() is None
                if kind==TIPOS[2]:
                    from xml.dom import minidom
                    from motor import texto
                    assert data['escuela'].upper() in texto(minidom.parseString(z.read('word/document.xml')))
                else:
                    from xml.dom import minidom
                    from motor import texto
                    assert 'firmada por la Dra. Médica de Prueba' in texto(minidom.parseString(z.read('word/document.xml')))
            report['documentos'].append({'tipo':kind,'periodo':mode,'pdf':pdf.name,'word':docx.name})
        report['estado']='correcto';report['carpeta_programa']=str(ROOT)
        return_code=0
    except Exception as e:
        report.update(estado='error',error=f'{type(e).__name__}: {e}');return_code=1
    (output/'autoprueba.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return return_code
