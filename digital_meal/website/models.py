from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.images.blocks import ImageChooserBlock


class IntroTextBlock(blocks.StructBlock):
    text = blocks.RichTextBlock(features=['bold', 'italic', 'link'])

    class Meta:
        icon = 'edit'
        label = 'Intro Text'


class ColorChoiceBlock(blocks.ChoiceBlock):
    """
    Color choices according to the main colors defined in
    Digital Meal's corporate design plus black and white.
    """
    choices = [
        ('#BFE2E0', 'Blue'),
        ('#C8C1E1', 'Purple'),
        ('#F7B17B', 'Orange'),
        ('#F5E165', 'Yellow'),
        ('#D6E297', 'Lightgreen'),
        ('#9BCEA4', 'Green'),
        ('#FFFFFF', 'White'),
        ('#212529', 'Black'),
    ]

    class Meta:
        icon = 'pick'


class CallToActionBlock(blocks.StructBlock):
    """
    A page-spanning block that can be used to highlight certain information.
    """
    title = blocks.TextBlock()
    text = blocks.RichTextBlock(features=['bold', 'italic', 'document-link', 'link', 'ol', 'ul'])
    cta_linktext = blocks.TextBlock()
    cta_link = blocks.URLBlock()
    background_color = ColorChoiceBlock(default='#F5E165')
    text_color = ColorChoiceBlock(default='#212529')
    button_background_color = ColorChoiceBlock(default='#F7B17B')
    button_text_color = ColorChoiceBlock(default='#212529')

    def get_form_context(self, value, prefix='', errors=None):
        context = super().get_form_context(value, prefix=prefix, errors=errors)
        context['advanced_fields'] = [
            'background color',
            'text color',
            'button background color',
            'button text color'
        ]
        return context

    class Meta:
        icon = 'edit'
        label = 'Call to Action'
        template = 'website/components/call_to_action.html'
        form_template = 'website/wagtail_forms/call_to_action.html'


class DigitalMealContentPage(Page):
    """
    Default page model used for pages created in the wagtail CMS.
    """
    template = 'website/wagtail_content.html'

    body = StreamField([
        ('intro_text', IntroTextBlock()),
        ('heading', blocks.CharBlock(form_classname='full title', icon='title')),
        ('paragraph', blocks.RichTextBlock(icon='pilcrow')),
        ('list', blocks.ListBlock(blocks.CharBlock(label='List'), icon='list-ul')),
        ('image', ImageChooserBlock()),
        ('call_to_action', CallToActionBlock()),
    ], use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel('body', classname='full'),
    ]
