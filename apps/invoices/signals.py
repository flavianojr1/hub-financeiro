from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Category, CategoryRule

@receiver(post_save, sender=User)
def create_default_categories(sender, instance, created, **kwargs):
    """Cria categorias e regras padrão para novos usuários"""
    if created:
        # Lista de categorias padrão com suas cores, ícones e regras iniciais
        defaults = [
            {
                'name': 'Alimentação', 
                'color': '#f5576c', 
                'icon': '🍔', 
                'rules': ['iFood', 'Restaurante', 'Mcdonald', 'Burger King', 'Sweetco']
            },
            {
                'name': 'Transporte', 
                'color': '#4facfe', 
                'icon': '🚗', 
                'rules': ['Uber', '99app', 'Posto', 'Shell', 'Ipiranga', 'Bilhunico', 'Recargapay *Bilhunico']
            },
            {
                'name': 'Mercado', 
                'color': '#43e97b', 
                'icon': '🛒', 
                'rules': ['Mercado', 'Carrefour', 'Extra', 'Pão de Açucar', 'Marukai', 'Towa', 'Azuki']
            },
            {
                'name': 'Lazer', 
                'color': '#fa709a', 
                'icon': '🍿', 
                'rules': ['Netflix', 'Spotify', 'Cinema', 'Steam', 'Jogos', 'App Store', 'Apple.com/Bill', 'Google Claude']
            },
            {
                'name': 'Saúde', 
                'color': '#fee140', 
                'icon': '💊', 
                'rules': ['Farmacia', 'Droga', 'Hospital', 'Odonto', 'Laboratorio']
            },
            {
                'name': 'Serviços', 
                'color': '#764ba2', 
                'icon': '⚡', 
                'rules': ['Claro', 'Vivo', 'Tim', 'Energia', 'Agua', 'Internet', 'Condominio', 'Google One']
            },
            {
                'name': 'Assinaturas', 
                'color': '#fee140', 
                'icon': '📅', 
                'rules': ['Amazon Prime', 'Disney Plus', 'HBO Max', 'Youtube', 'Udemy']
            },
            {
                'name': 'Compras', 
                'color': '#30cfd0', 
                'icon': '🛍️', 
                'rules': ['Mercado Livre', 'Amazon', 'Shopee', 'Magalu', 'Renner', 'Farm', 'Temu']
            },
        ]

        for item in defaults:
            # Criar a categoria para o usuário
            category, _ = Category.objects.get_or_create(
                user=instance,
                name=item['name'],
                defaults={
                    'color': item['color'],
                    'icon': item['icon']
                }
            )
            
            # Criar as regras iniciais vinculadas a essa categoria e usuário
            for keyword in item['rules']:
                CategoryRule.objects.get_or_create(
                    user=instance,
                    keyword=keyword,
                    defaults={'category': category}
                )
