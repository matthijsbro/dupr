from django.db import models
from django.http import HttpResponseForbidden
from django.shortcuts import render
from modelcluster.fields import ParentalManyToManyField

from wagtail.models import Page
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.embeds.blocks import EmbedBlock


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
        ('embed', EmbedBlock(max_width=800, max_height=400)),
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

    def serve(self, request, *args, **kwargs):
        """
        Control access based on user categories.
        """
        page_categories = set(self.categories.all()) # Get categories for this page as a set

        # If the page has no categories assigned, it's publically accessible
        if not page_categories:
            return super().serve(request, *args, **kwargs)

        # If the page has categories, require authentication
        if not request.user.is_authenticated:
            # You might want to redirect to a login page instead
            response = render(request, '403.html', {}, status=403)
            return response
            # return HttpResponseForbidden("You must be authorized in to view this teaching.")

        # Superusers and staff have access to all pages
        if request.user.is_superuser or request.user.is_staff:
            return super().serve(request, *args, **kwargs)

        # For authenticated non-staff users, check for intersecting categories
        user_categories = set(request.user.categories.all()) # Get user's categories as a set

        # Check if there is any overlap between user and page categories
        if user_categories.intersection(page_categories):
            return super().serve(request, *args, **kwargs)
        else:
            # No intersecting categories, deny access - Render the custom 403 template
            response = render(request, '403.html', {}, status=403)
            return response
            # return HttpResponseForbidden("You do not have the required auhtorization to view this teaching, contact us if you think you should get access.")

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
