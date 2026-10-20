"""Auditoría de eventos reales Tk y tamaños, sin imprimir ni usar datos reales."""
from pathlib import Path
import json
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
from app import Aplicacion
from motor import TIPOS,ROOT,MODOS_PERIODO

def check_ui():
    a=Aplicacion();a.title('UIS · Auditoría de calidad')
    errors=[];a.report_callback_exception=lambda *e:errors.append(str(e[1]))
    checks=[]
    try:
        for size in ('980x640','980x680','1100x760','1280x900'):
            a.geometry(size);a.update()
            for kind,mode in [(kind,mode) for kind in TIPOS for mode in MODOS_PERIODO]:
                a.fields['tipo'].current(TIPOS.index(kind));a.fields['tipo'].event_generate('<<ComboboxSelected>>');a.update()
                assert tuple(a.fields['modo_periodo'].cget('values'))==MODOS_PERIODO
                assert a.fields['modo_periodo'].winfo_ismapped(),'El selector debe mostrarse en todos los formatos'
                a.fields['modo_periodo'].current(MODOS_PERIODO.index(mode));a.fields['modo_periodo'].event_generate('<<ComboboxSelected>>');a.update();a.update_idletasks()
                assert a.data()['modo_periodo']==mode
                assert bool(a.extension.winfo_ismapped())==(mode!=MODOS_PERIODO[0]),'El selector no muestra/oculta los campos correctos'
                for frame,button in a.nav_buttons:
                    a.goto_section(frame);a.update()
                    assert button.winfo_reqwidth()<=button.winfo_width(),f'Navegación recortada: {button.cget("text")}, {size}'
                    assert button.winfo_reqheight()<=button.winfo_height(),f'Navegación sin altura: {size}'
                a.status.configure(text='PDF y Word guardados. Abra el PDF para revisar e imprimir a tamaño real (100%).')
                a.update()
                def inspect(widget):
                    if isinstance(widget,ttk.Label) and widget.winfo_ismapped() and not str(widget.cget('image')):
                        if widget.cget('text'):
                            assert widget.winfo_reqwidth()<=widget.winfo_width()+1,f'Ancho insuficiente: {widget.cget("text")}, {size}'
                            assert widget.winfo_reqheight()<=widget.winfo_height()+1,f'Altura insuficiente: {widget.cget("text")}, {size}'
                    for child in widget.winfo_children():inspect(child)
                inspect(a)
                # La rueda se entrega al propio selector: detecta el bug de clase.
                for field in (w for w in a.fields.values() if isinstance(w,ttk.Combobox)):
                    before=a.data();a.canvas.yview_moveto(0);a.update()
                    field.event_generate('<MouseWheel>',delta=-120);a.update()
                    assert a.data()==before,'La rueda cambió una opción del caso'
                    assert a.canvas.yview()[0]>0,'La rueda debe desplazar el formulario sobre un selector cerrado'
                a.canvas.yview_moveto(0);a.update()
                a.fields['nombre'].event_generate('<MouseWheel>',delta=-15);a.update()
                assert a.canvas.yview()[0]>0,'Se perdieron los eventos de touchpad'
                checks.append(f'{size}: {kind}, periodo={mode}')
        a.last=(Path('anterior.docx'),Path('anterior.pdf'));a.pdf_button.configure(state='normal')
        a.v['nombre'].set('Caso nuevo')
        assert a.last is None and str(a.pdf_button['state'])=='disabled'
        a.last=(Path('anterior.docx'),Path('anterior.pdf'));a.detail.insert('1.0','Cambio clínico');a.update()
        assert a.last is None
        a.clear(confirm=False);a.update()
        for key in ('fecha','inicio','fin','inicio_adicional','hasta'):
            a.v[key].set('16/10/2026');dialog=a.select_date(key);a.update()
            def buttons(w):
                result=[w] if isinstance(w,ttk.Button) else []
                for child in w.winfo_children():result+=buttons(child)
                return result
            next(b for b in buttons(dialog) if b.cget('text')=='20').invoke();a.update()
            assert a.v[key].get()=='20/10/2026','El calendario no devolvió la fecha elegida'
        a.clear(confirm=False);a.update()
        try:a.detail.edit_undo()
        except tk.TclError:pass
        else:raise AssertionError('Deshacer recuperó datos de un estudiante anterior')
        a.lock_form(True)
        assert all(str(w['state'])=='disabled' for w in a.fields.values())
        assert str(a.new_button['state'])=='disabled'
        a.lock_form(False)
        assert str(a.fields['tipo']['state'])=='readonly'
        assert str(a.fields['accion']['state'])=='normal'
        assert not a._locked_controls
        dialog=tk.Toplevel(a);dialog.title('Prueba modal');dialog.grab_set();a.update()
        before=a.canvas.yview();a.fields['tipo'].event_generate('<MouseWheel>',delta=-120);a.update()
        assert a.canvas.yview()==before,'La rueda atravesó un diálogo modal'
        dialog.destroy();a.update()
        a.results.put(('error','Fallo simulado de exportación'));a.busy=True;a.lock_form(True)
        with patch.object(a,'show_error') as error:a.poll();assert error.called
        assert not a.busy and str(a.new_button['state'])=='normal'
        long_error='Mensaje de prueba con una ruta extensa y explicación. '*100
        error_dialog=a.show_error('Prueba de error largo',long_error);a.update()
        error_text=next(w for area in error_dialog.winfo_children() for w in area.winfo_children() if isinstance(w,tk.Text))
        assert error_text.get('1.0','end').strip()==long_error.strip()
        assert error_text.yview()[1]<1,'El error largo debe poder desplazarse'
        error_dialog.destroy();a.update()
        assert not errors,errors
        return {'distribuciones':checks,'rueda_sin_cambio_datos':True,'touchpad':True,'modal_aislado':True,'pdf_anterior_invalidado':True,'sin_undo_entre_estudiantes':True,'recuperacion_error':True,'errores_callback':errors,'dpi':a.winfo_fpixels('1i')}
    finally:a.destroy()

if __name__=='__main__':
    (ROOT/'qa').mkdir(exist_ok=True)
    result=check_ui()
    (ROOT/'qa/informe_interfaz.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"OK: {len(result['distribuciones'])} combinaciones de tamaño y formato, rueda, touchpad, modales, PDF anterior, deshacer y recuperación de errores.")
