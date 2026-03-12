import csv
import re
import pdfplumber
import io
import django.db.models as models
from decimal import Decimal
from datetime import datetime
from collections import Counter
from dateutil import parser
from dateutil.relativedelta import relativedelta
from .models import Invoice, Transaction

def create_transaction_deduplicated(invoice, date, description, amount, is_predicted=False):
    """
    Cria uma transação garantindo integridade entre dados REAIS e PREVISTOS.
    Previsões (is_predicted=True) são substituídas quando o dado REAL (is_predicted=False) chega.
    """
    # Buscar duplicatas considerando data, valor e descrição em TODAS as faturas do usuário para este cartão
    duplicate_qs = Transaction.objects.filter(
        invoice__user=invoice.user,
        invoice__credit_card=invoice.credit_card,
        date=date,
        amount=amount,
        description=description
    )

    if is_predicted:
        # Se estamos tentando criar uma PREVISÃO, mas já existe algo (REAL ou PREVISTO), ignora
        if duplicate_qs.exists():
            return None
    else:
        # Se estamos tentando criar uma REAL, removemos TODAS as previsões idênticas que existirem (em qualquer fatura)
        predicted_matches = duplicate_qs.filter(is_predicted=True)
        if predicted_matches.exists():
            predicted_matches.delete()
        
        # Como "a fatura é a lei", permitimos criar o dado REAL mesmo que exista outro igual
        # (ex: dois gastos idênticos no mesmo dia/valor/loja)

    # Criar a transação finalmente
    return Transaction.objects.create(
        invoice=invoice,
        date=date,
        description=description,
        amount=amount,
        is_predicted=is_predicted
    )


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

        # Configurar ano/mês da fatura baseado no vencimento
        invoice.year = due_date.year
        invoice.month = due_date.month
        invoice.save()

        # LIMPEZA ESTRATÉGICA: Ao subir uma fatura REAL, removemos TODAS as previsões
        # deste cartão para este mês e meses futuros. O arquivo atual será a nova fonte da verdade.
        Transaction.objects.filter(
            invoice__credit_card=invoice.credit_card,
            date__year__gte=invoice.year,
            is_predicted=True
        ).filter(
            # Garante que só apague meses futuros do mesmo ano ou qualquer mês de anos futuros
            models.Q(date__year__gt=invoice.year) | models.Q(date__month__gte=invoice.month)
        ).delete()

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
                        date_val = due_date 

                        # Limpar valor
                        clean_value = value_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                        amount_val = Decimal(clean_value)

                        # Criar transação principal deduplicada
                        t = create_transaction_deduplicated(
                            invoice=invoice,
                            date=date_val,
                            description=description.strip(),
                            amount=abs(amount_val),
                            is_predicted=False
                        )
                        if t: transactions_created += 1

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

                                    create_transaction_deduplicated(
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
    import django.db.models as models

    # Decodificar o arquivo
    csv_file.seek(0)
    decoded_file = csv_file.read().decode('utf-8').splitlines()

    # Primeira passada: Descobrir o mês predominante para limpar previsões futuras
    reader = csv.reader(decoded_file)
    try:
        first_row = next(reader)
        has_header = any(keyword in str(first_row).lower() for keyword in ['data', 'date', 'descri', 'valor', 'amount'])
    except StopIteration:
        return 0, 0

    if not has_header:
        csv_file.seek(0)
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.reader(decoded_file)

    dates_found = []
    rows_to_process = []
    
    for row in reader:
        if len(row) < 3: continue
        rows_to_process.append(row)
        # Tentar extrair data de qualquer coluna
        for cell in row:
            cell_str = str(cell).strip()
            if '/' in cell_str or '-' in cell_str:
                try:
                    if re.match(r'^\d{4}[/-]', cell_str):
                        dates_found.append(parser.parse(cell_str, yearfirst=True, dayfirst=False).date())
                        break
                    elif re.match(r'^\d{2}[/-]\d{2}[/-]\d{4}$', cell_str) or re.match(r'^\d{2}[/-]\d{2}[/-]\d{2}$', cell_str):
                        dates_found.append(parser.parse(cell_str, dayfirst=True).date())
                        break
                except: pass

    # Determinar ano/mês predominante
    if dates_found:
        month_counter = Counter((d.year, d.month) for d in dates_found)
        most_common = month_counter.most_common(1)[0][0]
        invoice.year = most_common[0]
        invoice.month = most_common[1]
        invoice.save()

        # LIMPEZA ESTRATÉGICA: Remover previsões deste cartão para este mês e meses futuros
        from .models import Transaction
        Transaction.objects.filter(
            invoice__credit_card=invoice.credit_card,
            is_predicted=True
        ).filter(
            models.Q(date__year__gt=invoice.year) | models.Q(date__year=invoice.year, date__month__gte=invoice.month)
        ).delete()

    transactions_created = 0
    predictions_created = 0
    payments = []

    # Segunda passada: Processar transações
    for row in rows_to_process:
        try:
            date_val = None
            amount_val = None
            desc_cols = []

            for cell in row:
                cell_str = str(cell).strip()
                if not cell_str: continue

                if date_val is None:
                    try:
                        if '/' in cell_str or '-' in cell_str:
                            if re.match(r'^\d{4}[/-]', cell_str):
                                date_val = parser.parse(cell_str, yearfirst=True, dayfirst=False).date()
                                continue
                            elif re.match(r'^\d{2}[/-]\d{2}[/-]\d{4}$', cell_str) or re.match(r'^\d{2}[/-]\d{2}[/-]\d{2}$', cell_str):
                                date_val = parser.parse(cell_str, dayfirst=True).date()
                                continue
                    except: pass

                if amount_val is None:
                    try:
                        clean_amount = cell_str.replace('R$', '').replace(' ', '').replace(',', '.')
                        if clean_amount and re.match(r'^-?\d+(\.\d+)?$', clean_amount):
                            amount_val = Decimal(clean_amount)
                            continue
                    except: pass
                
                desc_cols.append(cell_str)

            description = " ".join(desc_cols).strip()

            if date_val and description and amount_val is not None:
                desc_lower = description.lower()
                
                # Coletar pagamentos para análise posterior
                if 'pagamento recebido' in desc_lower or 'pagamento efetuado' in desc_lower:
                    payments.append((date_val, description, amount_val))
                    continue

                t = create_transaction_deduplicated(
                    invoice=invoice,
                    date=date_val,
                    description=description.strip(),
                    amount=amount_val,
                    is_predicted=False
                )
                if t: transactions_created += 1

                installment_match = re.search(r'(\d{1,2})/(\d{1,2})', description)
                if installment_match:
                    current_installment = int(installment_match.group(1))
                    total_installments = int(installment_match.group(2))

                    if 0 < current_installment < total_installments <= 60:
                        remaining = total_installments - current_installment
                        for i in range(1, remaining + 1):
                            next_date = date_val + relativedelta(months=i)
                            next_installment = current_installment + i
                            new_desc = description.replace(
                                f'{current_installment:02d}/{total_installments:02d}',
                                f'{next_installment:02d}/{total_installments:02d}'
                            ).replace(
                                f'{current_installment}/{total_installments}',
                                f'{next_installment}/{total_installments}'
                            )

                            create_transaction_deduplicated(
                                invoice=invoice,
                                date=next_date,
                                description=new_desc.strip(),
                                amount=amount_val,
                                is_predicted=True
                            )
                            predictions_created += 1
        except Exception: continue

    # Lógica Inteligente de Pagamentos
    if payments:
        from django.db.models import Sum
        from datetime import date
        
        # 1. Tentar encontrar a fatura do mês anterior
        prev_month_date = date(invoice.year, invoice.month, 1) - relativedelta(months=1)
        prev_invoice = Invoice.objects.filter(
            user=invoice.user,
            credit_card=invoice.credit_card,
            year=prev_month_date.year,
            month=prev_month_date.month
        ).first()

        target_to_ignore = None
        
        if prev_invoice:
            # Se existe fatura anterior, o pagamento que "casa" com o total dela é o que ignoramos
            prev_total = Transaction.objects.filter(invoice=prev_invoice).aggregate(Sum('amount'))['amount__sum'] or 0
            if prev_total > 0:
                # Encontrar o pagamento mais próximo do valor da fatura anterior (em valor absoluto)
                target_to_ignore = min(payments, key=lambda p: abs(abs(p[2]) - prev_total))
        
        if not target_to_ignore:
            # 2. Se não houver fatura anterior ou não bateu o valor, ignoramos o de maior valor (pagamento da fatura)
            target_to_ignore = min(payments, key=lambda p: p[2]) # p[2] é negativo, então min() pega o mais negativo

        # Adicionar os demais como pagamentos antecipados (reduzem o total)
        for p_date, p_desc, p_amount in payments:
            if (p_date, p_desc, p_amount) == target_to_ignore:
                target_to_ignore = None # Ignora apenas uma ocorrência
                continue
            
            # Criar como transação real (negativa)
            create_transaction_deduplicated(
                invoice=invoice,
                date=p_date,
                description=f"{p_desc.strip()} (Antecipado)",
                amount=p_amount,
                is_predicted=False
            )
            transactions_created += 1

    return transactions_created, predictions_created

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
    """Agrupa transações por mês de referência da fatura e por cartão para gráfico temporal empilhado"""
    from django.db.models import Sum
    from collections import defaultdict

    if transactions is None:
        transactions = Transaction.objects.all()

    MONTH_ABBR = {
        1: 'jan', 2: 'fev', 3: 'mar', 4: 'abr',
        5: 'mai', 6: 'jun', 7: 'jul', 8: 'ago',
        9: 'set', 10: 'out', 11: 'nov', 12: 'dez'
    }

    # Buscar transações com dados da invoice (select_related para evitar N+1)
    transactions = transactions.select_related('invoice__credit_card')

    # Calcular display_month em Python: 
    # - Para previstos: usa date.month/year
    # - Para reais: usa invoice.month/year (mês de referência da fatura)
    month_data = defaultdict(lambda: defaultdict(float))
    cards_info = defaultdict(lambda: {'color': '#667eea'})
    month_keys_set = set()

    for trans in transactions:
        if trans.is_predicted:
            # Previsto: usa a data real da parcela
            display_year = trans.date.year
            display_month = trans.date.month
        else:
            # Real: usa o mês de referência da fatura
            if trans.invoice:
                display_year = trans.invoice.year or trans.date.year
                display_month = trans.invoice.month or trans.date.month
            else:
                display_year = trans.date.year
                display_month = trans.date.month

        month_key = (display_year, display_month)
        month_keys_set.add(month_key)

        card_name = trans.invoice.credit_card.name if trans.invoice and trans.invoice.credit_card else 'Sem Cartão'
        card_color = trans.invoice.credit_card.color if trans.invoice and trans.invoice.credit_card else '#9ca3af'

        month_data[month_key][card_name] += float(trans.amount)
        cards_info[card_name] = {'color': card_color}

    # Ordenar meses
    month_keys = sorted(month_keys_set)
    labels = [f"{MONTH_ABBR.get(m[1], '?')}/{m[0]}" for m in month_keys]

    # Montar datasets
    datasets = []
    for card_name, info in cards_info.items():
        data = [month_data[m].get(card_name, 0) for m in month_keys]
        total = sum(data)
        datasets.append({
            'label': card_name,
            'data': data,
            'color': info['color'],
            'total': total
        })

    datasets.sort(key=lambda x: x['total'])

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
