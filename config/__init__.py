"""
FlexyRide Corporate package.
"""

# Compatibility patch for Django 5.2+ / 6.0+ with legacy admin inclusion tags
# Only applies if InclusionAdminNode.__init__ has 'name' as its first parameter
try:
    import inspect
    from django.contrib.admin.templatetags.base import InclusionAdminNode

    _orig_inclusion_admin_node_init = InclusionAdminNode.__init__
    _init_params = list(inspect.signature(_orig_inclusion_admin_node_init).parameters.keys())

    if len(_init_params) > 1 and _init_params[1] == 'name':
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

