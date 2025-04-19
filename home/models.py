from django.db import models
from wagtail.models import Page
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, PageChooserPanel, FieldRowPanel
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.embeds.blocks import EmbedBlock

class HomePage(Page):
    """Home page with hero image, quote, body"""
    hero_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    hero_quote = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short inspirational quote to overlay on the hero image."
    )
    intro_body = StreamField(
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
    featured_activity_1 = models.ForeignKey(
        'activities.ActivityPage',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    featured_activity_2 = models.ForeignKey(
        'activities.ActivityPage',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    featured_activity_3 = models.ForeignKey(
        'activities.ActivityPage',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )


    content_panels = Page.content_panels + [
        FieldPanel('hero_image'),
        FieldPanel('hero_quote'),
        FieldPanel('intro_body'),
        PageChooserPanel('featured_activity_1'),
        PageChooserPanel('featured_activity_2'),
        PageChooserPanel('featured_activity_3'),
    ]
    
    def get_featured_activities(self):
        """
        Return a list of the three featured activity pages (skipping any that are None).
        """
        return [
            activity for activity in (
                self.featured_activity_1,
                self.featured_activity_2,
                self.featured_activity_3
            ) if activity
        ]