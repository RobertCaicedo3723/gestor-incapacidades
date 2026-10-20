"""Menú contextual de edición y sugerencias locales, sin reemplazos automáticos."""
import re
import tkinter as tk
from ortografia import CorrectorEspanol

PALABRAS = re.compile(r'[^\W\d_]+', re.UNICODE)


class EditorTexto:
    def __init__(self, root):
        self.root=root
        self.corrector=None
        self.menu=None

    def instalar(self, widget):
        widget.bind('<Button-3>', self.abrir, add='+')
        widget.bind('<Shift-F10>', lambda event:self.abrir(event, teclado=True), add='+')
        widget.bind('<Menu>', lambda event:self.abrir(event, teclado=True), add='+')

    def objetivo(self, widget, x=0, y=0, teclado=False):
        """Localiza solo la palabra bajo el puntero o el cursor de escritura."""
        if isinstance(widget,tk.Text):
            contenido=widget.get('1.0','end-1c')
            indice=widget.index('insert' if teclado else f'@{int(x)},{int(y)}')
            cuenta=widget.count('1.0',indice,'chars')
            posicion=int(cuenta[0]) if cuenta else 0
        else:
            contenido=widget.get()
            posicion=int(widget.index('insert' if teclado else f'@{int(x)}'))
        for palabra in PALABRAS.finditer(contenido):
            if palabra.start()<=posicion<palabra.end() or posicion==len(contenido)==palabra.end():
                if isinstance(widget,tk.Text):
                    inicio=f'1.0+{palabra.start()}c';fin=f'1.0+{palabra.end()}c'
                else:inicio,fin=palabra.span()
                return (widget,inicio,fin,palabra.group())
        return None

    def preparar(self, widget, objetivo):
        """Construye el menú; separado de su despliegue para verificar sus acciones."""
        if self.menu is not None:self.menu.destroy()
        menu=self.menu=tk.Menu(self.root,tearoff=False)
        if self.corrector is None:self.corrector=CorrectorEspanol()
        if objetivo:
            palabra=objetivo[3]
            muestra=palabra if len(palabra)<=38 else palabra[:35]+'…'
            menu.add_command(label=f'Sugerencias para «{muestra}»',state='disabled')
            sugerencias=self.corrector.sugerencias(palabra)
            if sugerencias:
                for alternativa in sugerencias:
                    menu.add_command(label=alternativa,command=lambda a=alternativa,o=objetivo:self.reemplazar(o,a))
            else:
                mensaje='Sin cambios sugeridos' if self.corrector.disponible else 'Diccionario no disponible'
                menu.add_command(label=mensaje,state='disabled')
        else:menu.add_command(label='Haga clic derecho sobre una palabra',state='disabled')
        menu.add_separator()
        def editar(evento):
            widget.focus_set();widget.event_generate(evento)
        menu.add_command(label='Cortar',command=lambda:editar('<<Cut>>'))
        menu.add_command(label='Copiar',command=lambda:editar('<<Copy>>'))
        menu.add_command(label='Pegar',command=lambda:editar('<<Paste>>'))
        menu.add_command(label='Seleccionar todo',command=lambda:self.seleccionar_todo(widget))
        return menu

    def abrir(self, event, teclado=False):
        widget=event.widget
        if str(widget.cget('state')) in ('disabled','readonly'):return 'break'
        grab=self.root.grab_current()
        if grab is not None and grab is not self.menu:return 'break'
        objetivo=self.objetivo(widget,event.x,event.y,teclado)
        widget.focus_set()
        menu=self.preparar(widget,objetivo)
        x=widget.winfo_rootx()+12 if teclado else event.x_root
        y=widget.winfo_rooty()+widget.winfo_height() if teclado else event.y_root
        try:menu.tk_popup(x,y)
        finally:menu.grab_release()
        return 'break'

    def reemplazar(self, objetivo, alternativa):
        widget,inicio,fin,palabra=objetivo
        if not widget.winfo_exists() or str(widget.cget('state')) in ('disabled','readonly'):return
        if isinstance(widget,tk.Text):
            if widget.get(inicio,fin)!=palabra:return
            automaticos=widget.cget('autoseparators')
            widget.edit_separator();widget.configure(autoseparators=False)
            try:widget.delete(inicio,fin);widget.insert(inicio,alternativa)
            finally:widget.edit_separator();widget.configure(autoseparators=automaticos)
            widget.mark_set('insert',f'{inicio}+{len(alternativa)}c')
        else:
            if widget.get()[inicio:fin]!=palabra:return
            # Una sola actualización conserva todo el resto y las trazas del campo.
            valor=widget.get()[:inicio]+alternativa+widget.get()[fin:]
            variable=widget.cget('textvariable')
            if variable:widget.setvar(variable,valor)
            else:widget.delete(inicio,fin);widget.insert(inicio,alternativa)
            widget.icursor(inicio+len(alternativa));widget.selection_clear()
        widget.focus_set()

    @staticmethod
    def seleccionar_todo(widget):
        widget.focus_set()
        if isinstance(widget,tk.Text):widget.tag_add('sel','1.0','end-1c')
        else:widget.selection_range(0,'end')
