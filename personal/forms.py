"""
Formularios para el módulo personal.
"""
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from .models import Area, SubArea, Personal, Roster


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['nombre', 'codigo', 'jefe_area', 'responsables', 'descripcion', 'activa']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'responsables': FilteredSelectMultiple(
                verbose_name='Responsables adicionales',
                is_stacked=False
            ),
            'codigo': forms.TextInput(attrs={
                'placeholder': 'Ej: ADM, OPS-01, GG',
                'style': 'text-transform:uppercase',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        personal_qs = Personal.objects.filter(estado='Activo').order_by('apellidos_nombres')
        # Jefe de área — solo 1 persona activa
        self.fields['jefe_area'].queryset = personal_qs
        self.fields['jefe_area'].empty_label = '— Sin jefe asignado —'
        self.fields['jefe_area'].help_text = 'Jefe inmediato del área (aparece en reportes SUNAT)'
        # Responsables — múltiples
        self.fields['responsables'].queryset = personal_qs
        self.fields['responsables'].help_text = 'Personas con acceso de gestión al área (opcional)'

        # No usar Layout de crispy (incompatible Python 3.14 + context.__copy__)
        # El template area_form.html renderiza los campos manualmente


class SubAreaForm(forms.ModelForm):
    class Meta:
        model = SubArea
        fields = ['nombre', 'area', 'descripcion', 'activa']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar', css_class='btn btn-primary'))


class PersonalForm(forms.ModelForm):
    class Meta:
        model = Personal
        fields = [
            'tipo_doc', 'nro_doc', 'apellidos_nombres', 'codigo_fotocheck',
            'cargo', 'tipo_trab', 'categoria', 'subarea',
            'fecha_alta', 'fecha_cese', 'motivo_cese', 'estado',
            'regimen_pension', 'afp', 'cuspp', 'asignacion_familiar',
            'fecha_nacimiento', 'sexo', 'celular', 'correo_personal', 'correo_corporativo',
            'direccion', 'ubigeo',
            'sueldo_base', 'banco', 'cuenta_ahorros', 'cuenta_cci', 'cuenta_cts',
            'cond_trabajo_mensual', 'alimentacion_mensual', 'viaticos_mensual',
            'tiene_eps', 'eps_descuento_mensual',
            'grupo_tareo', 'condicion', 'regimen_laboral', 'regimen_turno',
            'codigo_sap', 'codigo_s10', 'partida_control', 'jornada_horas',
            'dias_libres_corte_2025', 'observaciones',
            # Contrato
            'tipo_contrato', 'fecha_inicio_contrato', 'fecha_fin_contrato',
            'renovacion_automatica', 'observaciones_contrato',
        ]
        widgets = {
            'fecha_alta': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_cese': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio_contrato': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin_contrato': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
            'observaciones_contrato': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que las fechas se muestren en el formato correcto
        if self.instance and self.instance.pk:
            if self.instance.fecha_alta:
                self.initial['fecha_alta'] = self.instance.fecha_alta.strftime('%Y-%m-%d')
            if self.instance.fecha_cese:
                self.initial['fecha_cese'] = self.instance.fecha_cese.strftime('%Y-%m-%d')
            if self.instance.fecha_nacimiento:
                self.initial['fecha_nacimiento'] = self.instance.fecha_nacimiento.strftime('%Y-%m-%d')
            if self.instance.fecha_inicio_contrato:
                self.initial['fecha_inicio_contrato'] = self.instance.fecha_inicio_contrato.strftime('%Y-%m-%d')
            if self.instance.fecha_fin_contrato:
                self.initial['fecha_fin_contrato'] = self.instance.fecha_fin_contrato.strftime('%Y-%m-%d')
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            # --- Identificación ---
            Div(
                Row(
                    Column('tipo_doc', css_class='col-md-3'),
                    Column('nro_doc', css_class='col-md-3'),
                    Column('codigo_fotocheck', css_class='col-md-3'),
                    Column('sexo', css_class='col-md-3'),
                ),
                Row(
                    Column('apellidos_nombres', css_class='col-md-8'),
                    Column('fecha_nacimiento', css_class='col-md-4'),
                ),
                css_class='card mb-3 p-3'
            ),
            # --- Datos Laborales ---
            Div(
                Row(
                    Column('cargo', css_class='col-md-4'),
                    Column('tipo_trab', css_class='col-md-4'),
                    Column('categoria', css_class='col-md-4'),
                ),
                Row(
                    Column('subarea', css_class='col-md-4'),
                    Column('estado', css_class='col-md-4'),
                    Column('asignacion_familiar', css_class='col-md-4 pt-4'),
                ),
                Row(
                    Column('fecha_alta', css_class='col-md-4'),
                    Column('fecha_cese', css_class='col-md-4'),
                    Column('sueldo_base', css_class='col-md-4'),
                ),
                Row(
                    Column('motivo_cese', css_class='col-md-6 motivo-cese-row'),
                ),
                css_class='card mb-3 p-3'
            ),
            # --- Pensión y Banca ---
            Div(
                Row(
                    Column('regimen_pension', css_class='col-md-3'),
                    Column('afp', css_class='col-md-3'),
                    Column('cuspp', css_class='col-md-3'),
                    Column('banco', css_class='col-md-3'),
                ),
                Row(
                    Column('cuenta_ahorros', css_class='col-md-4'),
                    Column('cuenta_cci', css_class='col-md-4'),
                    Column('cuenta_cts', css_class='col-md-4'),
                ),
                css_class='card mb-3 p-3'
            ),
            # --- Beneficios No Remunerativos ---
            Div(
                Row(
                    Column('cond_trabajo_mensual', css_class='col-md-4'),
                    Column('alimentacion_mensual', css_class='col-md-4'),
                    Column('viaticos_mensual', css_class='col-md-4'),
                ),
                Row(
                    Column('tiene_eps', css_class='col-md-4 pt-4'),
                    Column('eps_descuento_mensual', css_class='col-md-4'),
                ),
                css_class='card mb-3 p-3'
            ),
            # --- Tareo / Régimen ---
            Div(
                Row(
                    Column('grupo_tareo', css_class='col-md-3'),
                    Column('condicion', css_class='col-md-3'),
                    Column('regimen_laboral', css_class='col-md-3'),
                    Column('regimen_turno', css_class='col-md-3'),
                ),
                Row(
                    Column('jornada_horas', css_class='col-md-3'),
                    Column('codigo_sap', css_class='col-md-3'),
                    Column('codigo_s10', css_class='col-md-3'),
                    Column('partida_control', css_class='col-md-3'),
                ),
                Row(
                    Column('dias_libres_corte_2025', css_class='col-md-4'),
                ),
                css_class='card mb-3 p-3'
            ),
            # --- Contrato Laboral ---
            Div(
                Row(
                    Column('tipo_contrato', css_class='col-md-4'),
                    Column('fecha_inicio_contrato', css_class='col-md-3'),
                    Column('fecha_fin_contrato', css_class='col-md-3'),
                    Column('renovacion_automatica', css_class='col-md-2 pt-4'),
                ),
                Row(
                    Column('observaciones_contrato', css_class='col-md-12'),
                ),
                css_class='card mb-3 p-3'
            ),
            # --- Contacto ---
            Div(
                Row(
                    Column('celular', css_class='col-md-4'),
                    Column('correo_personal', css_class='col-md-4'),
                    Column('correo_corporativo', css_class='col-md-4'),
                ),
                Row(
                    Column('direccion', css_class='col-md-8'),
                    Column('ubigeo', css_class='col-md-4'),
                ),
                Row(
                    Column('observaciones', css_class='col-md-12'),
                ),
                css_class='card mb-3 p-3'
            ),
            Submit('submit', 'Guardar', css_class='btn btn-primary')
        )


class RosterForm(forms.ModelForm):
    class Meta:
        model = Roster
        fields = ['personal', 'fecha', 'codigo', 'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar', css_class='btn btn-primary'))


class ImportExcelForm(forms.Form):
    """Formulario para importación de archivos Excel."""
    archivo = forms.FileField(
        label='Archivo Excel',
        help_text='Selecciona un archivo .xlsx o .xls',
        widget=forms.FileInput(attrs={'accept': '.xlsx,.xls'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.add_input(Submit('submit', 'Importar', css_class='btn btn-primary'))
