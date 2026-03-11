from django.shortcuts import render

from shared.routing.constants import MDMRoutingContext
from shared.routing.utils import get_routing_context


def get_template_prefix(request) -> str:
    routing_context = get_routing_context(request)
    if routing_context == MDMRoutingContext.MY_DM:
        return "mydigitalmeal"
    return "digital_meal"


def custom_400(request, exception):
    template_prefix = get_template_prefix(request)
    return render(request, f"{template_prefix}/400.html", status=400)


def custom_403(request, exception):
    template_prefix = get_template_prefix(request)
    return render(request, f"{template_prefix}/403.html", status=403)


def custom_404(request, exception):
    template_prefix = get_template_prefix(request)
    return render(request, f"{template_prefix}/404.html", status=404)


def custom_500(request):
    template_prefix = get_template_prefix(request)
    return render(request, f"{template_prefix}/500.html", status=500)
