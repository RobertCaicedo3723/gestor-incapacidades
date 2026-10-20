"""Construye un portátil usando recursos locales autorizados, nunca descargados."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parent


def main():
    required=['word_pdf.ps1','LICENSE','README.md',
              'plantillas/certificado_sin.docx','plantillas/certificado_con.docx',
              'plantillas/externa_legacy.doc','ortografia_datos/es.json.gz',
              'ortografia_datos/pyspellchecker-LICENSE.txt','ortografia_datos/LEEME.md']
    missing=[name for name in required if not (ROOT/name).is_file()]
    fonts=list((ROOT/'fuentes').glob('*.ttf'))
    if missing or not fonts:
        raise SystemExit('Configure los recursos locales descritos en README.md. Faltan: '+', '.join(missing+([] if fonts else ['fuentes/*.ttf'])))
    subprocess.run([sys.executable,'-c','import tkinter; r=tkinter.Tk(); r.withdraw(); r.destroy()'],check=True)
    cmd=[sys.executable,'-m','PyInstaller','--clean','--noconfirm','--onedir','--windowed',
         '--name','IncapacidadesUIS','--distpath',str(ROOT/'dist'),
         '--workpath',str(ROOT/'build'),'--specpath',str(ROOT/'build')]
    icon=ROOT/'assets/uis.ico'
    if icon.is_file():cmd+=['--icon',str(icon)]
    subprocess.run(cmd+[str(ROOT/'app.py')],cwd=ROOT,check=True)
    target=ROOT/'dist/IncapacidadesUIS'
    if not (target/'_internal/_tkinter.pyd').is_file() or not (target/'_internal/_tcl_data/init.tcl').is_file():
        raise RuntimeError('El paquete no contiene Tkinter completo.')
    for name in required+[p.relative_to(ROOT).as_posix() for p in fonts]:
        dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dst)
    logo=ROOT/'assets/uis-oficial.png'
    if logo.is_file():
        (target/'assets').mkdir(exist_ok=True);shutil.copy2(logo,target/'assets/uis-oficial.png')
    manifest={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file() and p.name!='MANIFIESTO.json'}
    (target/'MANIFIESTO.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=ROOT/'Incapacidades_UIS_Portatil_Windows_x64.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in target.rglob('*'):
            if p.is_file():z.write(p,'IncapacidadesUIS/'+p.relative_to(target).as_posix())
    print('Paquete local construido:',archive)


if __name__=='__main__':main()
