from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Offer, Review, ReviewReply, BusinessRequest, VetoAppeal, Category
from django.core.exceptions import ValidationError


class CustomUserCreationForm(UserCreationForm):
    """Formulario de registro personalizado"""
    email = forms.EmailField(required=True, label='Correo Electrónico')
    first_name = forms.CharField(max_length=150, required=True, label='Nombre')
    last_name = forms.CharField(max_length=150, required=True, label='Apellido')
    register_as_business = forms.BooleanField(
        required=False, 
        label='Registrarme como negocio',
        help_text='Marcar esta opción si deseas crear una cuenta empresarial. Podrás completar la información del negocio después de que tu cuenta sea verificada por un administrador.'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'register_as_business':
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class CustomAuthenticationForm(AuthenticationForm):
    """Formulario de login personalizado"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class BusinessRequestForm(forms.ModelForm):
    """Formulario para solicitar cuenta empresarial"""
    class Meta:
        model = BusinessRequest
        fields = ['business_name', 'business_description', 'phone', 'latitude', 'longitude', 'location_name']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del negocio'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe tu negocio...'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+507 1234-5678'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ubicación', 'readonly': 'readonly'}),
        }


class OfferForm(forms.ModelForm):
    """Formulario para crear/editar ofertas"""
    class Meta:
        model = Offer
        fields = ['category', 'title', 'description', 'image', 'original_price', 
                  'discount_type', 'discount_value', 'quantity_x', 'quantity_y', 
                  'bundle_price', 'expires_at']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título de la oferta'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe la oferta...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'quantity_x': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': '1'}),
            'quantity_y': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': '1'}),
            'bundle_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'expires_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
        labels = {
            'quantity_x': 'Cantidad X',
            'quantity_y': 'Cantidad Y',
            'bundle_price': 'Precio del Paquete',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Obtener el tipo de descuento actual
        # Primero intentar desde los datos POST (si existe)
        if self.data and 'discount_type' in self.data:
            discount_type = self.data.get('discount_type')
        elif self.instance and self.instance.pk:
            discount_type = self.instance.discount_type
        else:
            discount_type = 'percentage'
        
        # Configurar campos según el tipo de descuento
        self._configure_fields_by_discount_type(discount_type)
    
    def _configure_fields_by_discount_type(self, discount_type):
        """Configurar visibilidad y requerimiento de campos según tipo de descuento"""
        # Campos para buy_x_get_y
        if discount_type == 'buy_x_get_y':
            self.fields['quantity_x'].required = True
            self.fields['quantity_y'].required = True
            self.fields['discount_value'].required = False
            self.fields['bundle_price'].required = False
            self.fields['original_price'].required = True
        # Campos para buy_x_for_price
        elif discount_type == 'buy_x_for_price':
            self.fields['quantity_x'].required = True
            self.fields['bundle_price'].required = True
            self.fields['discount_value'].required = False
            self.fields['quantity_y'].required = False
            # Precio original es opcional para este tipo (porque puede variar en el menú)
            self.fields['original_price'].required = False
            self.fields['original_price'].help_text = 'Opcional: Precio de referencia (puede variar en el menú)'
            # Remover atributo required del widget HTML
            if 'required' in self.fields['original_price'].widget.attrs:
                del self.fields['original_price'].widget.attrs['required']
        # Campos para percentage o fixed
        else:
            self.fields['discount_value'].required = True
            self.fields['quantity_x'].required = False
            self.fields['quantity_y'].required = False
            self.fields['bundle_price'].required = False
            self.fields['original_price'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value')
        original_price = cleaned_data.get('original_price')
        quantity_x = cleaned_data.get('quantity_x', 1)
        quantity_y = cleaned_data.get('quantity_y')
        bundle_price = cleaned_data.get('bundle_price')
        
        if discount_type == 'percentage':
            if not original_price:
                raise ValidationError('El precio original es requerido para descuentos porcentuales')
            if discount_value and discount_value > 100:
                raise ValidationError('El descuento porcentual no puede ser mayor al 100%')
            if not discount_value:
                raise ValidationError('El valor del descuento es requerido para descuentos porcentuales')
        
        if discount_type == 'fixed':
            if not original_price:
                raise ValidationError('El precio original es requerido para descuentos fijos')
            if discount_value and original_price:
                if discount_value >= original_price:
                    raise ValidationError('El descuento fijo no puede ser mayor o igual al precio original')
            if not discount_value:
                raise ValidationError('El valor del descuento es requerido para descuentos fijos')
        
        if discount_type == 'buy_x_get_y':
            if not original_price:
                raise ValidationError('El precio original es requerido para ofertas tipo "Compra X Lleva Y"')
            if not quantity_x or quantity_x < 1:
                raise ValidationError('La cantidad X debe ser al menos 1')
            if not quantity_y or quantity_y < 1:
                raise ValidationError('La cantidad Y debe ser al menos 1')
        
        if discount_type == 'buy_x_for_price':
            # El precio original es OPCIONAL para este tipo
            if not quantity_x or quantity_x < 1:
                raise ValidationError('La cantidad X debe ser al menos 1')
            if not bundle_price or bundle_price <= 0:
                raise ValidationError('El precio del paquete debe ser mayor a 0')
            # Si se proporciona precio original, validar que tenga sentido
            if original_price and bundle_price:
                # Solo validar si el precio original es muy bajo (menos de $0.50 por unidad)
                min_reasonable_price = bundle_price / quantity_x * 0.5  # 50% del precio del paquete
                if original_price < min_reasonable_price:
                    raise ValidationError(f'El precio original parece muy bajo. Debe ser al menos ${min_reasonable_price:.2f} por unidad para que la oferta tenga sentido.')
        
        return cleaned_data


class ReviewForm(forms.ModelForm):
    """Formulario para crear/editar reseñas"""
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i} Estrella{"s" if i > 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-select'}
            ),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Comparte tu experiencia...'}),
        }


class ReviewReplyForm(forms.ModelForm):
    """Formulario para responder a reseñas"""
    class Meta:
        model = ReviewReply
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Escribe tu respuesta...'
            }),
        }


class VetoAppealForm(forms.ModelForm):
    """Formulario para apelar un veto"""
    class Meta:
        model = VetoAppeal
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Explica por qué deberías ser reactivado...'}),
        }


class UserProfileForm(forms.ModelForm):
    """Formulario para editar perfil de usuario"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_image', 
                  'latitude', 'longitude', 'location_name', 'notifications_enabled']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BusinessInitialProfileForm(forms.ModelForm):
    """Formulario inicial para completar perfil de negocio al registrarse"""
    class Meta:
        model = User
        fields = ['business_name', 'business_description', 'latitude', 'longitude', 'location_name']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de tu negocio'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe tu negocio...'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'placeholder': 'Selecciona una ubicación en el mapa'}),
        }
        labels = {
            'business_name': 'Nombre del Negocio',
            'business_description': 'Descripción del Negocio',
            'location_name': 'Ubicación',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['business_name'].required = True
        self.fields['business_description'].required = True
        self.fields['latitude'].required = True
        self.fields['longitude'].required = True
        self.fields['location_name'].required = True


class BusinessProfileForm(forms.ModelForm):
    """Formulario para editar perfil de empresa"""
    class Meta:
        model = User
        fields = ['business_name', 'business_description', 'phone', 'profile_image', 
                  'latitude', 'longitude', 'location_name', 'notifications_enabled']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    """Formulario para crear/editar categorías (admin)"""
    class Meta:
        model = Category
        fields = ['name', 'description', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fa-shopping-bag'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }