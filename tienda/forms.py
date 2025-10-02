from django import forms
from django.db import models
from django.utils.safestring import mark_safe
from .models import Producto, Cupon, Profile, NewsletterSubscription, NewsletterCampaign, ProductoImagen


class ImagePreviewWidget(forms.ClearableFileInput):
    """Widget personalizado para vista previa de imágenes con drag & drop"""
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.update({
            'multiple': True,
            'accept': 'image/*',
            'class': 'image-upload-widget form-control',
            'data-max-files': '10',
            'data-max-size': '5MB'
        })
        super().__init__(attrs)

    def value_from_datadict(self, data, files, name):
        """Return a list of UploadedFile objects for multiple file uploads"""
        if hasattr(files, 'getlist'):
            file_list = files.getlist(name)
            print(f"DEBUG ImagePreviewWidget.value_from_datadict: Recibidos {len(file_list)} archivos")
            return file_list
        single_file = files.get(name)
        if single_file:
            print(f"DEBUG ImagePreviewWidget.value_from_datadict: Recibido 1 archivo: {single_file.name}")
            return [single_file]
        print("DEBUG ImagePreviewWidget.value_from_datadict: No se recibieron archivos")
        return []

    def value_omitted_from_data(self, data, files, name):
        """Check if the field value is omitted from the data"""
        return name not in files

    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget with debugging"""
        if attrs is None:
            attrs = {}
        
        # Asegurar atributos necesarios
        attrs.update({
            'multiple': True,
            'accept': 'image/*',
        })
        
        html = super().render(name, value, attrs, renderer)
        print(f"DEBUG ImagePreviewWidget.render: Renderizando campo {name}")
        return html


class ImageManagementWidget(forms.Widget):
    """Widget completo para gestión de imágenes con vista previa y gestión existente"""
    allow_multiple_selected = True

    def __init__(self, existing_images=None, attrs=None):
        self.existing_images = existing_images or []
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}

        # Widget de subida simple
        upload_widget = MultipleFileInput(attrs={
            'id': f'id_{name}',
            'name': name,
            'class': 'image-upload-input',
            'accept': 'image/*',
            'style': 'display: none;'
        })

        # Renderizar HTML personalizado
        html = f'''
        <div class="image-management-container" id="image-management-{name}">
            <!-- Área de drag & drop -->
            <div class="image-upload-area" id="upload-area-{name}">
                <div class="upload-placeholder">
                    <i class="bi bi-cloud-upload"></i>
                    <p>Arrastra imágenes aquí o <span class="upload-link" id="upload-link-{name}">haz clic para seleccionar</span></p>
                    <small>Máximo 10 imágenes, 5MB cada una</small>
                </div>
            </div>

            <!-- Vista previa de imágenes nuevas -->
            <div class="new-images-preview" id="new-images-{name}">
                <div class="images-grid" id="new-images-grid-{name}"></div>
            </div>

            <!-- Gestión de imágenes existentes -->
            <div class="existing-images-section" id="existing-images-{name}">
                <h4>Imágenes existentes:</h4>
                <div class="images-grid sortable" id="existing-images-grid-{name}">
        '''

        # Agregar imágenes existentes
        for img in self.existing_images:
            html += f'''
                    <div class="image-item existing-image" data-image-id="{img.id}">
                        <div class="image-container">
                            <img src="{img.url_imagen}" alt="{img.imagen_nombre}" class="image-preview">
                            <div class="image-overlay">
                                <button type="button" class="btn btn-sm btn-danger delete-image" data-image-id="{img.id}">
                                    <i class="bi bi-trash"></i>
                                </button>
                                <button type="button" class="btn btn-sm btn-warning set-primary {'btn-success' if img.es_principal else ''}" data-image-id="{img.id}">
                                    <i class="bi bi-star"></i> {'Principal' if img.es_principal else 'Hacer Principal'}
                                </button>
                            </div>
                        </div>
                        <div class="image-info">
                            <small class="text-muted">{img.imagen_nombre}</small>
                            <input type="hidden" name="existing_images_order[]" value="{img.id}">
                        </div>
                    </div>
            '''

        html += f'''
            <!-- Campo oculto para imágenes a eliminar -->
            <input type="hidden" name="images_to_delete" id="images_to_delete" value="">
            {upload_widget.render(name, value)}
        </div>
        '''

        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        """Return a list of UploadedFile objects for multiple file uploads"""
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

    def value_omitted_from_data(self, data, files, name):
        """Check if the field value is omitted from the data"""
        return name not in files


class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.update({'multiple': True, 'accept': 'image/*'})
        super().__init__(attrs)

    def value_from_datadict(self, data, files, name):
        """Return a list of UploadedFile objects for multiple file uploads"""
        print(f"DEBUG MultipleFileInput.value_from_datadict: Extrayendo archivos para campo '{name}'")
        print(f"DEBUG MultipleFileInput.value_from_datadict: files keys: {list(files.keys())}")
        
        if hasattr(files, 'getlist'):
            file_list = files.getlist(name)
            print(f"DEBUG MultipleFileInput.value_from_datadict: getlist retornó {len(file_list)} archivos")
            return file_list
        
        single_file = files.get(name)
        print(f"DEBUG MultipleFileInput.value_from_datadict: get retornó: {single_file}")
        return single_file

    def value_omitted_from_data(self, data, files, name):
        """Check if the field value is omitted from the data"""
        return name not in files


class MultipleFileField(forms.FileField):
    """Campo personalizado para múltiples archivos"""
    widget = MultipleFileInput
    default_validators = []  # No validar archivos individualmente

    def __init__(self, *args, **kwargs):
        self.max_files = kwargs.pop('max_files', 10)
        self.max_file_size = kwargs.pop('max_file_size', 5 * 1024 * 1024)  # 5MB
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """Convertir el valor a una lista de archivos"""
        print(f"DEBUG MultipleFileField.to_python: Recibido valor: {type(value)}, {value}")
        if value is None:
            print("DEBUG MultipleFileField.to_python: Valor es None, retornando lista vacía")
            return []
        if isinstance(value, list):
            print(f"DEBUG MultipleFileField.to_python: Valor es lista con {len(value)} elementos")
            return value
        print(f"DEBUG MultipleFileField.to_python: Valor único convertido a lista")
        return [value]

    def validate(self, value):
        """Validar la lista de archivos"""
        if self.required and not value:
            raise forms.ValidationError("Este campo es obligatorio.")

        if len(value) > self.max_files:
            raise forms.ValidationError(f"No puedes subir más de {self.max_files} imágenes.")

        for file in value:
            if hasattr(file, 'size') and file.size > self.max_file_size:
                raise forms.ValidationError(f"El archivo {file.name} es demasiado grande. Máximo {self.max_file_size // (1024*1024)}MB.")

            # Validar tipo de archivo
            if hasattr(file, 'content_type'):
                allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if file.content_type not in allowed_types:
                    raise forms.ValidationError(f"El archivo {file.name} no es un tipo de imagen válido. Solo se permiten: JPEG, PNG, GIF, WebP.")


class ProductoAdminForm(forms.ModelForm):
    # Campo personalizado para subir múltiples imágenes como blobs
    imagenes_files = MultipleFileField(
        required=False,
        max_files=10,
        max_file_size=5 * 1024 * 1024,  # 5MB
        label="Imágenes del producto",
        help_text="Arrastra imágenes aquí o haz clic para seleccionar. Máximo 10 imágenes de 5MB cada una."
    )

    # Campo oculto para imágenes a eliminar
    images_to_delete = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label=""
    )

    # Campo oculto para orden de imágenes existentes
    existing_images_order = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label=""
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

        # Configurar campos opcionales
        self.fields['peso'].required = False
        self.fields['dimensiones'].required = False
        self.fields['sku'].required = False

        # Configurar el widget personalizado para imágenes
        print(f"DEBUG ProductoAdminForm.__init__: Configurando widget para imagenes_files")
        
        if self.instance and self.instance.pk:
            existing_images = list(self.instance.imagenes.order_by('orden'))
            print(f"DEBUG ProductoAdminForm.__init__: Producto existente con {len(existing_images)} imágenes")
            self.fields['imagenes_files'].widget = ImagePreviewWidget()  # Usar widget simple por ahora

            num_imagenes = len(existing_images)
            if num_imagenes > 0:
                self.fields['imagenes_files'].help_text += f" Actualmente tiene {num_imagenes} imagen(es)."
        else:
            # Para productos nuevos, usar el widget de subida simple
            print("DEBUG ProductoAdminForm.__init__: Producto nuevo, usando ImagePreviewWidget")
            self.fields['imagenes_files'].widget = ImagePreviewWidget()

    def clean(self):
        cleaned_data = super().clean()

        # Validar que no se eliminen todas las imágenes si no se suben nuevas
        images_to_delete = self.data.get('images_to_delete', '')
        uploaded_files = self.files.getlist('imagenes_files') if self.files and hasattr(self.files, 'getlist') and 'imagenes_files' in self.files else []
        
        # Si no tiene getlist, intentar obtener como lista o valor único
        if not uploaded_files and self.files and 'imagenes_files' in self.files:
            file_value = self.files['imagenes_files']
            if isinstance(file_value, list):
                uploaded_files = file_value
            else:
                uploaded_files = [file_value] if file_value else []

        if self.instance and self.instance.pk:
            current_images = self.instance.imagenes.count()
            images_to_delete_count = len(images_to_delete.split(',')) if images_to_delete else 0

            # Para productos existentes, permitir guardar sin imágenes por ahora
            # Solo mostrar una advertencia
            if current_images - images_to_delete_count == 0 and not uploaded_files:
                # No agregar error, solo una advertencia en el campo
                pass
        else:
            # Para productos nuevos, requerir al menos una imagen
            if not uploaded_files:
                self.add_error('imagenes_files', "El producto debe tener al menos una imagen.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()

            # Evitar procesar archivos múltiples veces
            if hasattr(self, '_files_processed'):
                print("DEBUG: Archivos ya procesados, saltando...")
                return instance
            self._files_processed = True

            # Procesar imágenes a eliminar
            images_to_delete = self.cleaned_data.get('images_to_delete', '')
            if images_to_delete:
                image_ids = [int(id.strip()) for id in images_to_delete.split(',') if id.strip()]
                ProductoImagen.objects.filter(id__in=image_ids, producto=instance).delete()

            # Procesar reordenamiento de imágenes existentes
            existing_order = self.data.get('existing_images_order', '')
            if existing_order:
                order_data = existing_order.split(',')
                for index, image_id in enumerate(order_data):
                    if image_id.strip():
                        try:
                            img = ProductoImagen.objects.get(id=int(image_id), producto=instance)
                            img.orden = index
                            img.save()
                        except (ProductoImagen.DoesNotExist, ValueError):
                            pass

            # Procesar los archivos subidos si existen
            uploaded_files = self.files.getlist('imagenes_files') if self.files and hasattr(self.files, 'getlist') and 'imagenes_files' in self.files else []
            
            # Si no tiene getlist, intentar obtener como lista o valor único
            if not uploaded_files and self.files and 'imagenes_files' in self.files:
                file_value = self.files['imagenes_files']
                if isinstance(file_value, list):
                    uploaded_files = file_value
                else:
                    uploaded_files = [file_value] if file_value else []
            
            # DEBUG: Agregar logs para depuración
            print(f"DEBUG ProductoAdminForm.save(): self.files = {self.files}")
            print(f"DEBUG: uploaded_files = {uploaded_files}")
            print(f"DEBUG: len(uploaded_files) = {len(uploaded_files)}")

            if commit:
                # Obtener el orden máximo actual para las nuevas imágenes
                max_orden = instance.imagenes.aggregate(max_orden=models.Max('orden'))['max_orden'] or 0
                print(f"DEBUG: max_orden inicial: {max_orden}")

                has_principal = instance.imagenes.filter(es_principal=True).exists()
                for i, uploaded_file in enumerate(uploaded_files):
                    try:
                        # Asegurar que el archivo esté al inicio
                        uploaded_file.seek(0)
                        file_content = uploaded_file.read()
                        print(f"DEBUG: Procesando archivo: {uploaded_file.name}, tamaño: {len(file_content)} bytes")
                        
                        # Verificar que el archivo no esté vacío
                        if len(file_content) == 0:
                            print(f"WARNING: El archivo {uploaded_file.name} está vacío, saltando...")
                            continue
                        
                        es_principal = not has_principal and i == 0  # Primera imagen y no hay principal
                        nueva_imagen = ProductoImagen.objects.create(
                            producto=instance,
                            imagen_blob=file_content,
                            imagen_nombre=uploaded_file.name,
                            imagen_tipo_mime=uploaded_file.content_type or 'application/octet-stream',
                            orden=max_orden + 1,
                            es_principal=es_principal
                        )
                        print(f"DEBUG: Imagen creada exitosamente: {nueva_imagen.imagen_nombre} (ID: {nueva_imagen.id})")
                        max_orden += 1
                        # Si es la primera imagen y no hay principal, ya tenemos principal
                        if es_principal:
                            has_principal = True
                    except Exception as e:
                        print(f"ERROR: Fallo al procesar archivo {uploaded_file.name}: {e}")
                        import traceback
                        traceback.print_exc()

                print(f"DEBUG: ProductoAdminForm.save() completado. Total imágenes del producto: {instance.imagenes.count()}")

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