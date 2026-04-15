from datetime import datetime

def global_date(request):

    now = datetime.now()

    return {
        'selected_month': now.month,
        'selected_year': now.year,
        'month_name': now.strftime("%B")
    }