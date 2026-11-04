from .services import available_dashboards


def dashboards_nav(request):
    if not request.user.is_authenticated:
        return {'nav_dashboards': []}
    return {'nav_dashboards': available_dashboards(request.user)}
