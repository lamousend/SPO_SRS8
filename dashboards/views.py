import csv

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .services import DASHBOARDS, available_dashboards
from .utils import ru


def get_dashboard(request, slug):
    dashboard = DASHBOARDS.get(slug)
    if dashboard is None:
        raise Http404
    if not dashboard.allowed(request.user):
        raise PermissionDenied
    return dashboard(request.GET)


@login_required
def dashboard_index(request):
    dashboards = [(d, d().summary()) for d in available_dashboards(request.user)]
    return render(request, 'dashboards/index.html', {'dashboards': dashboards})


@login_required
def dashboard_page(request, slug):
    dashboard = get_dashboard(request, slug)
    return render(request, f'dashboards/{slug}.html', {'dashboard': dashboard, 'data': dashboard.build()})


@login_required
def dashboard_export(request, slug):
    dashboard = get_dashboard(request, slug)
    if not dashboard.columns:
        raise Http404

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{slug}_{timezone.localtime():%Y-%m-%d}.csv"'
    response.write('﻿')
    writer = csv.writer(response, delimiter=';')
    writer.writerow([f'{label}, %' if key == 'share' else label for key, label in dashboard.columns])
    for row in dashboard.build()['rows']:
        writer.writerow([ru(row[key]) if isinstance(row[key], float) else row[key] for key, _ in dashboard.columns])
    return response
