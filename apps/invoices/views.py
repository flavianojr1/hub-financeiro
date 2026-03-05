from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.db import IntegrityError
from .models import Invoice, Transaction, Category, CategoryRule, CreditCard
from .forms import CSVUploadForm, CategoryForm, CategoryRuleForm, CreditCardForm
from .utils import (
    process_nubank_csv, 
    process_inter_pdf, 
    get_temporal_data, 
    get_category_data, 
    recategorize_user_transactions
)

MONTH_NAMES = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}



@login_required
def dashboard(request):
    """View principal do dashboard com filtro por mês"""
    all_transactions = Transaction.objects.filter(invoice__user=request.user)
    
    selected_card = request.GET.get('card')
    if selected_card:
        try:
            int_card = int(selected_card)
            all_transactions = all_transactions.filter(invoice__credit_card_id=int_card)
        except ValueError:
            selected_card = None
    
    credit_cards = CreditCard.objects.filter(user=request.user)

    # Resumo mensal: todos os meses com transações, em ordem crescente
    from datetime import date
    today = date.today()
    current_month_key = f"{today.year}-{today.month:02d}"

    monthly_summary = (
        all_transactions
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            total_transactions=Count('id'),
            total_amount=Sum('amount')
        )
        .order_by('month')
    )

    # Formatar resumo mensal com nomes legíveis
    monthly_list = []
    for item in monthly_summary:
        m = item['month']
        month_key = f"{m.year}-{m.month:02d}"
        monthly_list.append({
            'key': month_key,
            'label': f"{MONTH_NAMES.get(m.month, '?')}/{m.year}",
            'year': m.year,
            'month': m.month,
            'total_transactions': item['total_transactions'],
            'total_amount': item['total_amount'] or 0,
            'is_current': month_key == current_month_key,
        })

    # Todos os meses disponíveis para o dropdown (sem filtro de data)
    all_months_qs = (
        all_transactions
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    all_months = []
    for item in all_months_qs:
        m = item['month']
        month_key = f"{m.year}-{m.month:02d}"
        all_months.append({
            'key': month_key,
            'label': f"{MONTH_NAMES.get(m.month, '?')}/{m.year}",
        })

    # Verificar se há filtro de mês ativo
    selected_month = request.GET.get('month')  # formato: "2026-01"
    filtered = False

    if selected_month:
        try:
            parts = selected_month.split('-')
            filter_year = int(parts[0])
            filter_month = int(parts[1])
            transactions = all_transactions.filter(date__year=filter_year, date__month=filter_month)
            filtered = True
            selected_label = f"{MONTH_NAMES.get(filter_month, '?')}/{filter_year}"
        except (ValueError, IndexError):
            transactions = all_transactions
            selected_month = None
    else:
        transactions = all_transactions
        selected_label = None

    # Estatísticas (filtradas ou globais)
    total_amount = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    total_transactions = transactions.count()
    
    # Estatísticas do mês atual (para KPIs fixos)
    current_month_transactions = all_transactions.filter(
        date__year=today.year, 
        date__month=today.month
    )
    current_month_amount = current_month_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    current_month_count = current_month_transactions.count()
    
    stats = {
        'total_transactions': total_transactions,
        'total_amount': total_amount,
        'total_invoices': Invoice.objects.filter(user=request.user).count(),
        'avg_amount': total_amount / total_transactions if total_transactions > 0 else 0,
    }
    
    # KPIs do mês atual (mostrados independentemente do filtro)
    stats_current_month = {
        'total_transactions': current_month_count,
        'total_amount': current_month_amount,
    }

    context = {
        'stats': stats,
        'stats_current_month': stats_current_month,
        'monthly_list': monthly_list,
        'all_months': all_months,
        'filtered': filtered,
        'selected_month': selected_month,
        'selected_label': selected_label,
        'credit_cards': credit_cards,
        'selected_card': int(selected_card) if selected_card else None,
    }

    # Se filtrado, incluir lista de transações do mês
    if filtered:
        context['transactions'] = transactions.order_by('date', 'description')

    return render(request, 'invoices/dashboard.html', context)



@login_required
def upload_invoice(request):
    """View para upload de fatura (CSV ou PDF)"""
    has_cards = CreditCard.objects.filter(user=request.user).exists()

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES, user=request.user, upload_mode=True)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            credit_card = form.cleaned_data.get('credit_card')

            # Criar invoice
            invoice = Invoice.objects.create(
                user=request.user,
                credit_card=credit_card,
                filename=csv_file.name
            )

            # Processar arquivo baseado na extensão
            try:
                # Obter período confirmado pelo usuário (sobreposição)
                target_month = form.cleaned_data.get('target_month')
                target_year = form.cleaned_data.get('target_year')

                extension = csv_file.name.lower().split('.')[-1]
                if extension == 'pdf':
                    created, predicted = process_inter_pdf(csv_file, invoice)
                else:
                    created, predicted = process_nubank_csv(csv_file, invoice)
                
                # Aplicar sobreposição de período se o usuário confirmou no modal
                if target_month and target_year:
                    orig_month = invoice.month
                    orig_year = invoice.year
                    
                    invoice.month = target_month
                    invoice.year = target_year
                    invoice.save()
                    
                    # Calcular o deslocamento de meses entre o detectado e o confirmado
                    from dateutil.relativedelta import relativedelta
                    delta_months = (int(target_year) - int(orig_year)) * 12 + (int(target_month) - int(orig_month))
                    
                    if delta_months != 0:
                        # Deslocar TODAS as transações (reais e previstas) proporcionalmente
                        for trans in invoice.transactions.all():
                            trans.date = trans.date + relativedelta(months=delta_months)
                            trans.save()

                msg = f'✅ Fatura processada! {created} transações importadas.'
                if predicted > 0:
                    msg += f' 🔮 {predicted} parcelas futuras geradas.'
                messages.success(request, msg)
                return redirect('dashboard')
            except Exception as e:
                invoice.delete()
                messages.error(
                    request,
                    f'❌ Erro ao processar arquivo: {str(e)}'
                )
    else:
        form = CSVUploadForm(user=request.user, upload_mode=True)

    return render(request, 'invoices/upload.html', {'form': form, 'has_cards': has_cards})



