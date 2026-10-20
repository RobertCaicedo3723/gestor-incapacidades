"""Rellenado local de OOXML. Solo modifica word/document.xml; no reconstruye gráficos."""
from pathlib import Path
from xml.dom import minidom
import zipfile
import re
import datetime as dt
import subprocess
import tempfile
import uuid
import json
import sys
import os
import shutil
import ctypes
import hashlib
import winreg
import unicodedata

ROOT = Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent

_FUENTES_REGISTRADAS = False


def registrar_fuente_institucional():
    """Hace disponible Humanist 521 BT para Word sin requerir administrador.

    Las plantillas ya contienen la referencia a ``Humanst521 BT``.  En equipos
    sin esa fuente Word puede sustituirla silenciosamente; por eso la copia se
    instala en el perfil del usuario y se notifica el cambio a Windows antes de
    abrir Word.
    """
    global _FUENTES_REGISTRADAS
    if _FUENTES_REGISTRADAS or os.name != 'nt':
        return
    carpeta = ROOT / 'fuentes'
    archivos = tuple(carpeta.glob('*.ttf')) if carpeta.is_dir() else ()
    if not archivos:
        raise RuntimeError('No se encontró la carpeta de fuentes institucionales.')
    destino = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Microsoft' / 'Windows' / 'Fonts'
    destino.mkdir(parents=True, exist_ok=True)
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts') as clave:
            for archivo in archivos:
                salida = destino / archivo.name
                if not salida.exists() or hashlib.sha256(salida.read_bytes()).digest() != hashlib.sha256(archivo.read_bytes()).digest():
                    shutil.copy2(archivo, salida)
                # Windows usa el nombre del registro para enumerar fuentes de usuario;
                # el nombre interno del TTF conserva familia y variante tipográfica.
                winreg.SetValueEx(clave, f'Humanist 521 BT - {archivo.stem}', 0, winreg.REG_SZ, str(salida))
                ctypes.windll.gdi32.AddFontResourceW(str(salida))
        HWND_BROADCAST = 0xFFFF
        WM_FONTCHANGE = 0x001D
        ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0, 0x0002, 1000, None)
    except (OSError, PermissionError, FileNotFoundError) as exc:
        raise RuntimeError(f'No fue posible registrar la fuente institucional: {exc}') from exc
    _FUENTES_REGISTRADAS = True
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
MESES = ('enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre').split()
ESCUELAS = {
    'Facultad de Ciencias': ['Biología', 'Física', 'Matemáticas', 'Química'],
    'Facultad de Ciencias Humanas': ['Artes y Música', 'Derecho y Ciencia Política', 'Economía y Administración', 'Educación', 'Filosofía', 'Historia', 'Idiomas', 'Trabajo Social'],
    'Facultad de Ingenierías Fisicomecánicas': ['Diseño Industrial', 'Estudios Industriales y Empresariales', 'Ingeniería Civil', 'Ingeniería de Sistemas e Informática', 'Ingeniería Eléctrica, Electrónica y de Telecomunicaciones', 'Ingeniería Mecánica'],
    'Facultad de Ingenierías Fisicoquímicas': ['Geología', 'Ingeniería de Petróleos', 'Ingeniería Metalúrgica y Ciencia de los Materiales', 'Ingeniería Química'],
    'Facultad de Salud': ['Enfermería', 'Fisioterapia', 'Medicina', 'Microbiología', 'Nutrición y Dietética'],
}
TIPOS = ('Certificado sin prórroga (modelo 30 días)', 'Certificado con prórroga (modelo 30 días)', 'Remisión de incapacidad externa')

def es_externa(data): return data.get('tipo') == TIPOS[2]

def lleva_prorroga(data):
    return modo_periodo(data) == 'Prórroga'

MODOS_PERIODO = ('Sin periodo adicional', 'Prórroga', 'Incapacidad posterior independiente')

def modo_periodo(data):
    if data.get('modo_periodo'):
        return data['modo_periodo']
    return MODOS_PERIODO[1] if data.get('tipo') == TIPOS[1] or data.get('prorroga') in (True,'True','1','sí') else MODOS_PERIODO[0]

