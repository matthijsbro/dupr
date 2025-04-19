from django.db import models
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.admin.panels import FieldPanel


class ActivityPage(Page):
    """Page model for a single activity (e.g., teaching, trip, ceremony)."""

    main_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    body = StreamField(
        [
            ('heading', blocks.CharBlock(classname='full title')),
            ('paragraph', blocks.RichTextBlock(features=['h2', 'bold', 'italic', 'link'])),
            ('embed_video', EmbedBlock()),
            ('image', ImageChooserBlock()),
            ('gallery', blocks.ListBlock(ImageChooserBlock())),
        ],
        null=True,
        blank=True,
        use_json_field=True
    )

    content_panels = Page.content_panels + [
        FieldPanel('main_image'),
        FieldPanel('body'),
    ]

    class Meta:
        verbose_name = "Activity Page"

    template = "activities/activity_page.html"

class ActivitiesIndexPage(Page):
    """Landing page that lists all ActivityPage children."""

    intro_text = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro_text'),
    ]

    # This is where you add the method
    def get_context(self, request):
        context = super().get_context(request)
        context['activities'] = ActivityPage.objects.live().descendant_of(self).order_by('-first_published_at')
        return context

    class Meta:
        verbose_name = "Activities Index Page"
    
    template = "activities/activities_index_page.html"