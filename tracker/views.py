import os
from unicodedata import category
from django.contrib import messages
from httpx import request
from .ml_utils import predict_category
from django.http import JsonResponse

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from tracker.models import Budget, Categories, Expense, Income
from decimal import Decimal, InvalidOperation
import calendar
from django.utils.timezone import datetime, now
from django.db.models import Sum
from .ml_utils import predict_category as ml_predict




months = [(i, calendar.month_name[i]) for i in range(1, 13)]

def get_month_year(request):
    month = request.GET.get("month")
    year = request.GET.get("year")

    try:
        month = int(month) if month else datetime.now().month
    except ValueError:
        month = datetime.now().month

    try:
        year = int(year) if year else datetime.now().year
    except ValueError:
        year = datetime.now().year

    # fix overflow
    if month > 12:
        month = 1
        year += 1
    if month < 1:
        month = 12
        year -= 1

    return month, year


# Create your views here.



@login_required(login_url='login')
def dashboard(request):

    today = now()

    month, year = get_month_year(request)

    month_name = calendar.month_name[month]

    # ---------------- TOTAL INCOME ----------------

    total_income = Income.objects.filter(
        user=request.user,
        date__month=month,
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ---------------- TOTAL EXPENSE ----------------

    total_expense = Expense.objects.filter(
        user=request.user,
        date__month=month,
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or 0

    balance = total_income - total_expense

    # ---------------- CATEGORY WISE ----------------

    expense_by_category = Expense.objects.filter(
        user=request.user,
        date__month=month,
        date__year=year
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    income_by_category = Income.objects.filter(
        user=request.user,
        date__month=month,
        date__year=year
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # ---------------- BUDGET OVERVIEW ----------------

    budget_data = Budget.objects.filter(
        user=request.user,
        month=month_name,
        year=year
    )

    budget_summary = []
    budget_warnings = []

    for budget in budget_data:

        actual = Expense.objects.filter(
            user=request.user,
            category=budget.category,
            date__month=month,
            date__year=year
        ).aggregate(total=Sum('amount'))['total'] or 0

        percentage = (actual / budget.amount * 100) if budget.amount > 0 else 0

        # progress bar max 100%
        display_percentage = min(percentage, 100)

        # warnings
        if percentage > 100:
            budget_warnings.append(f"{budget.category.name} budget exceeded!")
        elif percentage > 75:
            budget_warnings.append(f"{budget.category.name} budget almost finished")

        budget_summary.append({
            "category": budget.category.name,
            "budget_amount": budget.amount,
            "actual_amount": actual,
            "percentage": percentage,
            "display_percentage": display_percentage,
            "remaining": budget.amount - actual
        })

    # ---------------- EXPENSE > INCOME WARNING ----------------

    expense_income_warning = total_expense > total_income

    # ---------------- RECENT TRANSACTIONS ----------------

    recent_income = Income.objects.filter(
        user=request.user
    ).order_by('-date')[:5]

    recent_expense = Expense.objects.filter(
        user=request.user
    ).order_by('-date')[:5]

    recent_transactions = list(recent_income) + list(recent_expense)

    recent_transactions = sorted(
        recent_transactions,
        key=lambda x: x.date,
        reverse=True
    )[:5]

    transactions_count = (
        Income.objects.filter(user=request.user).count() +
        Expense.objects.filter(user=request.user).count()
    )

    # ---------------- MONTHLY GRAPH DATA ----------------

    months_data = []
    monthly_expense = []
    monthly_income = []

    for m in range(1, 13):

        months_data.append(calendar.month_abbr[m])


        total = Expense.objects.filter(
            user=request.user,
            date__month=m,
            date__year=year
        ).aggregate(total=Sum('amount'))['total'] or 0

        income_total = Income.objects.filter(
        user=request.user,
        date__month=m,
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or 0

        monthly_expense.append(total)
        monthly_income.append(income_total)

    # ---------------- FILTER OPTIONS ----------------

    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years = range(2023, 2031)

    # ---------------- CONTEXT ----------------

    context = {

        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,

        "selected_month": month,
        "selected_year": year,
        "month_name": month_name,

        "months": months,
        "years": years,

        "expense_by_category": expense_by_category,
        "income_by_category": income_by_category,

        "budget_summary": budget_summary,
        "budget_warnings": budget_warnings,

        "expense_income_warning": expense_income_warning,

        "recent_transactions": recent_transactions,
        "transactions_count": transactions_count,

        "months_data": months_data,
    "monthly_expense": monthly_expense,
    "monthly_income": monthly_income,

    }

    return render(request, "dashboard.html", context)


@login_required(login_url='login')
def add_category(request):
    if request.method == "POST":
        name = request.POST.get("name")
        type_value = request.POST.get("type")

        if not name or not type_value:
            messages.error(request, "All fields are required.")
            return redirect("add_category")

        Categories.objects.create(
            user=request.user,
            name=name,
            type=type_value
        )
        messages.success(request, "Category added successfully.")
        return redirect("view_category")  # change as needed

    return render(request, "add_category.html")

@login_required(login_url='login')
def add_budget(request):

    categories = Categories.objects.filter(
        user=request.user,
        type='expense'
    )

    if request.method == "POST":
        category_id = request.POST.get("category")
        month = request.POST.get("month")
        year = request.POST.get("year")
        amount = request.POST.get("amount")

        if not category_id or not month or not year or not amount:
            messages.error(request, "All fields are required.")
            return redirect("add_budget")

        try:
            year = int(year)
            amount = Decimal(amount)
        except (ValueError, InvalidOperation):
            messages.error(request, "Invalid year or amount.")
            return redirect("add_budget")

        category = get_object_or_404(
            Categories,
            id=category_id,
            user=request.user
        )

        # Duplicate check
        if Budget.objects.filter(
            user=request.user,
            category=category,
            month=month,
            year=year
        ).exists():
            messages.error(request, "Budget already exists for this category and month.")
            return redirect("add_budget")

        Budget.objects.create(
            user=request.user,
            category=category,
            month=month,
            year=year,
            amount=amount
        )

        messages.success(request, "Budget added successfully.")
        return redirect("view_budget")

    return render(request, "add_budget.html", {"categories": categories})


@login_required(login_url='login')
def add_income(request):

    # Only income type categories
    categories = Categories.objects.filter(
        user=request.user,
        type='income'
    )

    if request.method == "POST":
        category_id = request.POST.get("category")
        title = request.POST.get("title")
        amount = request.POST.get("amount")
        date = request.POST.get("date")
        description = request.POST.get("description")

        # Validation
        if not category_id or not title or not amount or not date:
            messages.error(request, "All required fields must be filled.")
            return redirect("add_income")

        try:
            amount = Decimal(amount)
        except InvalidOperation:
            messages.error(request, "Invalid amount value.")
            return redirect("add_income")

        # Secure category fetch
        category = get_object_or_404(
            Categories,
            id=category_id,
            user=request.user,
            type='income'
        )

        # Create income
        Income.objects.create(
            user=request.user,
            category=category,
            title=title,
            amount=amount,
            date=date,
            description=description
        )

        messages.success(request, "Income added successfully.")
        return redirect("view_income")

    return render(request, "add_income.html", {"categories": categories})

@login_required(login_url='login')
def add_expense(request):

    # Only expense type categories
    categories = Categories.objects.filter(
        user=request.user,
        type='expense'
    )

    if request.method == "POST":
        category_id = request.POST.get("category")
        title = request.POST.get("title")
        amount = request.POST.get("amount")
        date = request.POST.get("date")
        description = request.POST.get("description")

        # Validation
        if not category_id or not title or not amount or not date:
            messages.error(request, "All required fields must be filled.")
            return redirect("add_expense")

        try:
            amount = Decimal(amount)
        except InvalidOperation:
            messages.error(request, "Invalid amount value.")
            return redirect("add_expense")

        # Secure category fetch
        category = get_object_or_404(
            Categories,
            id=category_id,
            user=request.user,
            type='expense'
        )

        # Create expense
        Expense.objects.create(
            user=request.user,
            category=category,
            title=title,
            amount=amount,
            date=date,
            description=description
        )

        messages.success(request, "Expense added successfully.")
        return redirect("view_expense")

    return render(request, "add_expense.html", {"categories": categories})



@login_required(login_url='login')
def view_category(request):

    categories = Categories.objects.filter(user=request.user)

    search = request.GET.get('search')
    type_filter = request.GET.get('type')

    if search:
        categories = categories.filter(name__icontains=search)

    if type_filter:
        categories = categories.filter(type=type_filter)

    return render(request, "view_category.html", {
        "categories": categories
    })



@login_required(login_url='login')
def view_budget(request):

    month_num, year = get_month_year(request)
    month_name = calendar.month_name[month_num]

    budgets = Budget.objects.filter(user=request.user)
    categories = Categories.objects.filter(user=request.user, type='expense')

    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    # filters
    category = request.GET.get('category')
    month = request.GET.get('month')
    year_param = request.GET.get('year')

    # category filter
    if category:
        budgets = budgets.filter(category_id=int(category))

    # ✅ Month filter (REAL filtering)
    month_param = request.GET.get('month')

    if month_param is not None and month_param not in ["None"]:
        if month_param == "":
            # 🔥 ALL MONTHS
            month_num_filter = None
        else:
            # specific month
            month_num_filter = int(month_param)
            month_name_filter = calendar.month_name[month_num_filter]
            budgets = budgets.filter(month=month_name_filter)
    else:
        # 🔥 DEFAULT (no param) → CURRENT MONTH
        month_num_filter = month_num
        month_name_filter = calendar.month_name[month_num_filter]
        budgets = budgets.filter(month=month_name_filter)
        

    # ✅ Year filter (REAL filtering)
    if year_param and year_param not in ["", "None"]:
        try:
            year_filter = int(year_param)
        except ValueError:
            year_filter = year
    else:
        # 🔥 DEFAULT = CURRENT YEAR
        year_filter = year

    budgets = budgets.filter(year=year_filter)

    context = {
        "budgets": budgets,
        "categories": categories,
        "months": months,

        "selected_category": category,
        "selected_month": month_num_filter,
        "selected_year": year_filter,
        
        "month_name": calendar.month_name[month_num_filter] if month_num_filter else "All Months",
        
    }

    return render(request, "view_budget.html", context)

   

@login_required(login_url='login')
def view_income(request):

    # 🔥 get month/year
    month, year = get_month_year(request)

    incomes = Income.objects.filter(user=request.user)
    categories = Categories.objects.filter(user=request.user, type='income')

    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    # existing filters
    category = request.GET.get('category') or ""
    title = request.GET.get('title') or ""
    #month_param = request.GET.get('month') or ""
    #year_param = request.GET.get('year') or ""
    month_param = request.GET.get('month')
    year_param = request.GET.get('year')

    # category filter
    if category:
        incomes = incomes.filter(category_id=int(category))

    # title filter
    if title:
        incomes = incomes.filter(title__icontains=title)

    # ✅ MONTH LOGIC
    if month_param is not None and month_param not in ["None"]:
        if month_param == "":
            month_num_filter = None  # ALL months
        else:
            month_num_filter = int(month_param)
            incomes = incomes.filter(date__month=month_num_filter)
    else:
        month_num_filter = month  # current month
        incomes = incomes.filter(date__month=month_num_filter)

    # ✅ YEAR LOGIC
    if year_param and year_param not in ["", "None"]:
        try:
            year_filter = int(year_param)
        except ValueError:
            year_filter = year
    else:
        year_filter = year

    incomes = incomes.filter(date__year=year_filter)

    incomes = incomes.order_by('-date')

    context = {
        "incomes": incomes,
        "categories": categories,
        "months": months,

        "selected_category": category,
        "selected_title": title,

        "selected_month": month_num_filter,
        "selected_year": year_filter,
        "month_name": calendar.month_name[month_num_filter] if month_num_filter else "All Months",
    }

    return render(request, "view_income.html", context)

@login_required(login_url='login')
def view_expense(request):

    # 🔥 get month/year
    month, year = get_month_year(request)

    expenses = Expense.objects.filter(user=request.user)
    categories = Categories.objects.filter(user=request.user, type='expense')

    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    # existing filters
    category = request.GET.get('category') or ""
    title = request.GET.get('title') or ""
    #month_param = request.GET.get('month') or ""
    #year_param = request.GET.get('year') or ""
    month_param = request.GET.get('month')
    year_param = request.GET.get('year')

    # category filter
    if category:
        expenses = expenses.filter(category_id=int(category))

    # title filter
    if title:
        expenses = expenses.filter(title__icontains=title)

    # ✅ MONTH LOGIC
    if month_param is not None and month_param not in ["None"]:
        if month_param == "":
            # 🔥 ALL MONTHS → no filter
            month_num_filter = None
        else:
            # specific month
            month_num_filter = int(month_param)
            expenses = expenses.filter(date__month=month_num_filter)
    else:
        # 🔥 DEFAULT → CURRENT MONTH
        month_num_filter = month
        expenses = expenses.filter(date__month=month_num_filter)

    # ✅ YEAR LOGIC
    if year_param and year_param not in ["", "None"]:
        try:
            year_filter = int(year_param)
        except ValueError:
            year_filter = year
    else:
        # 🔥 DEFAULT → CURRENT YEAR
        year_filter = year

    expenses = expenses.filter(date__year=year_filter)

    expenses = expenses.order_by('-date')

    context = {
        "expenses": expenses,
        "categories": categories,
        "months": months,

        "selected_category": category,
        "selected_title": title,

        "selected_month": month_num_filter,
        "selected_year": year_filter,
        "month_name": calendar.month_name[month_num_filter] if month_num_filter else "All Months",
    }

    return render(request, "view_expense.html", context)



@login_required(login_url='login')
def edit_category(request, pk):
    category = get_object_or_404(Categories, id=pk, user=request.user)

    if request.method == "POST":
        name = request.POST.get("name")
        type_value = request.POST.get("type")

        if not name or not type_value:
            messages.error(request, "All fields are required.")
            return redirect("view_category")            

        category.name = name
        category.type = type_value
        category.save()

        messages.success(request, "Category updated successfully.")
        return redirect("view_category")

    return redirect("view_category")


@login_required(login_url='login')
def edit_income(request, pk):
    income = get_object_or_404(Income, id=pk, user=request.user)

    if request.method == "POST":
        category_id = request.POST.get("category")
        title = request.POST.get("title")
        amount = request.POST.get("amount")
        date = request.POST.get("date")
        description = request.POST.get("description")

        if not category_id or not title or not amount or not date:
            messages.error(request, "All required fields must be filled.")
            return redirect("view_income")

        try:
            amount = Decimal(amount)
        except InvalidOperation:
            messages.error(request, "Invalid amount value.")
            return redirect("view_income")

        category = get_object_or_404(
            Categories,
            id=category_id,
            user=request.user,
            type='income'
        )

        income.category = category
        income.title = title
        income.amount = amount
        income.date = date
        income.description = description
        income.save()

        messages.success(request, "Income updated successfully.")
        return redirect("view_income")

    return redirect("view_income")



@login_required(login_url='login')
def edit_budget(request, pk):
    budget = get_object_or_404(Budget, id=pk, user=request.user)

    if request.method == "POST":
        category_id = request.POST.get("category")
        month = request.POST.get("month")
        year = request.POST.get("year")
        amount = request.POST.get("amount")

        if not category_id or not month or not year or not amount:
            messages.error(request, "All fields are required.")
            return redirect("view_budget")

        try:
            year = int(year)
            amount = Decimal(amount)
        except (ValueError, InvalidOperation):
            messages.error(request, "Invalid year or amount.")
            return redirect("view_budget")

        # Duplicate check (exclude current record)
        if Budget.objects.filter(
            user=request.user,
            category_id=category_id,
            month=month,
            year=year
        ).exclude(id=budget.id).exists():
            messages.error(request, "Budget already exists for this category and month.")
            return redirect("view_budget")

        budget.category_id = category_id
        budget.month = month
        budget.year = year
        budget.amount = amount
        budget.save()

        messages.success(request, "Budget updated successfully.")
        return redirect("view_budget")

    return redirect("view_budget")


@login_required(login_url='login')
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, id=pk, user=request.user)

    if request.method == "POST":
        category_id = request.POST.get("category")
        title = request.POST.get("title")
        amount = request.POST.get("amount")
        date = request.POST.get("date")
        description = request.POST.get("description")

        if not category_id or not title or not amount or not date:
            messages.error(request, "All required fields must be filled.")
            return redirect("view_expense")

        try:
            amount = Decimal(amount)
        except InvalidOperation:
            messages.error(request, "Invalid amount value.")
            return redirect("view_expense")

        category = get_object_or_404(
            Categories,
            id=category_id,
            user=request.user,
            type='expense'
        )

        expense.category = category
        expense.title = title
        expense.amount = amount
        expense.date = date
        expense.description = description
        expense.save()

        messages.success(request, "Expense updated successfully.")
        return redirect("view_expense")

    return redirect("view_expense")


@login_required(login_url='login')
def delete_category(request, pk):
    category = get_object_or_404(Categories, id=pk, user=request.user)

    if request.method == "POST":
        category.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect("view_category")

    return redirect("view_category")


@login_required(login_url='login')
def delete_budget(request, pk):
    budget = get_object_or_404(Budget, id=pk, user=request.user)

    if request.method == "POST":
        budget.delete()
        messages.success(request, "Budget deleted successfully.")
        return redirect("view_budget")

    return redirect("view_budget")

@login_required(login_url='login')
def delete_income(request, pk):
    income = get_object_or_404(Income, id=pk, user=request.user)

    if request.method == "POST":
        income.delete()
        messages.success(request, "Income deleted successfully.")
        return redirect("view_income")

    return redirect("view_income")

@login_required(login_url='login')
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, id=pk, user=request.user)

    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
        return redirect("view_expense")

    return redirect("view_expense")





















@login_required(login_url='login')
def profile(request):
    return render(request, "profile.html")

#@login_required(login_url='login')
#def image_view(request):
 #   if request.method == 'POST' and request.FILES.get('fileImg'):
  #      uploaded_file = request.FILES['fileImg']
   #     file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.name)

        # save file to media folder
    #    with open(file_path, 'wb+') as f:
     #       for chunk in uploaded_file.chunks():
      #          f.write(chunk)

 #       return redirect('image')  # reload page after upload

  #  return render(request, "image.html")








def predict_category(request):

    description = request.GET.get("description")

    if not description:
        return JsonResponse({"category": ""})

    category = ml_predict(description)

    return JsonResponse({
        "category": category
    })