def tiene_periodo(data):
    return modo_periodo(data) != MODOS_PERIODO[0]

def texto(node):
    return ''.join(t.firstChild.data if t.firstChild else '' for t in node.getElementsByTagNameNS(W, 't'))

def reemplazar(node, old, new):
    """Sustituye un intervalo aunque esté fragmentado en runs, sin cambiar rPr/pPr."""
    nodes = list(node.getElementsByTagNameNS(W, 't'))
    values = [t.firstChild.data if t.firstChild else '' for t in nodes]
    full = ''.join(values)
    if full.count(old) != 1:
        raise ValueError(f'La plantilla no tiene un campo único esperado: {old[:50]}')
    start = full.index(old); end = start + len(old); offset = 0; inserted = False
    for t, value in zip(nodes, values):
        a, b = offset, offset + len(value); offset = b
        if b <= start or a >= end:
            continue
        updated = value[:max(0, start-a)]
        if not inserted:
            updated += new; inserted = True
        updated += value[max(0, end-a):] if end < b else ''
        while t.firstChild:
            t.removeChild(t.firstChild)
        t.appendChild(t.ownerDocument.createTextNode(updated))
        t.setAttribute('xml:space', 'preserve')

def paquete(src, dst, xml):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, xml if item.filename == 'word/document.xml' else zin.read(item.filename))

def preparar(src, dst):
    """Extrae el primer certificado de una plantilla externa compatible y crea slots."""
    with zipfile.ZipFile(src) as z:
        dom = minidom.parseString(z.read('word/document.xml'))
    body = dom.getElementsByTagNameNS(W, 'body')[0]
    ps = [p for p in body.childNodes if p.nodeType == p.ELEMENT_NODE and p.localName == 'p']
    if not ps or not texto(ps[0]).startswith('PARA:'):
        raise ValueError('Seleccione una plantilla de incapacidad externa con encabezado PARA.')
    ending = next((p for p in ps if texto(p).startswith('Copia:')), None)
    if ending is None:
        raise ValueError('No se encontró el cierre Copia: de la plantilla externa.')
    keep = True
    for child in list(body.childNodes):
        if child.nodeType == child.ELEMENT_NODE and child.localName == 'sectPr':
            continue
        if not keep:
            body.removeChild(child)
        if child is ending:
            keep = False
    ps = [p for p in body.childNodes if p.nodeType == p.ELEMENT_NODE and p.localName == 'p']
    # Cerrar marcadores que en el documento original abarcaban otros certificados.
    starts={n.getAttribute('w:id'): n for n in body.getElementsByTagNameNS(W,'bookmarkStart')}
    ends={n.getAttribute('w:id') for n in body.getElementsByTagNameNS(W,'bookmarkEnd')}
    for key in starts.keys()-ends:
        n=dom.createElementNS(W,'w:bookmarkEnd'); n.setAttribute('w:id',key); ending.appendChild(n)
    mappings = {}
    for p in ps:
        s=texto(p)
        if s.startswith('PARA:'):
            mappings['escuela']=s[len('PARA: '):]; reemplazar(p,mappings['escuela'],'{{escuela}}')
        elif s.startswith('FECHA:'):
            mappings['fecha']=s[len('FECHA: '):]; reemplazar(p,mappings['fecha'],'{{fecha}}')
        elif s.startswith('Remito Certificado'):
            pattern=r'emitida por (.+?), (DR[A]?\..+?), (al estudiante|a la estudiante) (.+?), Código estudiantil:?\s*(\d+), (?:Por|por) (.+?), durante el período del (\d{2}/\d{2}/\d{4}) al (\d{2}/\d{2}/\d{4})(.*)'
            m=re.search(pattern,s)
            if not m:
                raise ValueError('El texto del primer certificado no coincide con el modelo externo compatible.')
            keys=['entidad','medico','tratamiento','nombre','codigo','diagnostico','inicio','fin','extension']
            # Operar de derecha a izquierda para conservar las posiciones y el formato.
            for key,value in reversed(list(zip(keys,m.groups()))):
                mappings[key]=value
                reemplazar(p,value,'{{'+key+'}}')
        elif s.startswith('Anexos:'):
            mappings['folios']=s[len('Anexos: '):]; reemplazar(p,mappings['folios'],'{{folios}}')
    required={'escuela','fecha','entidad','medico','tratamiento','nombre','codigo','diagnostico','inicio','fin','extension','folios'}
    if set(mappings)!=required:
        raise ValueError('La plantilla no contiene todos los campos requeridos.')
    paquete(src,dst,dom.toxml(encoding='UTF-8'))
    return mappings

