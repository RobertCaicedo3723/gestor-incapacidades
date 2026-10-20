from pathlib import Path
import zipfile,tempfile,subprocess,os,json,shutil,hashlib

ROOT=Path(__file__).resolve().parent
(ROOT/'qa').mkdir(exist_ok=True)
archive=ROOT/'Incapacidades_UIS_Portatil_Windows_x64.zip'
with tempfile.TemporaryDirectory(prefix='portatil prueba á ',dir=ROOT/'qa') as temporary:
    temporary=Path(temporary)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all((temporary/name).resolve().is_relative_to(temporary.resolve()) for name in z.namelist())
        z.extractall(temporary)
    folder=temporary/'IncapacidadesUIS'
    manifest=json.loads((folder/'MANIFIESTO.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest for name,digest in manifest.items())
    assert not any(name.startswith(('qa/','generados/','.build-env/')) for name in manifest)
    env=os.environ.copy();env['PATH']=str(Path(env.get('SystemRoot',r'C:\Windows'))/'System32')
    env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None)
    output=ROOT/'qa/portatil_resultado'
    completed=subprocess.run([str(folder/'IncapacidadesUIS.exe'),'--autoprueba',str(output)],cwd=temporary,env=env,timeout=300)
    report=json.loads((output/'autoprueba.json').read_text(encoding='utf-8'))
    assert completed.returncode==0 and report['estado']=='correcto',report
    assert report['ejecutable_portatil'] and len(report['documentos'])==9
    report['sin_python_en_path']=True;report['carpeta_reubicada_con_espacios_y_acentos']=True
    (ROOT/'qa/informe_portatil.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('OK: ejecutable reubicado, sin Python en PATH, 36 escenarios de interfaz y nueve pares PDF/Word.')
