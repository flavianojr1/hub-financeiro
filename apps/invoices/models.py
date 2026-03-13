from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Category(models.Model):
    """Categoria de gasto personalizada"""
    TYPE_CHOICES = [
        ('expense', 'Despesa (Fatura)'),
        ('income', 'Receita (Entrada)')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='expense', help_text='Define se é categoria de fatura ou de entrada')
    color = models.CharField(max_length=7, default='#667eea', help_text='Cor hex para gráficos')
    icon = models.CharField(max_length=10, default='📁', help_text='Emoji/ícone')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'
        unique_together = ['user', 'name', 'type']

    def __str__(self):
        return self.name


class CategoryRule(models.Model):
    """Regra de categorização por palavra-chave"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='category_rules', null=True, blank=True)
    keyword = models.CharField(max_length=100, help_text='Palavra-chave (case-insensitive)')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='rules')
    priority = models.IntegerField(default=0, help_text='Maior prioridade = processado primeiro')

    class Meta:
        ordering = ['-priority', 'keyword']
        unique_together = ['user', 'keyword']

    def __str__(self):
        return f'"{self.keyword}" → {self.category.name}'


class CreditCard(models.Model):
    """Cartão de Crédito"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_cards', null=True, blank=True)
    name = models.CharField(max_length=100, help_text='Ex: Nubank, Sicoob, Itaú')
    bank = models.CharField(max_length=100, help_text='Instituição Financeira')
    closing_day = models.IntegerField(help_text='Dia de fechamento da fatura')
    color = models.CharField(max_length=7, default='#667eea', help_text='Cor hex para gráficos')

    class Meta:
        ordering = ['name']
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.name} ({self.bank})"


class Invoice(models.Model):
    """Representa um arquivo CSV de fatura enviado"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    credit_card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    filename = models.CharField(max_length=255)
    year = models.IntegerField(null=True, blank=True)
    month = models.IntegerField(null=True, blank=True)

    MONTH_NAMES = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    class Meta:
        ordering = ['-year', '-month', '-uploaded_at']

    def __str__(self):
        return f"{self.filename} - {self.period_display}"

    @property
    def period_display(self):
        if self.year and self.month:
            return f"{self.MONTH_NAMES.get(self.month, '?')}/{self.year}"
        return "Período desconhecido"


class Transaction(models.Model):
    """Representa uma transação individual da fatura"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    date = models.DateField()
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, blank=True)
    is_predicted = models.BooleanField(default=False, help_text='Transação gerada automaticamente como previsão de parcelas futuras')

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.description}: R$ {self.amount}"

    def save(self, *args, **kwargs):
        # Auto-categorizar se não tiver categoria
        if not self.category:
            self.category = self.auto_categorize()
        super().save(*args, **kwargs)

    def auto_categorize(self):
        """Categoriza automaticamente baseado nas regras de palavra-chave do banco"""
        desc_lower = self.description.lower()

        # Buscar regras apenas do usuário dono desta transação (via invoice)
        user = self.invoice.user if self.invoice else None
        
        # Se não houver usuário, buscar regras globais (user=None) ou retornar vazio
        rules = CategoryRule.objects.filter(user=user).select_related('category').order_by('-priority')

        for rule in rules:
            if rule.keyword.lower() in desc_lower:
                return rule.category.name

        return 'Outros'


class Income(models.Model):
    """Representa uma entrada/receita manual (salário, bônus, etc)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=100, blank=True, help_text='Categoria inferida automaticamente')
    is_recurring = models.BooleanField(default=False, help_text='Indica se foi criado como uma entrada recorrente')
    recurring_group_id = models.CharField(max_length=50, null=True, blank=True, help_text='Agrupa entradas recorrentes para exclusão em lote')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date} - {self.description}: R$ {self.amount}"

    def save(self, *args, **kwargs):
        # Auto-categorizar se não tiver categoria
        if not self.category:
            self.category = self.auto_categorize()
        super().save(*args, **kwargs)

    def auto_categorize(self):
        """Categoriza automaticamente baseado nas regras de palavra-chave do banco do tipo INCOME"""
        desc_lower = self.description.lower()
        
        # Buscar regras apenas do tipo 'income' para este usuário
        rules = CategoryRule.objects.filter(
            user=self.user, 
            category__type='income'
        ).select_related('category').order_by('-priority')

        for rule in rules:
            if rule.keyword.lower() in desc_lower:
                return rule.category.name

        return 'Outras Entradas'


class PixBoleto(models.Model):
    """Representa uma saída manual via Pix ou Boleto (fora do cartão)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pix_boletos')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=100, blank=True, help_text='Categoria inferida automaticamente')
    is_recurring = models.BooleanField(default=False)
    recurring_group_id = models.CharField(max_length=50, blank=True, null=True, help_text='Agrupa saídas recorrentes para exclusão em lote')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Pix/Boleto'
        verbose_name_plural = 'Pix e Boletos'

    def __str__(self):
        return f"{self.date} - {self.description}: R$ {self.amount}"

    def save(self, *args, **kwargs):
        # Auto-categorizar se não tiver categoria
        if not self.category:
            self.category = self.auto_categorize()
        super().save(*args, **kwargs)

    def auto_categorize(self):
        """Categoriza automaticamente baseado nas regras de palavra-chave do tipo EXPENSE"""
        desc_lower = self.description.lower()
        
        # Buscar regras apenas do tipo 'expense' para este usuário
        rules = CategoryRule.objects.filter(
            user=self.user, 
            category__type='expense'
        ).select_related('category').order_by('-priority')

        for rule in rules:
            if rule.keyword.lower() in desc_lower:
                return rule.category.name

        return 'Outros'