def preparar_sin(src,dst,con_prorroga=False):
    with zipfile.ZipFile(src) as z:
        dom=minidom.parseString(z.read('word/document.xml'))
    body=dom.getElementsByTagNameNS(W,'body')[0]
    ps=[p for p in body.childNodes if p.nodeType==p.ELEMENT_NODE and p.localName=='p']
    ending=next((p for p in ps if texto(p).strip()=='Coordinadora'),None)
    if ending is None: raise ValueError('No se encontró el cierre del certificado sin prórroga.')
    keep=True
    for child in list(body.childNodes):
        if child.nodeType==child.ELEMENT_NODE and child.localName=='sectPr': continue
        if not keep: body.removeChild(child)
        if child is ending: keep=False
    ps=[p for p in body.childNodes if p.nodeType==p.ELEMENT_NODE and p.localName=='p']
    mappings={}
    def slot(p,old,key):
        mappings[key]=old; reemplazar(p,old,'{{'+key+'}}')
    p=next(p for p in ps if texto(p).startswith('Que el estudiante'))
    s=texto(p)
    m=re.fullmatch(r'Que el estudiante\s+(.+?), identificado con código estudiantil\s+(\d+), (.+?)Hospital Universitario de Santander(.+)',s)
    if not m: raise ValueError('La descripción clínica no coincide con el modelo de referencia.')
    # Cada intervalo mantiene el formato del run original en que comienza.
    for key,value in reversed(list(zip(['nombre','codigo','atencion','entidad','detalle'],[m[1],m[2],m[3],'Hospital Universitario de Santander',m[4]]))):
        slot(p,value,key)
    slot(p,'Que el estudiante','presentacion')
    slot(p,'identificado con código estudiantil','identificacion')
    p=next(p for p in ps if texto(p).startswith('Como parte'))
    s=texto(p)
    m=re.fullmatch(r'.*?incapacidad médica por (30) días, con fecha de inicio el (.+?) y finalización el (.+?), según constancia firmada por el (.+?), médico especialista en (.+?)\.',s)
    if not m: raise ValueError('No se encontraron las fechas y el médico en el modelo sin prórroga.')
    for key,value in reversed(list(zip(['dias','inicio','fin','medico','especialidad'],m.groups()))): slot(p,value,key)
    if con_prorroga:
        # Reutilizar runs normales y en negrita del mismo párrafo para la variante.
        runs=list(p.getElementsByTagNameNS(W,'r'))
        def active_bold(run):
            b=list(run.getElementsByTagNameNS(W,'b'))
            if b:return b[0].getAttribute('w:val') not in ('0','false','off')
            return any(s.getAttribute('w:val')=='Textoennegrita' for s in run.getElementsByTagNameNS(W,'rStyle'))
        normal=next(r for r in runs if not active_bold(r))
        bold=next(r for r in runs if active_bold(r))
        for value,is_bold in [(' Con prórroga hasta el ',False),('{{hasta}}',True),(', según constancia firmada por ',False),('{{medico_prorroga}}',True),('{{entidad_prorroga}}',True),('.',False)]:
            run=(bold if is_bold else normal).cloneNode(True)
            for child in list(run.childNodes):
                if child.nodeType==child.ELEMENT_NODE and child.localName!='rPr': run.removeChild(child)
            t=dom.createElementNS(W,'w:t'); t.setAttribute('xml:space','preserve'); t.appendChild(dom.createTextNode(value));run.appendChild(t);p.appendChild(run)
        mappings.update(hasta='',medico_prorroga='',entidad_prorroga='')
    p=next(p for p in ps if texto(p).startswith('Médico General:'))
    slot(p,texto(p).split(': ',1)[1],'medico_general')
    p=next(p for p in ps if texto(p).startswith('Registro médico:'))
    slot(p,texto(p).split(': ',1)[1],'registro')
    p=next(p for p in ps if texto(p).startswith('Se expide'))
    slot(p,texto(p),'expedicion')
    paquete(src,dst,dom.toxml(encoding='UTF-8'))
    return mappings

