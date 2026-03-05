import csv
import re
import pdfplumber
import io
from decimal import Decimal
from datetime import datetime
from collections import Counter
from dateutil import parser
from dateutil.relativedelta import relativedelta
from .models import Invoice, Transaction

def process_inter_pdf(pdf_file, invoice):
    """
    Processa um arquivo PDF do Banco Inter e cria transações.
    """
    transactions_created = 0
    predictions_created = 0
    
    # Extrair data de vencimento da fatura (Página 1)
    due_date = None
    
    # Mapeamento de meses em português
    months_pt = {
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
    }

    # Regex para capturar: Data, Descrição, Valor
    inter_regex = re.compile(r'(\d{2} de (\w{3})\.? \d{4})\s+(.*?)\s+-\s+([\+\s]*R\$\s*[\d\.,]+)')
    
    # Regex para vencimento: "02/03/2026" (Página 1 ou 2)
    due_date_regex = re.compile(r'(\d{2}/\d{2}/\d{4})')

    with pdfplumber.open(pdf_file) as pdf:
        # Tentar pegar o vencimento nas primeiras páginas
        for i in range(2):
            text = pdf.pages[i].extract_text()
            if text:
                dates = due_date_regex.findall(text)
                if dates:
                    # O Inter repete o vencimento várias vezes, pegamos o primeiro
                    due_date = datetime.strptime(dates[0], '%d/%m/%Y').date()
                    break

        if not due_date:
            # Fallback para hoje caso não encontre
            due_date = datetime.now().date()

        # Configurar ano/mês da fatura baseado no vencimento (geralmente refere-se ao mês anterior ou atual)
        invoice.year = due_date.year
        invoice.month = due_date.month
        invoice.save()

        for page in pdf.pages:
            tables = page.extract_tables()
            all_rows = []
            for table in tables:
                for row in table:
                    line = " ".join([str(cell) for cell in row if cell])
                    all_rows.append(line)
            
            if not all_rows:
                text = page.extract_text()
                if text: all_rows = text.split('\n')

            for line in all_rows:
                match = inter_regex.search(line)
                if match:
                    _, month_abbr, description, value_str = match.groups()
                    if '+' in value_str: continue

                    try:
                        # Para o Banco Inter, a data da transação na fatura é informativa.
                        # Todos os gastos de uma fatura "pertencem" financeiramente ao mês de vencimento dela.
                        # Portanto, usamos o due_date para a transação principal.
                        date_val = due_date 

                        # Limpar valor
                        clean_value = value_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                        amount_val = Decimal(clean_value)

                        # Criar transação principal
                        t = Transaction.objects.create(
                            invoice=invoice,
                            date=date_val,
                            description=description.strip(),
                            amount=abs(amount_val),
                            is_predicted=False
                        )
                        transactions_created += 1

                        # Lógica de Parcelamento (Ex: Parcela 03 de 10)
                        installment_match = re.search(r'Parcela (\d{2}) de (\d{2})', description)
                        if installment_match:
                            current_installment = int(installment_match.group(1))
                            total_installments = int(installment_match.group(2))

                            if 0 < current_installment < total_installments:
                                remaining = total_installments - current_installment
                                for i in range(1, remaining + 1):
                                    next_date = due_date + relativedelta(months=i)
                                    next_desc = description.replace(
                                        f'Parcela {current_installment:02d} de {total_installments:02d}',
                                        f'Parcela {current_installment + i:02d} de {total_installments:02d}'
                                    ).strip()

                                    Transaction.objects.create(
                                        invoice=invoice,
                                        date=next_date,
                                        description=next_desc,
                                        amount=abs(amount_val),
                                        is_predicted=True
                                    )
                                    predictions_created += 1

                    except Exception:
                        continue

    return transactions_created, predictions_created