@login_required
def invoice_list(request):
    """View para listar e gerenciar faturas"""
    invoices = Invoice.objects.filter(user=request.user).select_related('credit_card').annotate(
        transaction_count=Count('transactions'),
        total_amount=Sum('transactions__amount')
    )

    context = {
        'invoices': invoices,
    }

    return render(request, 'invoices/invoice_list.html', context)



@login_required
def invoice_delete(request, pk):
    """Deletar uma fatura e todas suas transações"""
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    if request.method == 'POST':
        name = invoice.period_display
        invoice.delete()
        messages.success(request, f'🗑️ Fatura "{name}" deletada com sucesso.')
    return redirect('invoice_list')


@login_required
def invoice_update(request, pk):
    """View para atualizar uma fatura existente (substituindo-a por um novo arquivo)"""
    old_invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            credit_card = form.cleaned_data.get('credit_card')

            # Criar nova invoice antes de deletar a antiga em caso de erro
            new_invoice = Invoice.objects.create(
                user=request.user,
                credit_card=credit_card,
                filename=csv_file.name
            )

            try:
                extension = csv_file.name.lower().split('.')[-1]
                if extension == 'pdf':
                    created, predicted = process_inter_pdf(csv_file, new_invoice)
                else:
                    created, predicted = process_nubank_csv(csv_file, new_invoice)
                
                # Sucesso: deletar a antiga e mostrar mensagem
                old_name = old_invoice.period_display
                old_invoice.delete()
                
                msg = f'✅ Fatura "{old_name}" atualizada com sucesso! {created} transações importadas.'
                if predicted > 0:
                    msg += f' 🔮 {predicted} parcelas futuras geradas.'
                messages.success(request, msg)
                return redirect('invoice_list')
                
            except Exception as e:
                new_invoice.delete()
                messages.error(
                    request,
                    f'❌ Erro ao atualizar fatura: {str(e)}'
                )
    else:
        # Pre-selecionar o cartão da fatura antiga, se houver
        initial_data = {}
        if old_invoice.credit_card:
            initial_data['credit_card'] = old_invoice.credit_card
        form = CSVUploadForm(user=request.user, initial=initial_data)

    return render(request, 'invoices/invoice_update.html', {'form': form, 'invoice': old_invoice})



