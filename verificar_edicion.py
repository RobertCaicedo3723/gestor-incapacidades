"""Prueba el menú contextual en widgets reales con palabras y casos ficticios."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
from app import Aplicacion
from motor import TIPOS,firmante_medico


def check_edicion(a=None):
    own=a is None
    if own:a=Aplicacion()
    errors=[];a.report_callback_exception=lambda *e:errors.append(str(e[1]))
    try:
        a.fields['tipo'].current(2);a.fields['tipo'].event_generate('<<ComboboxSelected>>');a.update()
        escuela=a.fields['escuela']
        assert isinstance(escuela,ttk.Entry) and not isinstance(escuela,ttk.Combobox)
        assert a.help_labels['escuela'].winfo_rooty()+a.help_labels['escuela'].winfo_height()<=escuela.winfo_rooty()
        assert 'Hospital Universitario' in a.help_labels['entidad'].cget('text')
        assert firmante_medico('Dra. Ana Pérez')=='la Dra. Ana Pérez'
        assert firmante_medico('La Dra. Ana Pérez')=='la Dra. Ana Pérez'
        assert firmante_medico('Dr. Juan Gómez')=='el Dr. Juan Gómez'
        assert firmante_medico('el Dr. Juan Gómez')=='el Dr. Juan Gómez'
        a.v['escuela'].set('Esc. de Nuevas Tecnologías (E.N.T.)')
        assert a.data()['escuela']=='Esc. de Nuevas Tecnologías (E.N.T.)'
        assert a.edicion.corrector is None or a.edicion.corrector.disponible
        for key in ('escuela','nombre','entidad','medico','especialidad','medico_general','medico_prorroga','entidad_prorroga','accion'):
            assert a.fields[key].bind('<Button-3>'),key
        assert a.detail.bind('<Button-3>')
        a.v['escuela'].set('Escuela de biolgia (UIS)')
        a.goto_section(a.school);a.update()
        x,y,w,h=escuela.bbox(12)
        with patch.object(tk.Menu,'tk_popup') as popup:
            escuela.event_generate('<Button-3>',x=x+2,y=y+h//2,rootx=escuela.winfo_rootx()+x+2,rooty=escuela.winfo_rooty()+y+h//2)
            assert popup.called,'El clic derecho no intentó mostrar el menú'
        a.update()
        menu=a.edicion.menu
        assert menu is not None,'Clic derecho no abrió el menú'
        labels=[menu.entrycget(i,'label') for i in range(menu.index('end')+1) if menu.type(i)!='separator']
        assert 'biología' in labels,labels
        assert a.v['escuela'].get()=='Escuela de biolgia (UIS)','Se corrigió sin elegir sugerencia'
        a.last=(Path('anterior.docx'),Path('anterior.pdf'));a.pdf_button.configure(state='normal');a.save_button.configure(state='normal')
        index=next(i for i in range(menu.index('end')+1) if menu.type(i)!='separator' and menu.entrycget(i,'label')=='biología')
        menu.unpost();menu.invoke(index);a.update()
        assert a.v['escuela'].get()=='Escuela de biología (UIS)'
        assert a.last is None and str(a.save_button.cget('state'))=='disabled'
        a.v['tipo'].set(TIPOS[0]);a.toggle();a.detail.delete('1.0','end')
        a.detail.insert('1.0','Según soporte:\nLa incapasidad médica continúa.');a.goto_section(a.clinical);a.update()
        a.detail.see('2.5');a.update()
        x,y,w,h=a.detail.bbox('2.5')
        with patch.object(tk.Menu,'tk_popup') as popup:
            a.detail.event_generate('<Button-3>',x=x+2,y=y+h//2,rootx=a.detail.winfo_rootx()+x+2,rooty=a.detail.winfo_rooty()+y+h//2)
            assert popup.called
        a.update();menu=a.edicion.menu
        index=next(i for i in range(menu.index('end')+1) if menu.type(i)!='separator' and menu.entrycget(i,'label')=='incapacidad')
        menu.unpost();menu.invoke(index);a.update()
        assert a.detail.get('1.0','end-1c')=='Según soporte:\nLa incapacidad médica continúa.'
        a.detail.edit_undo();a.update()
        assert a.detail.get('1.0','end-1c')=='Según soporte:\nLa incapasidad médica continúa.'
        a.lock_form(True)
        before=a.detail.get('1.0','end-1c')
        a.edicion.reemplazar((a.detail,'2.3','2.14','incapasidad'),'incapacidad')
        assert a.detail.get('1.0','end-1c')==before
        a.lock_form(False)
        a.clear(confirm=False);a.update()
        assert not a.v['escuela'].get() and not a.detail.get('1.0','end-1c')
        assert not errors,errors
        return {'escuela_texto_libre':True,'clic_derecho_entry_y_text':True,'correccion_solo_al_elegir':True,'pdf_invalidado_al_corregir':True,'deshacer_texto':True,'sin_edicion_durante_generacion':True}
    finally:
        if a.edicion.menu:a.edicion.menu.unpost()
        if own:a.destroy()


if __name__=='__main__':
    print(check_edicion())
