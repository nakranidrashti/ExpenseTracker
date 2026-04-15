from django import forms

from tracker.models import Categories, Budget, Income, Expense


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Categories
        fields = ['name', 'type']

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['month', 'year', 'amount']

class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['category', 'title', 'amount', 'date', 'description']

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'title', 'amount', 'date', 'description']