@login_required
def category_manage(request):
    """View para gerenciar categorias e regras"""
    categories = Category.objects.filter(user=request.user).prefetch_related('rules')
    rules = CategoryRule.objects.filter(user=request.user).select_related('category')
    
    # Buscar transações não categorizadas (Outros) para sugestão rápida
    # Filtrar por usuário via invoice
    uncategorized_transactions = Transaction.objects.filter(
        invoice__user=request.user, 
        category='Outros'
    ).order_by('-date')

    # Forms
    category_form = CategoryForm()
    rule_form = CategoryRuleForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_category':
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                cat = category_form.save(commit=False)
                cat.user = request.user
                cat.save()
                messages.success(request, '✅ Categoria criada com sucesso!')
                return redirect('category_manage')

        elif action == 'add_rule':
            rule_form = CategoryRuleForm(request.POST)
            if rule_form.is_valid():
                rule = rule_form.save(commit=False)
                rule.user = request.user
                rule.save()
                count = recategorize_user_transactions(request.user)
                messages.success(request, f'✅ Regra criada! {count} transações recategorizadas.')
                return redirect('category_manage')

        elif action == 'delete_category':
            cat_id = request.POST.get('category_id')
            cat = get_object_or_404(Category, pk=cat_id, user=request.user)
            cat.delete()
            messages.success(request, '🗑️ Categoria deletada.')
            return redirect('category_manage')

        elif action == 'delete_rule':
            rule_id = request.POST.get('rule_id')
            rule = get_object_or_404(CategoryRule, pk=rule_id, user=request.user)
            rule.delete()
            count = recategorize_user_transactions(request.user)
            messages.success(request, f'🗑️ Regra deletada. {count} transações recategorizadas.')
            return redirect('category_manage')

        elif action == 'quick_rule':
            keyword = request.POST.get('keyword', '').strip()
            category_id = request.POST.get('category_id')
            
            if keyword and category_id:
                category = get_object_or_404(Category, pk=category_id, user=request.user)
                # Criar a regra
                CategoryRule.objects.get_or_create(
                    keyword=keyword, 
                    category=category,
                    defaults={'user': request.user}
                )
                # Reaplicar regras
                count = recategorize_user_transactions(request.user)
                messages.success(request, f'✅ Regra criada para "{keyword}"! {count} transações recategorizadas.')
            return redirect('category_manage')

        elif action == 'recategorize':
            count = recategorize_user_transactions(request.user)
            messages.success(request, f'🔄 {count} transações recategorizadas com as novas regras!')
            return redirect('category_manage')

    context = {
        'categories': categories,
        'rules': rules,
        'category_form': category_form,
        'category_form': category_form,
        'rule_form': rule_form,
        'uncategorized_transactions': uncategorized_transactions,
    }

    return render(request, 'invoices/category_manage.html', context)



@login_required
def get_chart_data(request):
    """API para retornar dados dos gráficos em JSON"""
    from datetime import date
    today = date.today()
    
    transactions = Transaction.objects.filter(invoice__user=request.user)

    selected_card = request.GET.get('card')
    if selected_card:
        try:
            transactions = transactions.filter(invoice__credit_card_id=int(selected_card))
        except ValueError:
            pass

    selected_month = request.GET.get('month')

    # Se não há mês selecionado, usar mês atual
    if not selected_month:
        target_year = today.year
        target_month = today.month
    else:
        try:
            parts = selected_month.split('-')
            target_year = int(parts[0])
            target_month = int(parts[1])
        except (ValueError, IndexError):
            target_year = today.year
            target_month = today.month

    # Categorias filtradas pelo mês (atual ou selecionado)
    category_transactions = transactions.filter(date__year=target_year, date__month=target_month)
    category = get_category_data(category_transactions)

    # Temporal sempre mostra todos os dados (global)
    temporal = get_temporal_data(transactions)
    
    result = {'category': category, 'temporal': temporal, 'filtered': bool(selected_month)}

    return JsonResponse(result)


