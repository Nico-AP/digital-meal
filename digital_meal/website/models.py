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
    ], use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel('body', classname='full'),
    ]
