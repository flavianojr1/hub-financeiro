#!/usr/bin/env python
"""
Ponto de entrada único do Hub Financeiro.
Substitui o manage.py e centraliza a execução do projeto.
"""
import os
import sys

def main():
    """Executa tarefas administrativas e o servidor."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Certifique-se de que ele está instalado "
            "e disponível no seu PYTHONPATH. Você esqueceu de ativar o ambiente virtual?"
        ) from exc

    # Se nenhum argumento for passado, inicia o servidor por padrão
    if len(sys.argv) == 1:
        print("--- Iniciando Hub Financeiro (Ambiente Local) ---")
        execute_from_command_line([sys.argv[0], "runserver"])
    else:
        # Repassa os argumentos para o Django (migrate, createsuperuser, etc)
        execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
