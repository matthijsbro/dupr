from django.db import models
from wagtail.admin.panels import (
    FieldPanel,
    MultiFieldPanel,
)
from wagtail.contrib.settings.models import (
    BaseGenericSetting,
    register_setting,
)

@register_setting
class NavigationSettings(BaseGenericSetting):
    youtube_url = models.URLField(verbose_name="YouTube URL", blank=True)
    facebook_url = models.URLField(verbose_name="Facebook URL", blank=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("youtube_url"),
                FieldPanel("facebook_url"),
            ],
            "Social settings",
        )
    ]