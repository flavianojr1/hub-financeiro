from django import forms
from .models import Category, CategoryRule, CreditCard


class CSVUploadForm(forms.Form):
    """Form para upload de arquivo CSV ou PDF (Inter)"""
    csv_file = forms.FileField(
        label='Arquivo de Fatura',
        help_text='Selecione o arquivo CSV (Nubank) ou PDF (Inter) da sua fatura',
        widget=forms.FileInput(attrs={
            'accept': '.csv,.pdf',
            'class': 'file-input',
            'id': 'csvFile'
        })
    )
    credit_card = forms.ModelChoiceField(
        queryset=CreditCard.objects.none(),
        label='Cartão de Crédito',
        help_text='Selecione o cartão vinculada a esta fatura',
        widget=forms.Select(attrs={
            'class': 'form-input',
            'id': 'creditCard'
        })
    )

    target_month = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    target_year = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        upload_mode = kwargs.pop('upload_mode', False)
        super(CSVUploadForm, self).__init__(*args, **kwargs)
        if user:
            queryset = CreditCard.objects.filter(user=user).order_by('name')
            self.fields['credit_card'].queryset = queryset

            if upload_mode:
                has_cards = queryset.exists()
                self.fields['credit_card'].empty_label = (
                    'Selecione um cartão' if has_cards else 'Nenhum cartão cadastrado.'
                )
                if not has_cards:
                    self.fields['credit_card'].widget.attrs['disabled'] = 'disabled'

    def clean_csv_file(self):
        file = self.cleaned_data.get('csv_file')
        if file:
            extension = file.name.lower().split('.')[-1]
            if extension not in ['csv', 'pdf']:
                raise forms.ValidationError('O arquivo deve ter extensão .csv ou .pdf')
            # Limite de 5MB
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('O arquivo não pode ter mais de 5MB')
        return file


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'color', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Alimentação, Transporte...',
                'id': 'categoryName',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-input form-input-color',
                'type': 'color',
                'id': 'categoryColor',
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '🍔',
                'id': 'categoryIcon',
                'style': 'max-width: 80px; text-align: center; font-size: 1.5rem; cursor: pointer;',
                'readonly': 'readonly',
            }),
        }


class CategoryRuleForm(forms.ModelForm):
    class Meta:
        model = CategoryRule
        fields = ['keyword', 'category', 'priority']
        widgets = {
            'keyword': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: ifood, barbearia, netflix...',
                'id': 'ruleKeyword',
            }),
            'category': forms.Select(attrs={
                'class': 'form-input',
                'id': 'ruleCategory',
            }),
            'priority': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0',
                'id': 'rulePriority',
                'style': 'max-width: 100px;',
            }),
        }


    def clean_keyword(self):
        keyword = self.cleaned_data.get('keyword')
        if keyword:
            return keyword.strip()
        return keyword

class CreditCardForm(forms.ModelForm):
    class Meta:
        model = CreditCard
        fields = ['name', 'bank', 'closing_day', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Nubank, Sicoob, Itaú...',
            }),
            'bank': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Nubank',
            }),
            'closing_day': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '1 a 31',
                'min': '1',
                'max': '31',
                'oninput': 'if(this.value.length > 2) this.value = this.value.slice(0, 2);',
                'style': 'max-width: 100px;',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-input form-input-color',
                'type': 'color',
            }),
        }
