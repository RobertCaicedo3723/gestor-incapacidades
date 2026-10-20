"""Aplicación de ventanilla: Python/Tk, sin servicios externos ni dependencias pip."""
import datetime as dt
import calendar
import shutil
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from tkinter import font as tkfont
from edicion_texto import EditorTexto
from motor import ROOT,TIPOS,ESCUELAS,validar,generar,fecha,es_externa,lleva_prorroga,parrafo_clinico,tiene_periodo,modo_periodo,MODOS_PERIODO

def configurar_dpi():
    """Declarar DPI antes de crear ventanas; no cambia la escala de Windows."""
    if os.name!='nt':return
    import ctypes
    try:
        api=ctypes.windll.user32.SetProcessDpiAwarenessContext
        api.argtypes=[ctypes.c_void_p];api.restype=ctypes.c_bool
        api(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2, sin estirar bitmaps.
    except AttributeError:
        try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError,OSError):pass

class Aplicacion(tk.Tk):
    def __init__(self):
        configurar_dpi()
        super().__init__()
        self._paint_job=None
        self._active_nav=None
        self._compact_nav=False
        self._dirty=False
        self._wheel_remainder=0.0
        self._locked_controls=[]
        self.fields={}
        self.help_labels={}
        self.edicion=EditorTexto(self)
        self._scroll_tag=f'UISScroll{id(self)}'
        self.bind_class(self._scroll_tag,'<MouseWheel>',self.wheel)
        self.title('UIS · Preparación de incapacidades')
        self.geometry(f'{min(1280,self.winfo_screenwidth()-80)}x{min(900,self.winfo_screenheight()-100)}');self.minsize(980,640)
        self.configure(bg='white')
        self.results=queue.Queue();self.last=None;self.busy=False
        self.palette={'green':'#67B93E','ink':'#202320','muted':'#626862','line':'#DFE3DE','rail':'#F4F5F3'}
        self.font_family='Open Sans' if 'Open Sans' in tkfont.families(self) else 'Segoe UI'
        self.option_add('*TCombobox*Listbox.font',(self.font_family,11))
        self.option_add('*TCombobox*Listbox.background','white')
        self.option_add('*TCombobox*Listbox.selectBackground','#EAF4E4')
        self.option_add('*TCombobox*Listbox.selectForeground','#202320')
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',font=(self.font_family,11),foreground='#202320',background='white')
        style.configure('TFrame',background='white')
        style.configure('TLabel',background='white',foreground='#202320')
        style.configure('Muted.TLabel',foreground='#626862',font=(self.font_family,10))
        style.configure('TLabelframe',background='white',borderwidth=0,relief='flat',padding=(0,16,0,12))
        style.configure('TLabelframe.Label',background='white',foreground='#202320',font=(self.font_family,15,'bold'))
        style.configure('TEntry',fieldbackground='white',bordercolor='#BFC7BC',lightcolor='white',darkcolor='white',padding=(10,8))
        style.map('TEntry',bordercolor=[('focus','#67B93E')],lightcolor=[('focus','#67B93E')],darkcolor=[('focus','#67B93E')])
        style.configure('TCombobox',fieldbackground='white',background='#F4F5F3',bordercolor='#BFC7BC',lightcolor='white',darkcolor='white',arrowcolor='#444B40',padding=(9,8))
        style.map('TCombobox',fieldbackground=[('readonly','white')],foreground=[('readonly','#202320')],selectbackground=[('readonly','white')],selectforeground=[('readonly','#202320')],bordercolor=[('focus','#67B93E')])
        style.configure('TButton',padding=(16,10),background='white',bordercolor='#C7CDC3',lightcolor='white',darkcolor='white',relief='flat',foreground='#202320')
        style.map('TButton',background=[('active','#F0F3EE')],foreground=[('disabled','#92978D')])
        style.configure('Primary.TButton',background='#67B93E',foreground='#14220B',bordercolor='#67B93E',font=(self.font_family,11,'bold'))
        style.map('Primary.TButton',background=[('disabled','#E4E8E1'),('active','#59A833')],bordercolor=[('disabled','#E4E8E1'),('active','#59A833')],foreground=[('disabled','#8B9285')])
        style.configure('Rail.TFrame',background='#F4F5F3')
        style.configure('Rail.TLabel',background='#F4F5F3',foreground='#626862',font=(self.font_family,10))
        style.configure('Rail.Footer.TLabel',background='#F4F5F3',foreground='#626862',font=(self.font_family,9))
        style.configure('Nav.TButton',background='#F4F5F3',foreground='#555D50',anchor='w',borderwidth=0,padding=(12,10),font=(self.font_family,11))
        style.configure('Active.Nav.TButton',background='#E5EFDF',foreground='#25361C',anchor='w',borderwidth=0,padding=(12,10),font=(self.font_family,11,'bold'))
        style.configure('Compact.Nav.TButton',background='#F4F5F3',foreground='#555D50',anchor='w',borderwidth=0,padding=(12,6),font=(self.font_family,10))
        style.configure('Active.Compact.Nav.TButton',background='#E5EFDF',foreground='#25361C',anchor='w',borderwidth=0,padding=(12,6),font=(self.font_family,10,'bold'))
        style.map('Nav.TButton',background=[('active','#E8EBE5')])
        style.map('Active.Nav.TButton',background=[('active','#DDEAD4')])
        style.configure('TCheckbutton',background='white',indicatorbackground='white',indicatorforeground='#202320',padding=(0,8))
        style.map('TCheckbutton',background=[('active','white')],indicatorbackground=[('selected','#67B93E')])
        style.configure('Vertical.TScrollbar',background='#D5DBD1',troughcolor='#F5F6F3',borderwidth=0,arrowsize=12)
        self.v={k:tk.StringVar() for k in ['tipo','facultad','escuela','fecha','entidad','medico','tratamiento','nombre','codigo','diagnostico','inicio','fin','folios','hasta','medico_prorroga','entidad_prorroga','especialidad','medico_general','registro','accion']}
        self.v['tipo'].set(TIPOS[0]);self.v['tratamiento'].set('al estudiante')
        self.v['fecha'].set(dt.date.today().strftime('%d/%m/%Y'))
        self.v['medico_general'].set('');self.v['registro'].set('')
        self.v['folios'].set('1')
        self.prorroga=tk.BooleanVar(value=False)
        self.folder=tk.StringVar(value=str(ROOT/'generados'))
        head=ttk.Frame(self,padding=(28,14));head.pack(fill='x');head.columnconfigure(2,weight=1)
        self.brand_logo=None
        try:
            self.brand_logo=tk.PhotoImage(file=str(ROOT/'assets/uis-oficial.png'))
            ttk.Label(head,image=self.brand_logo).grid(row=0,column=0,padx=(0,24))
            self.iconphoto(True,self.brand_logo)
        except tk.TclError:
            ttk.Label(head,text='Universidad Industrial\nde Santander',font=(self.font_family,11,'bold')).grid(row=0,column=0,padx=(0,24))
        ttk.Separator(head,orient='vertical').grid(row=0,column=1,sticky='ns',padx=(0,24))
        brand=ttk.Frame(head);brand.grid(row=0,column=2,sticky='ew')
        self.flow_label(brand,'Bienestar Estudiantil',font=(self.font_family,16,'bold')).pack(fill='x')
        self.flow_label(brand,'Servicios integrales de salud y desarrollo psicosocial',style='Muted.TLabel').pack(fill='x',pady=(3,0))
        self.header_kicker=ttk.Label(head,text='ATENCIÓN EN VENTANILLA',style='Muted.TLabel')
        self.header_kicker.grid(row=0,column=3,padx=(24,0))
        head.bind('<Configure>',lambda e:self.header_kicker.grid() if e.width>=1200 else self.header_kicker.grid_remove())
        tk.Frame(self,bg='#67B93E',height=3).pack(fill='x')
        body=ttk.Frame(self);body.pack(fill='both',expand=True)
        nav_width=tkfont.Font(family=self.font_family,size=11,weight='bold').measure('02   Destino y anexos')+80
        rail=ttk.Frame(body,style='Rail.TFrame',padding=(20,16,20,12),width=max(218,nav_width));rail.pack(side='left',fill='y');rail.pack_propagate(False)
        self.rail=rail
        rail.bind('<Configure>',self.resize_rail)
        ttk.Label(rail,text='INCAPACIDADES',style='Rail.TLabel',font=(self.font_family,10,'bold')).pack(anchor='w',padx=12,pady=(0,16))
        self.nav=ttk.Frame(rail,style='Rail.TFrame')
        self.nav_buttons=[]
        self.rail_identity=ttk.Label(rail,text='Universidad Industrial de Santander',style='Rail.Footer.TLabel',wraplength=150,justify='left',anchor='w')
        self.rail_identity.pack(side='bottom',fill='x',padx=12,pady=(10,0))
        self.document_note=ttk.Label(rail,text='',style='Rail.Footer.TLabel',wraplength=150,justify='left',anchor='w');self.document_note.pack(side='bottom',fill='x',padx=12,pady=(0,12))
        for label in (self.rail_identity,self.document_note):
            label.bind('<Configure>',lambda e,w=label:self.wrap_caption(w,e.width-2))
        self.nav.pack(fill='x')
        ttk.Separator(body,orient='vertical').pack(side='left',fill='y')
        self.canvas=tk.Canvas(body,bg='white',highlightthickness=0,borderwidth=0,yscrollincrement=1)
        scroll=ttk.Scrollbar(body,orient='vertical',command=self.canvas.yview)
        self.scrollbar=scroll
        self.canvas.configure(yscrollcommand=self.on_scroll);scroll.pack(side='right',fill='y');self.canvas.pack(side='left',fill='both',expand=True)
        self.form=ttk.Frame(self.canvas,padding=(36,26,36,30));window=self.canvas.create_window((0,0),window=self.form,anchor='nw')
        self.form.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(window,width=e.width))
        intro=ttk.Frame(self.form);intro.pack(fill='x',pady=(0,26))
        self.flow_label(intro,'Preparar certificado',font=(self.font_family,25,'bold')).pack(fill='x')
        self.flow_label(intro,'Complete los datos del soporte y revise el documento antes de imprimir.',style='Muted.TLabel').pack(fill='x',pady=(6,0))
        top=self.group('Estudiante y formato');self.top=top
        self.field(top,'tipo','Formato',0,0,values=TIPOS,width=54,span=2).bind('<<ComboboxSelected>>',self.toggle)
        self.field(top,'nombre','Nombre completo del estudiante',1,0,width=52)
        self.field(top,'codigo','Código estudiantil (7 dígitos)',1,1)
        self.field(top,'tratamiento','Tratamiento',2,0,values=['al estudiante','a la estudiante'])
        self.field(top,'fecha','Fecha de expedición (DD/MM/AAAA)',2,1)
        self.source_label=self.flow_label(top,'',style='Muted.TLabel');self.source_label.grid(row=6,column=0,columnspan=2,sticky='ew',pady=(6,0))
        self.school=self.group('Destino y anexos')
        self.school_entry=self.field(self.school,'escuela','Escuela',0,0,width=85,span=2)
        self.school_note=self.flow_label(self.school,'Escriba el nombre completo o la abreviatura que debe aparecer en el documento.',style='Muted.TLabel')
        self.school_note.grid(row=2,column=0,columnspan=2,sticky='ew',pady=(0,12))
        self.field(self.school,'folios','Cantidad de folios anexos',2,0)
        clinical=self.group('Incapacidad inicial');self.clinical=clinical
        self.action_frame=ttk.Frame(clinical)
        self.action_frame.grid(row=0,column=0,columnspan=2,sticky='ew');self.action_frame.columnconfigure(0,weight=1)
        self.action_combo=self.field(self.action_frame,'accion','¿Qué atención recibió? · elija o escriba la frase antes de la entidad',0,0,values=['fue valorado en','fue valorada en','fue hospitalizado en','fue hospitalizada en','fue programado en','fue programada en','fue atendido en','fue atendida en'],width=70)
        self.action_combo.configure(state='normal')
        self.field(clinical,'entidad','Institución de atención',1,0,width=42)
        self.field(clinical,'medico','Médico emisor (Dr. o Dra.)',1,1,width=38)
        self.field(clinical,'inicio','Fecha de inicio (DD/MM/AAAA)',2,0)
        self.field(clinical,'fin','Fecha de finalización (DD/MM/AAAA)',2,1)
        ttk.Button(clinical,text='Calcular fin a 30 días',command=self.calculate).grid(row=6,column=0,sticky='w',pady=6)
        self.days_label=self.flow_label(clinical,'',style='Muted.TLabel');self.days_label.grid(row=6,column=1,sticky='ew')
        self.detail_label=ttk.Label(clinical,text='',wraplength=820,style='Muted.TLabel');self.detail_label.grid(row=7,column=0,columnspan=2,sticky='ew',pady=(14,8))
        self.detail_label.bind('<Configure>',lambda e:self.wrap_caption(self.detail_label,e.width))
        self.detail=tk.Text(clinical,height=4,wrap='word',font=(self.font_family,11),relief='flat',borderwidth=0,highlightthickness=1,highlightbackground='#BFC7BC',highlightcolor='#67B93E',padx=12,pady=10,insertbackground='#202320',selectbackground='#DDEED2',selectforeground='#202320',undo=True)
        self.detail.grid(row=8,column=0,columnspan=2,sticky='ew')
        self.edicion.instalar(self.detail)
        self.cert=self.group('Datos del certificado')
        self.field(self.cert,'especialidad','Especialidad del médico emisor',0,0,width=52)
        self.field(self.cert,'medico_general','Médico general que figura en el certificado',1,0,width=52)
        self.field(self.cert,'registro','Registro médico',1,1)
        self.v['modo_periodo']=tk.StringVar(value=MODOS_PERIODO[0])
        self.v['inicio_adicional']=tk.StringVar()
        self.extcheck=ttk.Frame(self.form);self.extcheck.columnconfigure(0,weight=1)
        self.field(self.extcheck,'modo_periodo','Periodo adicional · disponible para todos los formatos',0,0,values=MODOS_PERIODO,span=2).bind('<<ComboboxSelected>>',self.toggle)
        self.extension=self.group('Periodo adicional')
        self.field(self.extension,'inicio_adicional','Inicio adicional · DD/MM/AAAA',0,0)
        self.field(self.extension,'hasta','Fin adicional · DD/MM/AAAA',0,1)
        self.field(self.extension,'medico_prorroga','Médico del periodo adicional · Dr. o Dra.',1,0,width=45)
        self.field(self.extension,'entidad_prorroga','Institución del periodo adicional · opcional',1,1,width=52)
        self.flow_label(self.extension,'Puede ser un médico distinto. Si deja el inicio vacío, se usará el día siguiente al fin inicial. La opción independiente se imprime sin la palabra prórroga.',style='Muted.TLabel').grid(row=4,column=0,columnspan=2,sticky='ew')
        self.dest=self.group('Guardar documentos')
        ttk.Entry(self.dest,textvariable=self.folder).grid(row=0,column=0,sticky='ew')
        ttk.Button(self.dest,text='Elegir carpeta',command=self.choose_folder).grid(row=0,column=1,padx=(10,0))
        self.flow_label(self.dest,'PDF para impresión y copia Word editable. Los archivos se guardan en este equipo. Para ver sugerencias de escritura, haga clic derecho sobre una palabra del formulario.',style='Muted.TLabel').grid(row=1,column=0,columnspan=2,sticky='ew',pady=(10,0))
        ttk.Separator(self).pack(fill='x')
        footer=ttk.Frame(self,padding=(28,12,28,16));footer.pack(fill='x')
        self.status=self.flow_label(footer,'Listo para un nuevo caso.',style='Muted.TLabel');self.status.pack(fill='x',pady=(0,10))
        actions=ttk.Frame(footer);actions.pack(fill='x');actions.columnconfigure(1,weight=1)
        self.new_button=ttk.Button(actions,text='Nuevo estudiante',command=self.clear);self.new_button.grid(row=0,column=0,sticky='w')
        self.generate_button=ttk.Button(actions,text='Revisar y generar PDF',style='Primary.TButton',command=self.review);self.generate_button.grid(row=0,column=2,sticky='e')
        self.pdf_button=ttk.Button(actions,text='Abrir PDF / imprimir',command=self.open_pdf,state='disabled');self.pdf_button.grid(row=1,column=0,sticky='w',pady=(8,0))
        self.save_button=ttk.Button(actions,text='Guardar PDF como…',command=self.save_pdf,state='disabled');self.save_button.grid(row=1,column=2,sticky='e',pady=(8,0))
        self.v['inicio'].trace_add('write',self.update_days);self.v['fin'].trace_add('write',self.update_days)
        for variable in self.v.values():variable.trace_add('write',self.case_changed)
        self.detail.bind('<<Modified>>',self.detail_changed)
        self.toggle();self.after(150,self.poll)
        self.install_wheel(self)
        self._dirty=False
        self.protocol('WM_DELETE_WINDOW',self.close)

    def flow_label(self,parent,text,**kwargs):
        label=ttk.Label(parent,text=text,wraplength=360,anchor='w',justify='left',**kwargs)
        label.bind('<Configure>',lambda e,w=label:self.wrap_caption(w,e.width-2))
        return label

    def resize_rail(self,event):
        compact=event.height<500
        if compact!=self._compact_nav:
            self._compact_nav=compact;self._active_nav=None
            # La identidad ya figura en la cabecera; en ventanas bajas se
            # reserva el lateral para que todos los pasos sigan accesibles.
            if compact:
                self.document_note.pack_forget();self.rail_identity.pack_forget()
            else:
                self.rail_identity.pack(side='bottom',fill='x',padx=12,pady=(10,0))
                self.document_note.pack(side='bottom',fill='x',padx=12,pady=(0,12))
            if hasattr(self,'canvas'):self.highlight_nav()

    def install_wheel(self,widget):
        # Precede al binding de clase TCombobox: bind_all ocurre demasiado tarde.
        tags=widget.bindtags()
        if self._scroll_tag not in tags:widget.bindtags((self._scroll_tag,)+tags)
        for child in widget.winfo_children():self.install_wheel(child)

    def case_changed(self,*args):
        self._dirty=True
        if self.last is not None and not self.busy:
            self.last=None;self.pdf_button.configure(state='disabled');self.save_button.configure(state='disabled')
            self.status.configure(text='Hay cambios en el caso. Revise y genere un nuevo documento antes de imprimir.')

    def detail_changed(self,event=None):
        if self.detail.edit_modified():
            self.detail.edit_modified(False);self.case_changed()

    def lock_form(self,locked):
        if locked:
            self._locked_controls=[]
            def freeze(widget):
                if isinstance(widget,(ttk.Entry,ttk.Combobox,ttk.Button,ttk.Checkbutton,tk.Text)):
                    self._locked_controls.append((widget,str(widget.cget('state'))))
                    widget.configure(state='disabled')
                for child in widget.winfo_children():freeze(child)
            freeze(self.form)
            self.new_button.configure(state='disabled')
        else:
            for widget,state in self._locked_controls:
                if widget.winfo_exists():widget.configure(state=state)
            self._locked_controls=[];self.new_button.configure(state='normal')

    def group(self,title):
        frame=ttk.LabelFrame(self.form,text=title);frame.pack(fill='x',pady=(0,24))
        frame.columnconfigure(0,weight=1,uniform='fields');frame.columnconfigure(1,weight=1,uniform='fields')
        return frame

    def rebuild_nav(self):
        self._active_nav=None
        for child in self.nav.winfo_children():child.destroy()
        sections=[('Estudiante',self.top)]
        if es_externa(self.data()):sections.append(('Destino y anexos',self.school))
        sections.append(('Incapacidad',self.clinical))
        if not es_externa(self.data()):sections.append(('Datos médicos',self.cert))
        if tiene_periodo(self.data()):sections.append(('Periodo adicional',self.extension))
        sections.append(('Guardar',self.dest))
        self.nav_buttons=[]
        for i,(label,frame) in enumerate(sections,1):
            button=ttk.Button(self.nav,text=f'{i:02}   {label}',style='Nav.TButton',command=lambda f=frame:self.goto_section(f))
            button.pack(fill='x',pady=2);self.nav_buttons.append((frame,button))
            self.install_wheel(button)
        self.document_note.configure(text=('Remisión externa' if es_externa(self.data()) else 'Certificado médico')+'\n'+modo_periodo(self.data()))
        self.after_idle(self.highlight_nav)

    def goto_section(self,frame):
        self.update_idletasks()
        height=max(self.form.winfo_height(),1)
        self.canvas.yview_moveto(max(0,frame.winfo_y()-20)/height)

    def on_scroll(self,first,last):
        self.scrollbar.set(first,last)
        self.highlight_nav()
        # Canvas mueve una ventana con controles ttk: Windows puede conservar
        # píxeles de la zona antes recortada. Invalidar el viewport y sus hijos
        # después del movimiento, una sola vez por lote de eventos.
        if self._paint_job is None:
            self._paint_job=self.after_idle(self.repaint_viewport)

    def repaint_viewport(self):
        self._paint_job=None
        if not self.canvas.winfo_exists() or not self.canvas.winfo_ismapped():return
        if os.name=='nt':
            import ctypes
            redraw=ctypes.windll.user32.RedrawWindow
            redraw.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint]
            redraw.restype=ctypes.c_bool
            # INVALIDATE | ERASE | ALLCHILDREN | UPDATENOW.
            redraw(ctypes.c_void_p(self.canvas.winfo_id()),None,None,0x0185)
        else:
            self.form.event_generate('<Expose>')

    def highlight_nav(self):
        if not self.nav_buttons:return
        y=self.canvas.canvasy(0)+70
        active=self.nav_buttons[0][0]
        for frame,_ in self.nav_buttons:
            if frame.winfo_y()<=y:active=frame
        if self.canvas.yview()[1]>=.999:active=self.nav_buttons[-1][0]
        if active is self._active_nav:return
        self._active_nav=active
        for frame,button in self.nav_buttons:
            base='Compact.Nav.TButton' if self._compact_nav else 'Nav.TButton'
            button.configure(style=('Active.'+base) if frame is active else base)

    def field(self,parent,key,label,row,col,values=None,width=30,span=1):
        examples={
            'escuela':'Ej.: Escuela de Biología o Esc. de Ing. de Sistemas.',
            'entidad':'Ej.: el Hospital Universitario de Santander (incluya el artículo si corresponde).',
            'medico':'Ej.: Dra. Ana Pérez o Dr. Juan Gómez. Incluya el título.',
            'medico_general':'Ej.: Dr. Juan Gómez. Incluya el título.',
            'medico_prorroga':'Ej.: Dra. Ana Pérez. Puede ser un médico distinto.',
            'entidad_prorroga':'Ej.: Clínica de Especialistas. Puede dejarlo vacío.',
            'especialidad':'Ej.: Ortopedia y Traumatología. Escriba solo la especialidad.',
            'accion':'Ej.: fue valorada en. Escriba la frase anterior a la institución.',
            'inicio_adicional':'Ej.: 16/10/2026. Vacío = día siguiente al fin inicial.',
        }
        heading=ttk.Frame(parent);heading.columnconfigure(0,weight=1)
        heading.grid(row=row*2,column=col,columnspan=span,sticky='ew',pady=(3,7),padx=(0,16))
        caption=ttk.Label(heading,text=label,font=(self.font_family,10),wraplength=780 if span==2 else 395)
        caption.grid(row=0,column=0,sticky='ew')
        caption.bind('<Configure>',lambda e,c=caption:self.wrap_caption(c,e.width))
        if key in examples:
            hint=self.flow_label(heading,examples[key],style='Muted.TLabel')
            hint.bind('<Configure>',lambda e,w=hint:self.wrap_caption(w,e.width-12))
            hint.grid(row=1,column=0,sticky='ew',pady=(3,0));self.help_labels[key]=hint
        date_field=key in ('fecha','inicio','fin','inicio_adicional','hasta')
        host=ttk.Frame(parent) if date_field else parent
        if values is None: widget=ttk.Entry(host,textvariable=self.v[key],width=width)
        else: widget=ttk.Combobox(parent,textvariable=self.v[key],values=values,width=width,state='readonly')
        if date_field:
            host.grid(row=row*2+1,column=col,columnspan=span,sticky='ew',pady=(0,16),padx=(0,16));host.columnconfigure(0,weight=1)
            widget.grid(row=0,column=0,sticky='ew')
            ttk.Button(host,text='Calendario',command=lambda:self.select_date(key)).grid(row=0,column=1,padx=(5,0))
        else:widget.grid(row=row*2+1,column=col,columnspan=span,sticky='ew',pady=(0,16),padx=(0,16))
        widget.bind('<FocusIn>',lambda e,w=widget:self.ensure_visible(w))
        self.fields[key]=widget
        if key not in ('tipo','tratamiento','modo_periodo','fecha','inicio','fin','inicio_adicional','hasta','codigo','folios','registro'):
            self.edicion.instalar(widget)
        return widget

    def select_date(self,key):
        try:selected=fecha(self.v[key].get())
        except ValueError:
            try:selected=fecha(self.v['fin'].get())+dt.timedelta(days=1) if key=='inicio_adicional' else dt.date.today()
            except ValueError:selected=dt.date.today()
        dialog=tk.Toplevel(self);dialog.title('Seleccionar fecha');dialog.transient(self);dialog.resizable(False,False);dialog.grab_set()
        area=ttk.Frame(dialog,padding=16);area.pack(fill='both',expand=True)
        year=tk.StringVar(value=str(selected.year));month=tk.StringVar(value=str(selected.month))
        nav=ttk.Frame(area);nav.pack(fill='x')
        days=ttk.Frame(area);days.pack(pady=12)
        def choose(day):
            self.v[key].set(dt.date(int(year.get()),int(month.get()),day).strftime('%d/%m/%Y'));dialog.destroy()
        def draw(*args):
            for child in days.winfo_children():child.destroy()
            try:y=int(year.get());m=int(month.get());weeks=calendar.monthcalendar(y,m)
            except (ValueError,OverflowError):return
            for c,name in enumerate(('Lu','Ma','Mi','Ju','Vi','Sá','Do')):ttk.Label(days,text=name,anchor='center').grid(row=0,column=c,pady=4)
            for r,week in enumerate(weeks,1):
                for c,day in enumerate(week):
                    if day:ttk.Button(days,text=str(day),width=4,command=lambda d=day:choose(d)).grid(row=r,column=c,padx=2,pady=2)
        def shift(step):
            total=int(year.get())*12+int(month.get())-1+step
            y,m=divmod(total,12)
            if 1<=y<=9999:year.set(str(y));month.set(str(m+1));draw()
        ttk.Button(nav,text='‹',width=3,command=lambda:shift(-1)).pack(side='left')
        months=ttk.Combobox(nav,values=tuple(range(1,13)),textvariable=month,width=4,state='readonly');months.pack(side='left',padx=8);months.bind('<<ComboboxSelected>>',draw)
        years=ttk.Spinbox(nav,from_=1900,to=2200,textvariable=year,width=7,command=draw);years.pack(side='left');years.bind('<Return>',draw);years.bind('<FocusOut>',draw)
        ttk.Button(nav,text='›',width=3,command=lambda:shift(1)).pack(side='left',padx=8)
        def today():
            self.v[key].set(dt.date.today().strftime('%d/%m/%Y'));dialog.destroy()
        ttk.Button(area,text='Hoy',command=today).pack(side='left')
        ttk.Button(area,text='Cancelar',command=dialog.destroy).pack(side='right')
        dialog.bind('<Escape>',lambda e:dialog.destroy());draw()
        return dialog

    @staticmethod
    def wrap_caption(caption,width):
        width=max(100,width)
        if int(caption.cget('wraplength'))!=width:caption.configure(wraplength=width)

    def ensure_visible(self,widget):
        self.update_idletasks()
        top=widget.winfo_rooty()-self.form.winfo_rooty()
        visible=self.canvas.canvasy(0);height=self.canvas.winfo_height()
        if top<visible+25:self.canvas.yview_moveto(max(0,top-55)/max(1,self.form.winfo_height()))
        elif top+widget.winfo_height()>visible+height-15:
            self.canvas.yview_moveto(max(0,top+widget.winfo_height()-height+45)/max(1,self.form.winfo_height()))

    def wheel(self,event):
        if event.widget.winfo_toplevel() is not self:return
        # Un cuadro de revisión modal debe desplazar su propio texto, no el caso.
        grab=self.grab_current()
        if grab is not None and grab.winfo_toplevel() is not self:return 'break'
        self._wheel_remainder-=event.delta*.4
        pixels=int(self._wheel_remainder);self._wheel_remainder-=pixels
        if pixels:
            if event.widget is self.detail and self.focus_get() is self.detail:
                first,last=self.detail.yview()
                if (pixels>0 and last<.999) or (pixels<0 and first>0):
                    self.detail.yview_scroll(1 if pixels>0 else -1,'units');return 'break'
            self.canvas.yview_scroll(pixels,'units')
        return 'break'

    def data(self):
        data={k:v.get() for k,v in self.v.items()}
        data['diagnostico']=' '.join(self.detail.get('1.0','end').split())
        data['prorroga']=self.prorroga.get()
        return data

    def toggle(self,event=None):
        if event is not None and event.widget is self.fields['tipo']:
            self.v['modo_periodo'].set(MODOS_PERIODO[1] if self.v['tipo'].get()==TIPOS[1] else MODOS_PERIODO[0])
        data=self.data();external=es_externa(data)
        for frame in (self.school,self.cert,self.extension,self.extcheck,self.dest): frame.pack_forget()
        if external:
            # Destino antes de la sección clínica.
            self.school.pack(fill='x',pady=(0,24),after=self.top)
        else: self.cert.pack(fill='x',pady=(0,24))
        self.extcheck.pack(fill='x',pady=(0,12),after=self.top)
        if tiene_periodo(data): self.extension.pack(fill='x',pady=(0,24))
        self.dest.pack(fill='x',pady=(0,24))
        self.source_label.configure(text='Remisión dirigida a la escuela, con relación de anexos.' if external else 'Certificado basado en el modelo institucional de 30 días.')
        self.help_labels['entidad'].configure(text='Ej.: Hospital Universitario de Santander.' if external else 'Ej.: el Hospital Universitario de Santander (incluya el artículo si corresponde).')
        if external:self.action_frame.grid_remove()
        else:self.action_frame.grid()
        self.detail_label.configure(text='Diagnóstico (transcriba el soporte)' if external else '¿Por qué / para qué? · continuación después de la entidad. Ej.: «, como consecuencia de un accidente…» o «para la realización de un procedimiento…». Incluya la coma cuando corresponda.')
        self.update_days()
        self.rebuild_nav()

    def update_days(self,*args):
        try:
            days=(fecha(self.v['fin'].get())-fecha(self.v['inicio'].get())).days+1
            self.days_label.configure(text=f'Duración inicial: {days} días (ambas fechas incluidas).')
        except ValueError: self.days_label.configure(text='Ambas fechas se incluyen en la duración.')

    def calculate(self):
        try: self.v['fin'].set((fecha(self.v['inicio'].get())+dt.timedelta(days=29)).strftime('%d/%m/%Y'))
        except ValueError as e:self.show_error('Revise la fecha de inicio',str(e))

    def show_error(self,title,message):
        # Texto seleccionable y desplazable: ni errores largos ni rutas quedan cortados.
        dialog=tk.Toplevel(self);dialog.title('UIS · '+title);dialog.configure(bg='white')
        dialog.geometry('720x440');dialog.minsize(540,340);dialog.transient(self);dialog.grab_set()
        heading=ttk.Frame(dialog,padding=(24,20,24,12));heading.pack(fill='x')
        self.flow_label(heading,title,font=(self.font_family,17,'bold')).pack(fill='x')
        area=ttk.Frame(dialog,padding=(24,0,24,0));area.pack(fill='both',expand=True)
        content=tk.Text(area,wrap='word',font=(self.font_family,11),borderwidth=0,highlightthickness=0,padx=4,pady=12)
        scroll=ttk.Scrollbar(area,command=content.yview);scroll.pack(side='right',fill='y')
        content.configure(yscrollcommand=scroll.set);content.pack(fill='both',expand=True)
        content.insert('1.0',str(message));content.configure(state='disabled')
        actions=ttk.Frame(dialog,padding=(24,16));actions.pack(fill='x')
        ttk.Button(actions,text='Volver al formulario',command=dialog.destroy).pack(side='right')
        dialog.bind('<Escape>',lambda e:dialog.destroy())
        return dialog

    def choose_folder(self):
        selected=filedialog.askdirectory(parent=self,title='Carpeta para documentos generados')
        if selected:self.folder.set(selected)

    def review(self):
        if self.busy:return
        data=self.data()
        try:
            values=validar(data)
            if not self.folder.get().strip():raise ValueError('Seleccione una carpeta para guardar los documentos.')
        except ValueError as e:self.show_error('Revise los datos',str(e));return
        dialog=tk.Toplevel(self);dialog.title('UIS · Revisión del certificado')
        review_height=min(700,self.winfo_screenheight()-100)
        dialog.geometry(f'820x{review_height}+40+30');dialog.minsize(640,min(480,review_height));dialog.configure(bg='white');dialog.transient(self);dialog.grab_set()
        # Reservar primero el pie: el texto consume solo el espacio restante.
        buttons=ttk.Frame(dialog,padding=(24,16));buttons.pack(side='bottom',fill='x')
        ttk.Button(buttons,text='Volver y corregir',command=dialog.destroy).pack(side='left')
        self.accept_button=ttk.Button(buttons,text='Aceptar y guardar PDF y Word',style='Primary.TButton',command=lambda:self.start(data,dialog));self.accept_button.pack(side='right')
        ttk.Separator(dialog).pack(side='bottom',fill='x')
        heading=ttk.Frame(dialog,padding=(28,24,28,18));heading.pack(fill='x')
        self.flow_label(heading,'Revise el certificado',font=(self.font_family,21,'bold')).pack(fill='x')
        self.flow_label(heading,'Confirme los datos antes de generar los documentos para impresión.',style='Muted.TLabel').pack(fill='x',pady=(6,0))
        ttk.Separator(dialog).pack(fill='x')
        review_body=ttk.Frame(dialog);review_body.pack(fill='both',expand=True)
        box=tk.Text(review_body,wrap='word',font=(self.font_family,11),padx=28,pady=22,borderwidth=0,highlightthickness=0,spacing3=5,selectbackground='#DDEED2',selectforeground='#202320')
        review_scroll=ttk.Scrollbar(review_body,command=box.yview);review_scroll.pack(side='right',fill='y');box.configure(yscrollcommand=review_scroll.set);box.pack(fill='both',expand=True)
        box.tag_configure('heading',font=(self.font_family,12,'bold'),spacing1=10,spacing3=10)
        labels={'nombre':'Estudiante','codigo':'Código','escuela':'Destino','fecha':'Fecha','entidad':'Entidad','medico':'Médico emisor','diagnostico':'Diagnóstico','detalle':'Detalle clínico','inicio':'Inicio','fin':'Fin inicial','extension':'Prórroga','hasta':'Fin de prórroga','medico_prorroga':'Médico de prórroga','entidad_prorroga':'Entidad de prórroga','folios':'Anexos','dias':'Días iniciales','especialidad':'Especialidad','medico_general':'Médico general','registro':'Registro','expedicion':'Expedición'}
        box.insert('end',data['tipo']+'\n\n','heading')
        box.insert('end','Periodo adicional: '+modo_periodo(data)+'\n\n')
        if values.get('periodo_adicional'):box.insert('end',values['periodo_adicional']+'\n\n')
        if not es_externa(data):
            box.insert('end','Párrafo clínico que se imprimirá\n','heading');box.insert('end',parrafo_clinico(values)+'\n\n')
        for k,label in labels.items():
            if k in values and values[k]:box.insert('end',label+': '+values[k]+'\n\n')
        box.configure(state='disabled')
        return dialog

    def start(self,data,dialog):
        dialog.destroy();self.busy=True;self.generate_button.configure(state='disabled',text='Generando documentos…');self.pdf_button.configure(state='disabled');self.save_button.configure(state='disabled')
        self.lock_form(True)
        self.status.configure(text='Preparando PDF en Word y verificando que ocupe una página…')
        folder=self.folder.get()
        def worker():
            try:self.results.put(('ok',generar(data,folder)))
            except Exception as e:self.results.put(('error',str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            status,result=self.results.get_nowait();self.busy=False;self.lock_form(False);self.generate_button.configure(state='normal',text='Revisar y generar PDF')
            if status=='ok':
                self.last=result;self._dirty=False;self.pdf_button.configure(state='normal');self.save_button.configure(state='normal')
                self.status.configure(text='PDF y Word guardados. Abra el PDF para revisar e imprimir a tamaño real (100%).')
                self.open_pdf()
            else:
                self.status.configure(text='No se publicó el documento. Revise el mensaje e inténtelo de nuevo.')
                self.show_error('No se pudo generar el documento',result)
        except queue.Empty:pass
        self.after(150,self.poll)

    def open_pdf(self):
        if self.last:
            try:os.startfile(self.last[1])
            except OSError:messagebox.showinfo('PDF guardado',str(self.last[1]),parent=self)

    def save_pdf(self):
        if not self.last or self.busy:return
        path=filedialog.asksaveasfilename(parent=self,title='Guardar copia del PDF',defaultextension='.pdf',filetypes=[('Documento PDF','*.pdf')],initialfile=self.last[1].name)
        if path:
            try:
                if Path(path).resolve()!=self.last[1].resolve():shutil.copy2(self.last[1],path)
                self.status.configure(text='PDF guardado en: '+path)
            except OSError as e:self.show_error('No se pudo guardar la copia',str(e))

    def clear(self,confirm=True):
        if self.busy:return
        if confirm and self._dirty and (any(self.v[k].get() for k in ('nombre','codigo','entidad','inicio','fin','escuela')) or self.detail.get('1.0','end').strip()):
            if not messagebox.askyesno('Nuevo estudiante','Hay datos sin generar. ¿Desea descartarlos y comenzar otro caso?',parent=self):return
        for key in ['nombre','codigo','entidad','medico','inicio','fin','hasta','medico_prorroga','entidad_prorroga','especialidad','facultad','escuela','accion']:self.v[key].set('')
        self.prorroga.set(False);self.v['tratamiento'].set('al estudiante')
        self.v['modo_periodo'].set(MODOS_PERIODO[0]);self.v['inicio_adicional'].set('')
        self.v['fecha'].set(dt.date.today().strftime('%d/%m/%Y'));self.toggle()
        self.detail.delete('1.0','end');self.detail.edit_reset();self.detail.edit_modified(False)
        self.v['folios'].set('1');self.last=None;self._dirty=False
        self._wheel_remainder=0.0
        self.pdf_button.configure(state='disabled');self.save_button.configure(state='disabled');self.status.configure(text='Nuevo caso: campos del estudiante vacíos.');self.canvas.yview_moveto(0)

    def close(self):
        if self.busy:messagebox.showinfo('Generación en curso','Espere a que termine la generación antes de cerrar.',parent=self);return
        if self._paint_job is not None:self.after_cancel(self._paint_job)
        self.destroy()

if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--autoprueba':
        from self_check import run
        sys.exit(run(Path(sys.argv[2])))
    Aplicacion().mainloop()