def fecha(value):
    try:
        return dt.datetime.strptime(value.strip(),'%d/%m/%Y').date()
    except ValueError:
        raise ValueError('Escriba una fecha válida en formato DD/MM/AAAA.') from None

def folios_texto(n):
    small=['','Un','Dos','Tres','Cuatro','Cinco','Seis','Siete','Ocho','Nueve','Diez','Once','Doce','Trece','Catorce','Quince','Dieciséis','Diecisiete','Dieciocho','Diecinueve','Veinte']
    number=small[n] if n<=20 else str(n)
    return number+(' folio útil.' if n==1 else ' folios útiles.')

def validar(data):
    d={k:str(v).strip() for k,v in data.items()}
    if es_externa(d) and any(unicodedata.category(c) in ('Cc','Zl','Zp') for c in str(data.get('escuela',''))):
        raise ValueError('El campo escuela debe ocupar una sola línea y no contener caracteres de control.')
    required=['tipo','fecha','entidad','medico','tratamiento','nombre','codigo','diagnostico','inicio','fin']
    required+=['escuela','folios'] if es_externa(d) else ['especialidad','medico_general','registro','accion']
    for k in required:
        if not d.get(k):
            raise ValueError(f'Complete el campo {k}.')
        if any(ord(c)<32 for c in d[k]):
            raise ValueError(f'El campo {k} debe ocupar una sola línea.')
        if '{{' in d[k] or '}}' in d[k]:raise ValueError(f'El campo {k} contiene marcas reservadas de la plantilla.')
    if d['tipo'] not in TIPOS: raise ValueError('Seleccione un tipo válido.')
    if d['tratamiento'] not in ('al estudiante','a la estudiante'): raise ValueError('Seleccione el tratamiento del estudiante.')
    if not re.fullmatch(r'[0-9]{7}',d['codigo']): raise ValueError('El código estudiantil debe tener 7 dígitos del 0 al 9.')
    if not d['diagnostico'].strip('.,;: '):raise ValueError('Escriba el diagnóstico o detalle clínico; no solo signos de puntuación.')
    if modo_periodo(d) not in MODOS_PERIODO: raise ValueError('Seleccione el tipo de periodo adicional.')
    applicable=set(required)|({'hasta','medico_prorroga','entidad_prorroga','inicio_adicional'} if tiene_periodo(d) else set())
    for k,limit in {'nombre':100,'escuela':160,'entidad':160,'medico':120,'diagnostico':350 if es_externa(d) else 600,'medico_prorroga':120,'entidad_prorroga':160,'especialidad':100,'medico_general':120,'registro':30,'accion':100}.items():
        if k in applicable and len(d.get(k,''))>limit: raise ValueError(f'El campo {k} supera {limit} caracteres.')
    issued,start,end=fecha(d['fecha']),fecha(d['inicio']),fecha(d['fin'])
    if end<start: raise ValueError('La fecha fin debe ser igual o posterior al inicio.')
    if es_externa(d) and (not re.fullmatch(r'[0-9]{1,3}',d['folios']) or not 1<=int(d['folios'])<=999): raise ValueError('Indique entre 1 y 999 folios.')
    adicional=''
    if tiene_periodo(d):
        if not d.get('hasta') or not d.get('medico_prorroga'): raise ValueError('Complete la fecha y el médico de la prórroga.')
        until=fecha(d['hasta'])
        second_start=fecha(d['inicio_adicional']) if d.get('inicio_adicional') else end+dt.timedelta(days=1)
        if second_start<=end: raise ValueError('El periodo adicional debe comenzar después del fin inicial.')
        if until<second_start: raise ValueError('El fin adicional debe ser igual o posterior a su inicio.')
        for k in ['medico_prorroga','entidad_prorroga']:
            if any(ord(c)<32 for c in d.get(k,'')): raise ValueError('La prórroga debe ocupar una sola línea.')
            if '{{' in d.get(k,'') or '}}' in d.get(k,''):raise ValueError('La prórroga contiene marcas reservadas de la plantilla.')
        def larga(date): return f'{date.day:02} de {MESES[date.month-1]} de {date.year}'
        nombre_periodo='Prórroga' if lleva_prorroga(d) else 'Incapacidad posterior independiente'
        adicional=f"{nombre_periodo} del {larga(second_start)} al {larga(until)}, según constancia firmada por {d['medico_prorroga']}"
        if d.get('entidad_prorroga'): adicional+=', '+d['entidad_prorroga']
        adicional+='.'
    if not es_externa(d):
        def larga(date): return f'{date.day:02} de {MESES[date.month-1]} de {date.year}'
        female=d['tratamiento']=='a la estudiante'
        values={'presentacion':'Que la estudiante' if female else 'Que el estudiante',
                'identificacion':'identificada con código estudiantil' if female else 'identificado con código estudiantil',
                'nombre':d['nombre'],'codigo':d['codigo'],'atencion':d['accion']+' ',
                'entidad':d['entidad'],'detalle':('' if d['diagnostico'][0] in ',;:.' else ' ')+d['diagnostico'].rstrip('., ')+'.',
                'dias':str((end-start).days+1),'inicio':larga(start),'fin':larga(end),
                'medico':d['medico'],'especialidad':d['especialidad'],'medico_general':d['medico_general'],'registro':d['registro'],
                'expedicion':f'Se expide a solicitud del interesado a los ({issued.day:02}) días del mes de {MESES[issued.month-1]} de {issued.year}.'}
        if adicional: values['periodo_adicional']=adicional
        return values
    extension='.'
    if adicional: extension='. '+adicional
    return {
        'escuela':d['escuela'].upper(),
        'fecha':f'{issued.day:02} DE {MESES[issued.month-1].upper()} DE {issued.year}',
        'entidad':d['entidad'].upper(),'medico':d['medico'].upper(),
        'tratamiento':d['tratamiento'],'nombre':d['nombre'].upper(),'codigo':d['codigo'],
        'diagnostico':d['diagnostico'].upper().rstrip('.,'),
        'inicio':f'{start:%d/%m/%Y}','fin':f'{end:%d/%m/%Y}',
        'extension':extension,'folios':folios_texto(int(d['folios'])),
    }

