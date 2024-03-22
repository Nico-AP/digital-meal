from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView


@method_decorator(staff_member_required, name='dispatch')
class StyleGuide(TemplateView):
    template_name = 'digital_meal_website/styleguide.html'
