from django.db import models
from modelcluster.fields import ParentalManyToManyField

from wagtail.models import Page
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock


@register_snippet
class Category(models.Model):
    """
    A content category snippet to group TeachingPage permissions.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
    ]

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'


class TeachingPage(Page):
    """
    A page representing a teaching: header image, rich body, and access categories.
    """
    header_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    body = StreamField([
        ('heading', blocks.CharBlock(form_classname='full title')),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('video', blocks.URLBlock(help_text='Embed URL for video')),
        ('audio', blocks.URLBlock(help_text='Embed URL for audio')),
        ('document', DocumentChooserBlock()),
    ], use_json_field=True)

    categories = ParentalManyToManyField(
        'teachings.Category',
        blank=True,
        related_name='teachings',
        help_text='Only users in these categories may view this page'
    )

    template = "teachings/teaching_page.html"
    parent_page_types = ['teachings.TeachingsIndexPage']

    content_panels = Page.content_panels + [
        FieldPanel('header_image'),
        FieldPanel('body'),
        FieldPanel('categories'),
    ]

    class Meta:
        verbose_name = 'Teaching Page'
        verbose_name_plural = 'Teaching Pages'

class TeachingsIndexPage(Page):
    """
    A listing page for all TeachingPage children.
    """
    template = "teachings/teachings_index_page.html"
    subpage_types = ['teachings.TeachingPage']
    max_count = 1

    def get_context(self, request, *args, **kwargs):
        # Fetch only live, specific TeachingPage children
        context = super().get_context(request, *args, **kwargs)
        context['teachings_list'] = self.get_children().live().specific()
        return context