def parrafo_clinico(values):
    return (f"{values['presentacion']} {values['nombre']}, {values['identificacion']} "
            f"{values['codigo']}, {values['atencion']}{values['entidad']}{values['detalle']}")

def firmante_medico(nombre):
    """Añade el artículo del título sin duplicar el escrito por el operador."""
    nombre=nombre.strip()
    articulo=re.match(r'(?i)^(el|la)\s+(.+)$',nombre)
    if articulo:return articulo[1].lower()+' '+articulo[2]
    if re.match(r'(?i)^(dra\.?|doctora)\s',nombre):return 'la '+nombre
    if re.match(r'(?i)^(dr\.?|doctor)\s',nombre):return 'el '+nombre
    return nombre

def generar(data, output_dir, template=None):
    values=validar(data)
    registrar_fuente_institucional()
    template=Path(template or ROOT/'plantillas'/('externa_campos.docx' if es_externa(data) else 'certificado_sin.docx'))
    if not str(output_dir).strip():raise ValueError('Seleccione una carpeta para guardar los documentos.')
    output_dir=Path(output_dir).resolve();output_dir.mkdir(parents=True,exist_ok=True)
    source=ROOT/'plantillas/externa_legacy.doc' if es_externa(data) else template
    if not source.is_file() or not (ROOT/'word_pdf.ps1').is_file():
        raise RuntimeError('Faltan archivos del programa. Descomprima la carpeta portátil completa, no solo el ejecutable.')
    suffix='con_prorroga' if lleva_prorroga(data) else 'periodo_independiente' if tiene_periodo(data) else 'sin_prorroga'
    name=f"{values['codigo']}_{'externa' if es_externa(data) else 'certificado'}_{suffix}_{dt.datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    # Se trabaja en una carpeta temporal: si Word detecta desbordamiento, no se publica.
    with tempfile.TemporaryDirectory(prefix='incapacidad_') as temp:
        temp=Path(temp); docx=temp/(name+'.docx'); pdf=temp/(name+'.pdf')
        if es_externa(data):
            # PDF directamente desde DOC: no cambiar el motor de compatibilidad legacy.
            fields=temp/'campos.json'; fields.write_text(json.dumps(values,ensure_ascii=False),encoding='utf-8')
            exportar(ROOT/'plantillas/externa_legacy.doc',pdf,fields,docx)
        else:
            with zipfile.ZipFile(template) as z:
                dom=minidom.parseString(z.read('word/document.xml'))
            ps=dom.getElementsByTagNameNS(W,'p')
            medico=firmante_medico(values['medico'])
            medico_p=next(p for p in ps if '{{medico}}' in texto(p))
            reemplazar(medico_p,'constancia firmada por el ','constancia firmada por ')
            if medico.startswith('la '):reemplazar(medico_p,', médico especialista en ',', médica especialista en ')
            for key,value in values.items():
                if key=='medico':value=medico
                if key=='periodo_adicional':
                    p=next(p for p in ps if '{{dias}}' in texto(p) or texto(p).startswith('Como parte'))
                    sample=next(r for r in p.getElementsByTagNameNS(W,'r') if r.getElementsByTagNameNS(W,'t'))
                    run=sample.cloneNode(True)
                    for child in list(run.childNodes):
                        if child.nodeType==child.ELEMENT_NODE and child.localName!='rPr':run.removeChild(child)
                    t=dom.createElementNS(W,'w:t');t.setAttribute('xml:space','preserve');t.appendChild(dom.createTextNode(' '+value));run.appendChild(t);p.appendChild(run)
                    continue
                matches=[p for p in ps if '{{'+key+'}}' in texto(p)]
                if len(matches)!=1: raise ValueError(f'Plantilla dañada: campo {key}.')
                reemplazar(matches[0],'{{'+key+'}}',value)
            paquete(template,docx,dom.toxml(encoding='UTF-8'))
            exportar(docx,pdf)
        publicar(docx,pdf,output_dir)
    return output_dir/(name+'.docx'),output_dir/(name+'.pdf')

