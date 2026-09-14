"""
FlexyRide Corporate package.
"""

# Compatibility patch for Django 6.1+ with django-unfold (and legacy admin inclusion tags)
# In Django 6.1+, InclusionAdminNode.__init__ takes:
# (self, name, parser, token, func, template_name, takes_context=True)
# Whereas older packages like django-unfold call:
# (self, parser, token, func=..., template_name=..., takes_context=...)
try:
    from django.contrib.admin.templatetags.base import InclusionAdminNode

    _orig_inclusion_admin_node_init = InclusionAdminNode.__init__

    def _compat_inclusion_admin_node_init(self, *args, **kwargs):
        if args and not isinstance(args[0], str):
            # The caller passed (parser, token, ...) instead of (name, parser, token, ...)
            tag_name = "inclusion_tag"
            if len(args) > 1 and hasattr(args[1], "contents"):
                try:
                    tag_name = args[1].contents.split()[0]
                except Exception:
                    pass
            return _orig_inclusion_admin_node_init(self, tag_name, *args, **kwargs)
        return _orig_inclusion_admin_node_init(self, *args, **kwargs)

    InclusionAdminNode.__init__ = _compat_inclusion_admin_node_init
except Exception:
    pass

from .celery import app as celery_app

__all__ = ('celery_app',)

