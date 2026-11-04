from django import template

register = template.Library()


@register.inclusion_tag('components/kpi_card.html')
def kpi_card(label, icon, item):
    return {'label': label, 'icon': icon, 'item': item, 'is_number': not isinstance(item['value'], str)}


@register.inclusion_tag('components/chart_card.html')
def chart_card(key, title, type, subtitle='', height=300):
    return {'key': key, 'title': title, 'type': type, 'subtitle': subtitle, 'height': height}


@register.inclusion_tag('components/table_card.html', takes_context=True)
def table_card(context, dashboard, rows):
    return {
        'slug': dashboard.slug,
        'title': dashboard.table_title,
        'columns': dashboard.columns,
        'rows': [[(key, row[key]) for key, _ in dashboard.columns] for row in rows],
        'query': context['request'].GET.urlencode(),
    }