@login_required
def get_stats_data(request):
    """API para retornar KPIs do mês filtrado ou atual em JSON"""
    all_transactions = Transaction.objects.filter(invoice__user=request.user)
    
    selected_card = request.GET.get('card')
    if selected_card:
        try:
            int_card = int(selected_card)
            all_transactions = all_transactions.filter(invoice__credit_card_id=int_card)
        except ValueError:
            pass
    
    from datetime import date
    today = date.today()
    
    selected_month = request.GET.get('month')
    
    if selected_month:
        try:
            parts = selected_month.split('-')
            filter_year = int(parts[0])
            filter_month = int(parts[1])
            target_year = filter_year
            target_month = filter_month
        except (ValueError, IndexError):
            target_year = today.year
            target_month = today.month
    else:
        target_year = today.year
        target_month = today.month
    
    # KPIs do mês alvo (filtrado ou atual)
    target_month_transactions = all_transactions.filter(
        date__year=target_year, 
        date__month=target_month
    )
    target_month_amount = target_month_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    target_month_count = target_month_transactions.count()
    
    # KPIs globais (para média)
    total_amount = all_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    total_transactions = all_transactions.count()
    
    result = {
        'total_transactions': target_month_count,
        'total_amount': float(target_month_amount),
        'avg_amount': float(total_amount / total_transactions) if total_transactions > 0 else 0,
    }
    
    return JsonResponse(result)


@login_required
def get_transactions_data(request):
    """API para retornar lista de transações filtradas por mês e cartão"""
    transactions = Transaction.objects.filter(invoice__user=request.user)

    selected_card = request.GET.get('card')
    if selected_card:
        try:
            transactions = transactions.filter(invoice__credit_card_id=int(selected_card))
        except ValueError:
            pass

    selected_month = request.GET.get('month')
    if selected_month:
        try:
            parts = selected_month.split('-')
            filter_year = int(parts[0])
            filter_month = int(parts[1])
            transactions = transactions.filter(date__year=filter_year, date__month=filter_month)
        except (ValueError, IndexError):
            pass

    transactions_list = transactions.order_by('-date', 'description').values(
        'date', 'description', 'amount'
    )

    result = {
        'transactions': [
            {
                'date': t['date'].strftime('%d/%m') if t['date'] else '',
                'description': t['description'] or '',
                'amount': float(t['amount']) if t['amount'] else 0
            }
            for t in transactions_list
        ]
    }

    return JsonResponse(result)


@login_required
def card_manage(request):
    """View para gerenciar cartões de crédito"""
    cards = CreditCard.objects.filter(user=request.user)
    form = CreditCardForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_card':
            form = CreditCardForm(request.POST)
            if form.is_valid():
                card = form.save(commit=False)
                card.user = request.user
                try:
                    card.save()
                    messages.success(request, '✅ Cartão adicionado com sucesso!')
                    return redirect('card_manage')
                except IntegrityError:
                    messages.error(request, f'❌ Erro: Você já possui um cartão cadastrado com o nome "{card.name}".')

        elif action == 'delete_card':
            card_id = request.POST.get('card_id')
            card = get_object_or_404(CreditCard, pk=card_id, user=request.user)
            card.delete()
            messages.success(request, '🗑️ Cartão deletado com sucesso. As faturas e transações atreladas também foram apagadas.')
            return redirect('card_manage')

        elif action == 'rename_card':
            card_id = request.POST.get('card_id')
            new_name = request.POST.get('new_name', '').strip()
            if new_name:
                card = get_object_or_404(CreditCard, pk=card_id, user=request.user)
                old_name = card.name
                card.name = new_name
                try:
                    card.save()
                    messages.success(request, f'✅ Cartão "{old_name}" renomeado para "{new_name}".')
                except IntegrityError:
                    messages.error(request, f'❌ Erro: Você já possui um cartão chamado "{new_name}".')
            return redirect('card_manage')

    context = {
        'cards': cards,
        'form': form,
    }

    return render(request, 'invoices/card_manage.html', context)
