from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone

MONTHS = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
TRUNC = {'day': TruncDay, 'week': TruncWeek, 'month': TruncMonth}


def chart(labels, *series):
    return {'labels': list(labels), 'series': [{'name': name, 'data': list(values)} for name, values in series]}


def kpi(value, hint='', suffix=''):
    return {'value': value, 'hint': hint, 'suffix': suffix}


def ru(number):
    return f'{number:g}'.replace('.', ',')


def percent(part, whole):
    return round(part * 100 / whole, 1) if whole else 0


def period_start(days):
    return timezone.now() - timedelta(days=days) if days else None


def step_for(days):
    if days and days <= 31:
        return 'day'
    if days and days <= 120:
        return 'week'
    return 'month'


def bucket_start(moment, step):
    day = timezone.localtime(moment).date()
    if step == 'week':
        return day - timedelta(days=day.weekday())
    if step == 'month':
        return day.replace(day=1)
    return day


def next_bucket(day, step):
    if step == 'month':
        return (day + timedelta(days=32)).replace(day=1)
    return day + timedelta(days=7 if step == 'week' else 1)


def bucket_label(day, step):
    if step == 'month':
        return f'{MONTHS[day.month - 1]} {day:%y}'
    if step == 'week':
        return f'с {day:%d.%m}'
    return f'{day:%d.%m}'


def timeseries(queryset, field, since, step):
    rows = (queryset.annotate(bucket=TRUNC[step](field)).values('bucket')
            .annotate(n=Count('pk', distinct=True)).order_by('bucket'))
    counts = {row['bucket'].date(): row['n'] for row in rows}
    if since is None and not counts:
        return [], []

    day = bucket_start(since, step) if since else min(counts)
    end = bucket_start(timezone.now(), step)
    labels, values = [], []
    while day <= end:
        labels.append(bucket_label(day, step))
        values.append(counts.get(day, 0))
        day = next_bucket(day, step)
    return labels, values


def time_ago(moment):
    minutes = int((timezone.now() - moment).total_seconds() // 60)
    if minutes < 1:
        return 'только что'
    if minutes < 60:
        return f'{minutes} мин назад'
    if minutes < 24 * 60:
        return f'{minutes // 60} ч назад'
    if minutes < 31 * 24 * 60:
        return f'{minutes // (24 * 60)} дн назад'
    return timezone.localtime(moment).strftime('%d.%m.%Y')
