from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from django.db import IntegrityError
import os
import requests
from datetime import date
import calendar
from .models import Invoice, Transaction, Category, CategoryRule, CreditCard, Income, PixBoleto
from .forms import CSVUploadForm, CategoryForm, CategoryRuleForm, CreditCardForm, IncomeForm, PixBoletoForm
from .utils import (
    process_nubank_csv, 
    process_inter_pdf, 
    get_temporal_data, 
    get_category_data, 
    recategorize_user_transactions,
    get_financial_context
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

    # Encontrar a última fatura uploadada (maior ano/mês)
    last_invoice = (
        Invoice.objects.filter(user=request.user)
        .exclude(year__isnull=True, month__isnull=True)
        .order_by('-year', '-month')
        .first()
    )
    
    # Data de corte para previsões: último dia do mês da última fatura
    from datetime import date
    import calendar
    
    if last_invoice:
        last_day = calendar.monthrange(last_invoice.year, last_invoice.month)[1]
        prediction_cutoff_date = date(last_invoice.year, last_invoice.month, last_day)
    else:
        prediction_cutoff_date = None

    # Agrupar transações com base na última fatura uploadada
    from collections import defaultdict
    monthly_data = defaultdict(lambda: {'transactions': 0, 'amount': 0})
    
    all_transactions_with_invoice = all_transactions.select_related('invoice')
    
    for trans in all_transactions_with_invoice:
        trans_month = None
        
        # Sempre incluir transações REAIS no mês de referência da fatura
        if not trans.is_predicted:
            if trans.invoice and trans.invoice.year and trans.invoice.month:
                trans_month = (trans.invoice.year, trans.invoice.month)
            else:
                trans_month = (trans.date.year, trans.date.month)
        else:
            # Transações PREVISTAS: incluir apenas se forem posteriores à última fatura real
            if prediction_cutoff_date and trans.date > prediction_cutoff_date:
                trans_month = (trans.date.year, trans.date.month)
            elif not prediction_cutoff_date:
                # Se não há faturas reais, mostra todas as previsões (ex: entradas manuais futuras)
                trans_month = (trans.date.year, trans.date.month)
        
        if trans_month:
            monthly_data[trans_month]['transactions'] += 1
            monthly_data[trans_month]['amount'] += float(trans.amount) if trans.amount else 0

    # Ordenar e formatar
    sorted_months = sorted(monthly_data.keys())
    monthly_list = []
    for year, month in sorted_months:
        month_key = f"{year}-{month:02d}"
        monthly_list.append({
            'key': month_key,
            'label': f"{MONTH_NAMES.get(month, '?')}/{year}",
            'year': year,
            'month': month,
            'total_transactions': monthly_data[(year, month)]['transactions'],
            'total_amount': monthly_data[(year, month)]['amount'],
            'is_current': month_key == current_month_key,
        })

    # Todos os meses disponíveis para o dropdown (usando dados já calculados)
    all_months = [{'key': m['key'], 'label': m['label']} for m in monthly_list]

    # Verificar se há filtro de mês ativo
    selected_month = request.GET.get('month')  # formato: "2026-01"
    filtered = False

    if selected_month:
        try:
            parts = selected_month.split('-')
            filter_year = int(parts[0])
            filter_month = int(parts[1])
            # Filtro híbrido: reais usam invoice.month/year, previstos usam date
            transactions = all_transactions.filter(
                Q(is_predicted=False, invoice__year=filter_year, invoice__month=filter_month) |
                Q(is_predicted=True, date__year=filter_year, date__month=filter_month)
            )
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
    
    # Estatísticas do mês atual (para KPIs fixos) - filtro híbrido
    current_month_transactions = all_transactions.filter(
        Q(is_predicted=False, invoice__year=today.year, invoice__month=today.month) |
        Q(is_predicted=True, date__year=today.year, date__month=today.month)
    )
    current_month_amount = current_month_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    current_month_count = current_month_transactions.count()
    
    # Soma das parcelas do mês atual
    current_installments_sum = current_month_transactions.filter(
        description__icontains='Parcela'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    stats = {
        'total_transactions': total_transactions,
        'total_amount': total_amount,
        'total_invoices': Invoice.objects.filter(user=request.user).count(),
        'avg_amount': current_installments_sum,
    }
    
    # KPIs do mês atual (mostrados independentemente do filtro)
    stats_current_month = {
        'total_transactions': current_month_count,
        'total_amount': current_month_amount,
    }

    # Incomes (Entradas)
    all_incomes = Income.objects.filter(user=request.user)
    all_pix_boletos = PixBoleto.objects.filter(user=request.user)

    if selected_month:
        try:
            parts = selected_month.split('-')
            filter_year = int(parts[0])
            filter_month = int(parts[1])
            month_incomes = all_incomes.filter(date__year=filter_year, date__month=filter_month)
            month_pix_boletos = all_pix_boletos.filter(date__year=filter_year, date__month=filter_month)
        except:
            month_incomes = all_incomes.filter(date__year=today.year, date__month=today.month)
            month_pix_boletos = all_pix_boletos.filter(date__year=today.year, date__month=today.month)
    else:
        month_incomes = all_incomes.filter(date__year=today.year, date__month=today.month)
        month_pix_boletos = all_pix_boletos.filter(date__year=today.year, date__month=today.month)
        
    total_income = month_incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    total_pix_boleto = month_pix_boletos.aggregate(Sum('amount'))['amount__sum'] or 0

    # Se filtrado, usa total_amount do filtro. Se não, usa do mês atual para o balanço.
    current_or_filtered_amount = total_amount if filtered else current_month_amount
    balance = total_income - current_or_filtered_amount - total_pix_boleto

    has_any_data = all_transactions.exists() or all_incomes.exists() or all_pix_boletos.exists()

    context = {
        'stats': stats,
        'stats_current_month': stats_current_month,
        'total_income': total_income,
        'total_pix_boleto': total_pix_boleto,
        'balance': balance,
        'has_any_data': has_any_data,
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
def chat_view(request):
    """View para o chat com o Consultor AI usando a API da NVIDIA e Memória de Sessão"""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            if not user_message:
                return JsonResponse({'status': 'error', 'message': 'Mensagem vazia'}, status=400)

            # 1. Gerenciar Histórico de Chat (Memória na Sessão)
            if 'chat_history' not in request.session:
                request.session['chat_history'] = []
            
            chat_history = request.session['chat_history']

            # 2. Obter Contexto Financeiro Real
            financial_context = get_financial_context(request.user)

            # 3. Configurar Chamada para NVIDIA
            api_key = os.getenv('NVIDIA_API_KEY')
            invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
            
            from datetime import datetime
            today_str = datetime.now().strftime('%d/%m/%Y')
            current_month_name = MONTH_NAMES.get(datetime.now().month)

            system_prompt = (
                "Você é o 'Consultor Hub Financeiro', um assistente especialista em finanças pessoais. "
                f"HOJE É DIA {today_str} ({current_month_name}).\n\n"
                "REGRAS DE FORMATAÇÃO (MUITO IMPORTANTES):\n"
                "1. Para que suas tabelas apareçam corretamente, você DEVE SEMPRE colocar DUAS QUEBRAS DE LINHA (pressionar Enter duas vezes) antes de começar uma tabela.\n"
                "2. Nunca escreva texto grudado no topo de uma tabela.\n"
                "3. Use Markdown para negrito e listas.\n\n"
                "REGRAS DE DADOS:\n"
                "1. Baseie-se SEMPRE nos DADOS REAIS abaixo.\n"
                "2. Mantenha o contexto da conversa anterior.\n\n"
                f"{financial_context}"
            )

            # Montar a lista de mensagens (System + Histórico + Pergunta Atual)
            messages = [{"role": "system", "content": system_prompt}]
            
            # Adiciona as últimas 6 mensagens do histórico para não estourar o contexto
            for msg in chat_history[-6:]:
                messages.append(msg)
            
            # Adiciona a pergunta atual
            messages.append({"role": "user", "content": user_message})

            payload = {
                "model": "mistralai/mistral-small-4-119b-2603",
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.2,
                "top_p": 0.7,
                "stream": False
            }

            response = requests.post(
                invoke_url, 
                headers={
                    "Authorization": f"Bearer {api_key}", 
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }, 
                json=payload, 
                timeout=45
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
                # 4. Atualizar Histórico na Sessão
                chat_history.append({"role": "user", "content": user_message})
                chat_history.append({"role": "assistant", "content": ai_response})
                request.session['chat_history'] = chat_history[-10:] # Mantém apenas as últimas 10
                request.session.modified = True
                
                return JsonResponse({'status': 'success', 'response': ai_response})
            else:
                return JsonResponse({'status': 'error', 'message': f'Erro API: {response.status_code}'}, status=500)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # GET: Limpa o histórico ao recarregar a página (opcional, para começar conversa nova)
    if 'chat_history' in request.session:
        del request.session['chat_history']
    
    return render(request, 'invoices/chat.html', {'topbar_title': 'Consultor AI'})


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
                    created, predicted = process_inter_pdf(
                        csv_file, invoice, 
                        target_month=target_month, 
                        target_year=target_year
                    )
                else:
                    created, predicted = process_nubank_csv(
                        csv_file, invoice,
                        target_month=target_month,
                        target_year=target_year
                    )
                
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
                # Obter período confirmado pelo usuário (sobreposição)
                target_month = form.cleaned_data.get('target_month')
                target_year = form.cleaned_data.get('target_year')

                extension = csv_file.name.lower().split('.')[-1]
                if extension == 'pdf':
                    created, predicted = process_inter_pdf(
                        csv_file, new_invoice,
                        target_month=target_month,
                        target_year=target_year
                    )
                else:
                    created, predicted = process_nubank_csv(
                        csv_file, new_invoice,
                        target_month=target_month,
                        target_year=target_year
                    )
                
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
    categories = Category.objects.filter(user=request.user, type='expense').prefetch_related('rules')
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

    # Categorias filtradas pelo mês (atual ou selecionado) - filtro híbrido
    category_transactions = transactions.filter(
        Q(is_predicted=False, invoice__year=target_year, invoice__month=target_month) |
        Q(is_predicted=True, date__year=target_year, date__month=target_month)
    )

    # Encontrar a última fatura uploadada para filtrar previstas corretamente
    last_invoice = (
        Invoice.objects.filter(user=request.user)
        .exclude(year__isnull=True, month__isnull=True)
        .order_by('-year', '-month')
        .first()
    )
    
    import calendar
    if last_invoice:
        last_day = calendar.monthrange(last_invoice.year, last_invoice.month)[1]
        prediction_cutoff_date = date(last_invoice.year, last_invoice.month, last_day)
    else:
        prediction_cutoff_date = None

    # Se houver data de corte, as previstas do mês só aparecem se forem posteriores a ela
    if prediction_cutoff_date:
        category_transactions = category_transactions.exclude(
            is_predicted=True,
            date__lte=prediction_cutoff_date
        )

    category = get_category_data(category_transactions)

    # Filtrar transações para o gráfico temporal:
    # - Reais: todas
    # - Previstas: apenas após a última fatura
    if prediction_cutoff_date:
        temporal_transactions = transactions.filter(
            Q(is_predicted=False) |
            Q(is_predicted=True, date__gt=prediction_cutoff_date)
        )
    else:
        temporal_transactions = transactions.filter(is_predicted=False)

    temporal = get_temporal_data(temporal_transactions)
    
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
    
    # KPIs do mês alvo (filtrado ou atual) - filtro híbrido
    target_month_transactions = all_transactions.filter(
        Q(is_predicted=False, invoice__year=target_year, invoice__month=target_month) |
        Q(is_predicted=True, date__year=target_year, date__month=target_month)
    )

    # Encontrar a última fatura uploadada para filtrar previstas corretamente
    last_invoice = (
        Invoice.objects.filter(user=request.user)
        .exclude(year__isnull=True, month__isnull=True)
        .order_by('-year', '-month')
        .first()
    )
    
    import calendar
    if last_invoice:
        last_day = calendar.monthrange(last_invoice.year, last_invoice.month)[1]
        prediction_cutoff_date = date(last_invoice.year, last_invoice.month, last_day)
        
        # Excluir previstas do mês que são anteriores ou iguais ao corte
        target_month_transactions = target_month_transactions.exclude(
            is_predicted=True,
            date__lte=prediction_cutoff_date
        )

    target_month_amount = target_month_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    target_month_count = target_month_transactions.count()
    
    # Soma das parcelas do mês
    installments_sum = target_month_transactions.filter(
        description__icontains='Parcela'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # KPIs globais (para média)
    total_amount = all_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    total_transactions = all_transactions.count()
    
    # Incomes
    month_incomes = Income.objects.filter(
        user=request.user, 
        date__year=target_year, 
        date__month=target_month
    )
    total_income = month_incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - target_month_amount

    result = {
        'total_transactions': target_month_count,
        'total_amount': float(target_month_amount),
        'avg_amount': float(installments_sum),
        'total_income': float(total_income),
        'balance': float(balance),
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
            # Filtro híbrido: reais usam invoice.month/year, previstos usam date
            transactions = transactions.filter(
                Q(is_predicted=False, invoice__year=filter_year, invoice__month=filter_month) |
                Q(is_predicted=True, date__year=filter_year, date__month=filter_month)
            )
        except (ValueError, IndexError):
            pass

    # Encontrar a última fatura uploadada para filtrar previstas corretamente
    last_invoice = (
        Invoice.objects.filter(user=request.user)
        .exclude(year__isnull=True, month__isnull=True)
        .order_by('-year', '-month')
        .first()
    )
    
    import calendar
    if last_invoice:
        last_day = calendar.monthrange(last_invoice.year, last_invoice.month)[1]
        prediction_cutoff_date = date(last_invoice.year, last_invoice.month, last_day)
        
        # Excluir previstas da lista que são anteriores ou iguais ao corte
        transactions = transactions.exclude(
            is_predicted=True,
            date__lte=prediction_cutoff_date
        )

    sort_field = request.GET.get('sort', 'date')
    sort_order = request.GET.get('order', 'desc')
    
    valid_fields = {'date', 'description', 'category', 'amount', 'card'}
    if sort_field not in valid_fields:
        sort_field = 'date'
    
    # Mapear campo de ordenação 'card' para o relacionamento correto
    db_sort_field = sort_field
    if sort_field == 'card':
        db_sort_field = 'invoice__credit_card__name'
    
    order_prefix = '-' if sort_order == 'desc' else ''
    transactions_list = transactions.select_related('invoice__credit_card').order_by(f'{order_prefix}{db_sort_field}', 'description')
    
    from apps.invoices.models import Category
    category_names = set(t.category for t in transactions_list if t.category)
    category_colors = {}
    for cat_name in category_names:
        cat = Category.objects.filter(name=cat_name).first()
        if cat:
            category_colors[cat_name] = cat.color

    result = {
        'transactions': [
            {
                'date': t.date.strftime('%d/%m') if t.date else '',
                'description': t.description or '',
                'amount': float(t.amount) if t.amount else 0,
                'category': t.category or 'Outros',
                'category_color': category_colors.get(t.category or 'Outros', '#6b7280'),
                'card_name': t.invoice.credit_card.name if t.invoice and t.invoice.credit_card else 'N/A',
                'card_color': t.invoice.credit_card.color if t.invoice and t.invoice.credit_card else '#6b7280'
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


@login_required
def income_manage(request):
    """View para gerenciar entradas manuais (receitas)"""
    incomes = Income.objects.filter(user=request.user)
    
    # Categorias específicas de receitas
    income_categories = Category.objects.filter(user=request.user, type='income').prefetch_related('rules')
    income_rules = CategoryRule.objects.filter(user=request.user, category__type='income').select_related('category')
    
    # Criar mapping de categoria -> cor para usar no template
    category_color_map = {cat.name: cat.color for cat in income_categories}
    
    # Adicionar cor a cada income para uso no template
    for inc in incomes:
        inc.category_color = category_color_map.get(inc.category, '#10b981')
    
    form = IncomeForm()
    category_form = CategoryForm()
    rule_form = CategoryRuleForm()
    
    # Customizando o queryset do rule_form para só exibir categorias de 'income'
    rule_form.fields['category'].queryset = Category.objects.filter(user=request.user, type='income')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_income':
            form = IncomeForm(request.POST)
            if form.is_valid():
                income = form.save(commit=False)
                income.user = request.user
                
                if income.is_recurring:
                    import uuid
                    group_id = uuid.uuid4().hex
                    
                    # Gera a entrada atual + 11 meses para frente
                    from dateutil.relativedelta import relativedelta
                    for i in range(12):
                        Income.objects.create(
                            user=request.user,
                            description=income.description,
                            amount=income.amount,
                            date=income.date + relativedelta(months=i),
                            is_recurring=True,
                            recurring_group_id=group_id
                        )
                    messages.success(request, '✅ Entrada recorrente criada para os próximos 12 meses!')
                else:
                    income.save()
                    messages.success(request, '✅ Entrada adicionada com sucesso!')
                
                return redirect('income_manage')

        elif action == 'delete_income':
            income_id = request.POST.get('income_id')
            delete_all = request.POST.get('delete_all') == 'true'
            
            income = get_object_or_404(Income, pk=income_id, user=request.user)
            
            if delete_all and income.recurring_group_id:
                # Deletar a atual e todas as FUTURAS do mesmo grupo
                count, _ = Income.objects.filter(
                    user=request.user,
                    recurring_group_id=income.recurring_group_id,
                    date__gte=income.date
                ).delete()
                messages.success(request, f'🗑️ {count} entradas recorrentes deletadas.')
            else:
                income.delete()
                messages.success(request, '🗑️ Entrada deletada.')
                
            return redirect('income_manage')
            
        elif action == 'add_category':
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                cat = category_form.save(commit=False)
                cat.user = request.user
                cat.type = 'income' # Força o tipo como receita
                cat.save()
                messages.success(request, '✅ Categoria de entrada criada!')
                return redirect('income_manage')

        elif action == 'add_rule':
            rule_form = CategoryRuleForm(request.POST)
            # Re-aplica queryset para validação passar
            rule_form.fields['category'].queryset = Category.objects.filter(user=request.user, type='income')
            
            if rule_form.is_valid():
                rule = rule_form.save(commit=False)
                rule.user = request.user
                rule.save()
                
                # Re-categoriza silenciosamente apenas entradas
                incomes_to_update = Income.objects.filter(user=request.user)
                for inc in incomes_to_update:
                    new_cat = inc.auto_categorize()
                    if new_cat != inc.category:
                        inc.category = new_cat
                        inc.save()
                        
                messages.success(request, '✅ Regra criada com sucesso!')
                return redirect('income_manage')

        elif action == 'delete_category':
            cat_id = request.POST.get('category_id')
            cat = get_object_or_404(Category, pk=cat_id, user=request.user, type='income')
            cat.delete()
            messages.success(request, '🗑️ Categoria de entrada deletada.')
            return redirect('income_manage')

        elif action == 'delete_rule':
            rule_id = request.POST.get('rule_id')
            rule = get_object_or_404(CategoryRule, pk=rule_id, user=request.user, category__type='income')
            rule.delete()
            messages.success(request, '🗑️ Regra de entrada deletada.')
            return redirect('income_manage')

    context = {
        'incomes': incomes,
        'form': form,
        'category_form': category_form,
        'rule_form': rule_form,
        'income_categories': income_categories,
        'income_rules': income_rules,
    }

    return render(request, 'invoices/income_manage.html', context)


@login_required
def pix_boleto_manage(request):
    """View para gerenciar Pix e Boletos manuais (saídas fora do cartão)"""
    pix_boletos = PixBoleto.objects.filter(user=request.user)
    
    # Usa as mesmas categorias de despesa do cartão
    expense_categories = Category.objects.filter(user=request.user, type='expense')
    category_color_map = {cat.name: cat.color for cat in expense_categories}
    
    for pb in pix_boletos:
        pb.category_color = category_color_map.get(pb.category, '#ef4444')
    
    # Buscar Pix/Boletos não categorizados (Outros) para sugestão rápida
    uncategorized_pix_boletos = PixBoleto.objects.filter(
        user=request.user,
        category='Outros'
    ).order_by('-date')

    form = PixBoletoForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_pix_boleto':
            form = PixBoletoForm(request.POST)
            if form.is_valid():
                pb = form.save(commit=False)
                pb.user = request.user
                
                if pb.is_recurring:
                    import uuid
                    from dateutil.relativedelta import relativedelta
                    group_id = uuid.uuid4().hex
                    
                    # Gera a saída atual + 11 meses para frente
                    for i in range(12):
                        PixBoleto.objects.create(
                            user=request.user,
                            description=pb.description,
                            amount=pb.amount,
                            date=pb.date + relativedelta(months=i),
                            is_recurring=True,
                            recurring_group_id=group_id
                        )
                    messages.success(request, '✅ Lançamento recorrente criado para os próximos 12 meses!')
                else:
                    pb.save()
                    messages.success(request, '✅ Lançamento realizado com sucesso!')
                return redirect('pix_boleto_manage')

        elif action == 'delete_pix_boleto':
            pb_id = request.POST.get('pb_id')
            delete_all = request.POST.get('delete_all') == 'true'
            
            pb = get_object_or_404(PixBoleto, pk=pb_id, user=request.user)
            
            if delete_all and pb.recurring_group_id:
                # Deletar a atual e todas as FUTURAS do mesmo grupo
                count, _ = PixBoleto.objects.filter(
                    user=request.user,
                    recurring_group_id=pb.recurring_group_id,
                    date__gte=pb.date
                ).delete()
                messages.success(request, f'🗑️ {count} lançamentos recorrentes deletados.')
            else:
                pb.delete()
                messages.success(request, '🗑️ Lançamento deletado.')
            return redirect('pix_boleto_manage')

        elif action == 'update_pix_boleto':
            pb_id = request.POST.get('pb_id')
            description = request.POST.get('description')
            amount_str = request.POST.get('amount', '0').replace('.', '').replace(',', '.')
            date_str = request.POST.get('date')
            category_name = request.POST.get('category')

            try:
                from decimal import Decimal
                import datetime
                from django.http import JsonResponse
                
                pb = get_object_or_404(PixBoleto, id=pb_id, user=request.user)
                pb.description = description
                pb.amount = Decimal(amount_str)
                pb.date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                pb.category = category_name or 'Outros'
                pb.save()
                
                # Buscar a cor da categoria para o retorno
                category_obj = Category.objects.filter(user=request.user, name=pb.category, type='expense').first()
                category_color = category_obj.color if category_obj else '#ef4444'
                
                # Retornar dados formatados para o JS atualizar a tela sem reload
                return JsonResponse({
                    'status': 'success',
                    'message': '✅ Lançamento atualizado!',
                    'data': {
                        'description': pb.description,
                        'amount': f"{pb.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                        'date': pb.date.strftime('%d/%m/%Y'),
                        'category': pb.category,
                        'category_color': category_color,
                        'is_recurring': pb.is_recurring
                    }
                })
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f"❌ Erro: {str(e)}"}, status=400)


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
                # Reaplicar regras (agora afeta Transações e Pix/Boletos)
                count = recategorize_user_transactions(request.user)
                messages.success(request, f'✅ Regra criada para "{keyword}"! {count} lançamentos atualizados.')
            return redirect('pix_boleto_manage')

    context = {
        'pix_boletos': pix_boletos,
        'form': form,
        'expense_categories': expense_categories,
        'uncategorized_pix_boletos': uncategorized_pix_boletos,
    }

    return render(request, 'invoices/pix_boleto_manage.html', context)
