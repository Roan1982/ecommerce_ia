from django import forms
from .models import Producto, Cupon


class ProductoAdminForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'peso': forms.NumberInput(attrs={'step': '0.01'}),
            'dimensiones': forms.TextInput(attrs={'placeholder': 'Ej: 10x20x5 cm'}),
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'precio', 'categoria', 'stock', 'stock_minimo',
                 'sku', 'imagen_url', 'estado', 'peso', 'dimensiones']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Descripción detallada del producto'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'categoria': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Categoría del producto'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código SKU único'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
            'peso': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'dimensiones': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 10x20x5 cm'
            }),
        }


class CuponForm(forms.ModelForm):
    class Meta:
        model = Cupon
        fields = ['codigo', 'descripcion', 'tipo_descuento', 'valor_descuento',
                 'fecha_expiracion', 'usos_maximos', 'activo']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código único del cupón (ej: DESCUENTO20)',
                'style': 'text-transform: uppercase;'
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Descripción del cupón y sus condiciones'
            }),
            'tipo_descuento': forms.Select(attrs={
                'class': 'form-select'
            }),
            'valor_descuento': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'fecha_expiracion': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'usos_maximos': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').upper()
        if Cupon.objects.filter(codigo=codigo).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError('Ya existe un cupón con este código.')
        return codigo

    def clean(self):
        cleaned_data = super().clean()
        tipo_descuento = cleaned_data.get('tipo_descuento')
        valor_descuento = cleaned_data.get('valor_descuento')

        if tipo_descuento == 'porcentaje' and valor_descuento and valor_descuento > 100:
            raise forms.ValidationError('El descuento porcentual no puede ser mayor al 100%.')

        return cleaned_data