def publicar(docx,pdf,output_dir):
    """Preparar ambas copias antes de publicar; revertir solo archivos de este caso."""
    published=[]
    with tempfile.TemporaryDirectory(prefix='.incapacidad_',dir=output_dir) as staging:
        staging=Path(staging)
        for source in (docx,pdf):shutil.copy2(source,staging/source.name)
        try:
            for source in (docx,pdf):
                target=Path(output_dir)/source.name
                if target.exists():raise FileExistsError('Ya existe un documento con ese nombre.')
                # En Windows rename no reemplaza un destino existente.
                os.rename(staging/source.name,target);published.append(target)
        except Exception:
            for target in published:target.unlink(missing_ok=True)
            raise

def exportar(docx,pdf,fields=None,output_docx=None):
    powershell=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    command=[str(powershell),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'word_pdf.ps1'),'-InputPath',str(Path(docx).resolve()),'-OutputPath',str(Path(pdf).resolve())]
    if fields:command+=['-FieldsPath',str(Path(fields).resolve()),'-DocxPath',str(Path(output_docx).resolve())]
    try:
        result=subprocess.run(command,capture_output=True,timeout=100,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired as e:
        detail=(e.stdout or b'').decode('utf-8',errors='replace')[-400:]
        raise RuntimeError('Word tardó demasiado. Revise si tiene un diálogo abierto y vuelva a intentarlo.\n'+detail) from None
    if result.returncode or not Path(pdf).is_file():
        detail=result.stderr.decode('utf-8',errors='replace')[-1800:]
        if any(word in detail.lower() for word in ('80040154','no registrada','not registered')):
            raise RuntimeError('No se encontró Microsoft Word de escritorio. Instálelo o active su instalación antes de generar documentos.')
        raise RuntimeError('No se pudo generar el PDF. Compruebe Microsoft Word.\n'+detail)
