from django.contrib import admin
from .models import Categories, Budget, Income, Expense

# 🔹 Base admin to handle category filtering
class BaseAdmin(admin.ModelAdmin):
    category_type = None  # 'income' or 'expense'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if self.category_type:
            # Superusers: filter only by type
            if request.user.is_superuser:
                form.base_fields['category'].queryset = Categories.objects.filter(
                    type=self.category_type
                )
            else:
                # Normal users: filter by type and user
                form.base_fields['category'].queryset = Categories.objects.filter(
                    type=self.category_type,
                    user=request.user
                )
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # superuser sees all entries
        return qs.filter(user=request.user)


# 🔹 CATEGORY
@admin.register(Categories)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'user']
    search_fields = ['name', 'type', 'user__username']
    list_filter = ['type', 'user']
    ordering = ['name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


# 🔹 BUDGET
@admin.register(Budget)
class BudgetAdmin(BaseAdmin):
    list_display = ['category', 'amount', 'month', 'year', 'user']
    search_fields = ['category__name', 'user__username']
    list_filter = ['category', 'month', 'year', 'user']
    category_type = 'expense'


# 🔹 INCOME
@admin.register(Income)
class IncomeAdmin(BaseAdmin):
    list_display = ['title', 'amount', 'category', 'date', 'user']
    search_fields = ['title', 'category__name', 'user__username']
    list_filter = ['category', 'date', 'user']
    date_hierarchy = 'date'
    category_type = 'income'


# 🔹 EXPENSE
@admin.register(Expense)
class ExpenseAdmin(BaseAdmin):
    list_display = ['title', 'amount', 'category', 'date', 'user']
    search_fields = ['title', 'category__name', 'user__username']
    list_filter = ['category', 'date', 'user']
    date_hierarchy = 'date'
    category_type = 'expense'