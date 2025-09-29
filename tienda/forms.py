from django import forms
from django.db import models
from .models import Producto, Cupon, Profile, NewsletterSubscription, NewsletterCampaign, ProductoImagen


class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.update({'multiple': True, 'accept': 'image/*'})
        super().__init__(attrs)

    def value_from_datadict(self, data, files, name):
        """Return a list of UploadedFile objects for multiple file uploads"""
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

    def value_omitted_from_data(self, data, files, name):
        """Check if the field value is omitted from the data"""
        return name not in files


class MultipleFileField(forms.FileField):
    """Campo personalizado para múltiples archivos"""
    widget = MultipleFileInput
    default_validators = []  # No validar archivos individualmente

    def to_python(self, value):
        """Convertir el valor a una lista de archivos"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def validate(self, value):
        """Validar la lista de archivos"""
        if self.required and not value:
            raise forms.ValidationError("Este campo es obligatorio.")
        for file in value:
            if hasattr(file, 'size') and self.max_length is not None and file.size > self.max_length:
                raise forms.ValidationError(f"El archivo {file.name} es demasiado grande.")


class ProductoAdminForm(forms.ModelForm):
    # Campo personalizado para subir múltiples imágenes como blobs
    imagenes_files = MultipleFileField(
        required=False,
        label="Imágenes del producto",
        help_text="Selecciona una o más imágenes para subir. Se almacenarán como blobs en la base de datos."
    )

    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'precio', 'categoria',
                 'stock', 'stock_minimo', 'sku', 'estado', 'peso', 'dimensiones']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'peso': forms.NumberInput(attrs={'step': '0.01'}),
            'dimensiones': forms.TextInput(attrs={'placeholder': 'Ej: 10x20x5 cm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si el producto ya tiene imágenes, mostrar información
        if self.instance and self.instance.pk:
            num_imagenes = self.instance.imagenes.count()
            if num_imagenes > 0:
                self.fields['imagenes_files'].help_text += f" Actualmente tiene {num_imagenes} imagen(es)."

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Procesar los archivos subidos si existen
        uploaded_files = self.files.getlist('imagenes_files')
        if uploaded_files:
            # Si estamos editando, determinar el orden inicial
            if instance.pk:
                ultimo_orden = instance.imagenes.aggregate(max_orden=models.Max('orden'))['max_orden'] or 0
            else:
                ultimo_orden = 0

            for uploaded_file in uploaded_files:
                # Leer el contenido del archivo
                file_content = uploaded_file.read()

                # Crear nueva imagen para el producto
                ProductoImagen.objects.create(
                    producto=instance,
                    imagen_blob=file_content,
                    imagen_nombre=uploaded_file.name,
                    imagen_tipo_mime=uploaded_file.content_type or 'application/octet-stream',
                    orden=ultimo_orden + 1
                )
                ultimo_orden += 1

        if commit:
            instance.save()

        return instance


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'precio', 'categoria', 'stock', 'stock_minimo',
                 'sku', 'estado', 'peso', 'dimensiones']
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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['telefono', 'fecha_nacimiento', 'genero', 'biografia']
        widgets = {
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'genero': forms.Select(attrs={
                'class': 'form-select'
            }),
            'biografia': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Cuéntanos un poco sobre ti...'
            }),
        }


# ===== FORMULARIOS DE NEWSLETTER =====

class NewsletterSubscriptionForm(forms.ModelForm):
    """Formulario para suscripción al newsletter"""
    class Meta:
        model = NewsletterSubscription
        fields = ['email', 'nombre', 'frecuencia', 'recibir_ofertas', 'recibir_novedades', 'recibir_recomendaciones']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'tu@email.com',
                'required': True
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tu nombre (opcional)'
            }),
            'frecuencia': forms.Select(attrs={
                'class': 'form-select'
            }),
            'recibir_ofertas': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'recibir_novedades': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'recibir_recomendaciones': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if NewsletterSubscription.objects.filter(email=email, activo=True).exists():
            raise forms.ValidationError('Este email ya está suscrito al newsletter.')
        return email


class NewsletterUnsubscribeForm(forms.Form):
    """Formulario para cancelar suscripción"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tu@email.com',
            'required': True
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            subscription = NewsletterSubscription.objects.get(email=email, activo=True)
            if not subscription.confirmado:
                raise forms.ValidationError('Esta suscripción no está confirmada.')
        except NewsletterSubscription.DoesNotExist:
            raise forms.ValidationError('No se encontró una suscripción activa con este email.')
        return email


class NewsletterCampaignForm(forms.ModelForm):
    """Formulario para crear/editar campañas de newsletter"""
    class Meta:
        model = NewsletterCampaign
        fields = ['titulo', 'asunto', 'contenido_html', 'contenido_texto',
                 'fecha_programada', 'frecuencia_target', 'solo_confirmados',
                 'tracking_aperturas', 'tracking_clics']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título de la campaña'
            }),
            'asunto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Asunto del email'
            }),
            'contenido_html': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'id': 'contenido_html',
                'placeholder': 'Contenido HTML del newsletter...'
            }),
            'contenido_texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Versión texto plano (opcional)...'
            }),
            'fecha_programada': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'frecuencia_target': forms.Select(attrs={
                'class': 'form-select'
            }),
            'solo_confirmados': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'tracking_aperturas': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'tracking_clics': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos opcionales
        self.fields['contenido_texto'].required = False
        self.fields['fecha_programada'].required = False
        self.fields['frecuencia_target'].required = False


class NewsletterTestForm(forms.Form):
    """Formulario para enviar newsletter de prueba"""
    email_prueba = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@prueba.com'
        })
    )