def process_nubank_csv(csv_file, invoice):
    """
    Processa um arquivo CSV do Nubank e cria transações.
    Detecta parcelamentos e cria previsões futuras.
    Também detecta o ano/mês predominante da fatura.
    """
    # Decodificar o arquivo
    csv_file.seek(0)
    decoded_file = csv_file.read().decode('utf-8').splitlines()

    reader = csv.reader(decoded_file)

    # Tentar identificar se há header
    first_row = next(reader)
    has_header = any(keyword in str(first_row).lower() for keyword in ['data', 'date', 'descri', 'valor', 'amount'])

    # Se não tem header, voltar para o início
    if not has_header:
        csv_file.seek(0)
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.reader(decoded_file)

    transactions_created = 0
    predictions_created = 0
    dates_found = []

    for row in reader:
        if len(row) < 3:
            continue

        try:
            # Identificar colunas automaticamente
            date_val = None
            description = None
            amount_val = None

            for idx, cell in enumerate(row):
                cell_str = str(cell).strip()

                # Tentar detectar data
                if not date_val:
                    try:
                        if '/' in cell_str or '-' in cell_str:
                            # Detectar se é formato ISO (YYYY-MM-DD ou YYYY/MM/DD)
                            if re.match(r'^\d{4}[/-]', cell_str):
                                date_val = parser.parse(cell_str, yearfirst=True, dayfirst=False).date()
                            else:
                                # Formato brasileiro DD/MM/YYYY ou DD-MM-YYYY
                                date_val = parser.parse(cell_str, dayfirst=True).date()
                    except:
                        pass

                # Tentar detectar valor (número com ou sem R$)
                if not amount_val:
                    try:
                        # Remover R$, espaços e trocar vírgula por ponto
                        clean_amount = cell_str.replace('R$', '').replace(' ', '').replace(',', '.')
                        # Tentar converter para Decimal
                        if clean_amount and (clean_amount.replace('.', '').replace('-', '').isdigit()):
                            amount_val = Decimal(clean_amount)
                    except:
                        pass

                # Se não é data nem valor, provavelmente é descrição
                if cell_str and not cell_str.replace('R$', '').replace(' ', '').replace(',', '').replace('.', '').replace('-', '').isdigit():
                    if '/' not in cell_str and '-' not in cell_str:
                        if not description or len(cell_str) > len(description):
                            description = cell_str
                    # Caso especial: descrição pode conter data e traço, mas geralmente é identificada aqui
                    elif description is None:
                         description = cell_str


            # Criar transação se conseguimos identificar os 3 campos
            if date_val and description and amount_val is not None:
                # Ignorar "Pagamento recebido" - é o pagamento da fatura anterior
                if 'pagamento recebido' in description.lower():
                    continue

                # Criar a transação REAL (atual)
                Transaction.objects.create(
                    invoice=invoice,
                    date=date_val,
                    description=description,
                    amount=abs(amount_val),  # Usar valor absoluto
                    is_predicted=False
                )
                transactions_created += 1
                dates_found.append(date_val)

                # Verificar parcelamento e criar previsões
                # Procura por padrões como: "Loja ABC - 01/10" ou "Compra X (1/5)"
                # Regex procura por digitos/digitos
                installment_match = re.search(r'(\d{1,2})/(\d{1,2})', description)

                if installment_match:
                    current_installment = int(installment_match.group(1))
                    total_installments = int(installment_match.group(2))

                    # Se detectou parcelamento válido (ex: 1/12) e não é a última
                    if 0 < current_installment < total_installments <= 60:
                        # Criar as parcelas futuras
                        remaining = total_installments - current_installment

                        for i in range(1, remaining + 1):
                            next_date = date_val + relativedelta(months=i)
                            next_installment = current_installment + i

                            # Atualizar descrição: "Loja ABC - 02/10"
                            # Substitui apenas a ocorrência da parcela
                            new_desc = description.replace(
                                f'{current_installment:02d}/{total_installments:02d}',
                                f'{next_installment:02d}/{total_installments:02d}'
                            ).replace(
                                f'{current_installment}/{total_installments}',
                                f'{next_installment}/{total_installments}'
                            )

                            # Evitar duplicatas em previsões já existentes?
                            # Por enquanto vamos criar vinculado a esta invoice
                            Transaction.objects.create(
                                invoice=invoice, # Vincula à fatura original para saber a origem
                                date=next_date,
                                description=new_desc,
                                amount=abs(amount_val),
                                is_predicted=True
                            )
                            predictions_created += 1

        except Exception as e:
            # Ignorar linhas com erro
            print(f"Erro ao processar linha: {row} - {e}")
            continue

    # Determinar ano/mês predominante da fatura
    if dates_found:
        month_counter = Counter((d.year, d.month) for d in dates_found)
        most_common = month_counter.most_common(1)[0][0]
        invoice.year = most_common[0]
        invoice.month = most_common[1]
        invoice.save()

    return transactions_created, predictions_created


