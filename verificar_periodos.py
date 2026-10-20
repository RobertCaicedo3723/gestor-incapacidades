"""Comprueba periodos adicionales con profesionales distintos y fechas explícitas."""
from pathlib import Path
import json
import zipfile
from xml.dom import minidom
from motor import ROOT,TIPOS,MODOS_PERIODO,validar,generar,texto,W

def run():
    out=ROOT/'qa/periodos';out.mkdir(parents=True,exist_ok=True)
    results=[]
    for i,kind in enumerate(TIPOS):
        for j,mode in enumerate(MODOS_PERIODO):
            d=dict(tipo=kind,modo_periodo=mode,accion='fue valorada en',facultad='Facultad de Salud',escuela='Medicina',fecha='21/10/2026',entidad='Hospital de Prueba',medico='Dra. Primera de Prueba',tratamiento='a la estudiante',nombre='Estudiante Ficticia',codigo='2000001',diagnostico=', según soporte clínico de prueba',inicio='01/10/2026',fin='15/10/2026',folios='2',inicio_adicional='16/10/2026',hasta='20/10/2026',medico_prorroga='Dr. Segundo de Prueba',entidad_prorroga='Clínica de Prueba',especialidad='Medicina General',medico_general='Dra. General de Prueba',registro='0000')
            docx,pdf=generar(d,out)
            with zipfile.ZipFile(docx) as z:
                s=texto(minidom.parseString(z.read('word/document.xml')))
            if j:
                assert 'Dr. Segundo de Prueba' in s
                assert '16 de octubre de 2026' in s and '20 de octubre de 2026' in s
                assert mode in s
                if j==2:assert 'prórroga' not in s.lower() and 'prorroga' not in s.lower()
            else:assert 'Dr. Segundo de Prueba' not in s
            results.append({'formato':kind,'periodo':mode,'pdf':str(pdf)})
    d.update(modo_periodo=MODOS_PERIODO[2],inicio_adicional='14/10/2026')
    try:validar(d)
    except ValueError:pass
    else:raise AssertionError('Se permitió solapamiento')
    (out/'informe.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('OK: nueve combinaciones, fechas propias, médico distinto y sin palabra prórroga en independientes.')

if __name__=='__main__':run()