def recategorize_user_transactions(user):
    """Reaplicar regras de categorização em todas as transações do usuário"""
    from .models import CategoryRule

    # Buscar regras do usuário
    rules = CategoryRule.objects.filter(user=user).select_related('category').order_by('-priority')
    
    # Buscar transações do usuário
    transactions = Transaction.objects.filter(invoice__user=user)
    
    count = 0
    for t in transactions:
        old_category = t.category
        
        # Lógica de auto-categorização inline para evitar N queries ou modificar o método do model
        new_category = 'Outros'
        desc_lower = t.description.lower()
        
        for rule in rules:
            if rule.keyword.lower() in desc_lower:
                new_category = rule.category.name
                break
        
        t.category = new_category
        
        if t.category != old_category:
            t.save(update_fields=['category'])
            count += 1
    return count


def get_temporal_data(transactions=None):
    """Agrupa transações por mês e por cartão para gráfico temporal empilhado"""
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth
    from collections import defaultdict

    if transactions is None:
        transactions = Transaction.objects.all()

    # Listar todos os meses que aparecem nos dados em ordem crescente
    months_qs = transactions.annotate(month=TruncMonth('date')).values('month').distinct().order_by('month')

    MONTH_ABBR = {
        1: 'jan', 2: 'fev', 3: 'mar', 4: 'abr',
        5: 'mai', 6: 'jun', 7: 'jul', 8: 'ago',
        9: 'set', 10: 'out', 11: 'nov', 12: 'dez'
    }

    labels = []
    month_keys = []
    for item in months_qs:
        m = item['month']
        if m:
            month_str = f"{MONTH_ABBR.get(m.month, '?')}/{m.year}"
            labels.append(month_str)
            month_keys.append(m)

    # Agrupar por cartão e mês
    grouped_data = transactions.annotate(
        month=TruncMonth('date')
    ).values('month', 'invoice__credit_card__name', 'invoice__credit_card__color').annotate(
        total=Sum('amount')
    )

    # Montar mapeamento de dados (card -> array de totais por mês)
    cards_info = defaultdict(lambda: {'data': [0]*len(labels), 'color': '#667eea'})

    for item in grouped_data:
        m = item['month']
        if not m: continue
        
        card_name = item['invoice__credit_card__name'] or 'Sem Cartão'
        card_color = item['invoice__credit_card__color'] or '#9ca3af'
        
        try:
            m_index = month_keys.index(m)
            cards_info[card_name]['data'][m_index] = float(item['total'])
            cards_info[card_name]['color'] = card_color
        except ValueError:
            pass

    datasets = []
    for name, info in cards_info.items():
        datasets.append({
            'label': name,
            'data': info['data'],
            'color': info['color']
        })

    return {
        'labels': labels,
        'datasets': datasets
    }


def get_category_data(transactions=None):
    """Agrupa transações por categoria para gráfico de barras"""
    from django.db.models import Sum

    if transactions is None:
        transactions = Transaction.objects.all()

    category_data = transactions.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')

    labels = []
    data = []

    for item in category_data:
        labels.append(item['category'])
        data.append(float(item['total']))

    return {
        'labels': labels,
        'data': data
    }
