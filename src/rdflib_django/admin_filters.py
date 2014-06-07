from django.contrib.admin import RelatedFieldListFilter, AllValuesFieldListFilter, FieldListFilter
from django.contrib.admin.options import IncorrectLookupParameters
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from django.db import models
from rdflib import URIRef, Literal
from rdflib_django.fields import URIField, LiteralField

__author__ = 'g.bronzini@gmail.com'


def last_part_related_filter(p_name, length=15, custom_template=None):
    """returns a django.contrib.admin.filters.RelatedFieldListFilter subclass
    that will override lookup_choices: will return only last word after the last /

    Useful for Context.

    """
    class _FieldListFilter(RelatedFieldListFilter):
        def __init__(self, field, request, params, model, model_admin, field_path):
            super(_FieldListFilter, self).__init__(field, request, params, model, model_admin, field_path)
            self.lookup_choices = [(k, v.rstrip('/').split('/')[-1], '/'.join(v.rstrip('/').split('/')[:-1])) for k,v in self.lookup_choices]

        parameter_name = p_name
        title = p_name

        def choices(self, cl):
            from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
            yield {
                'selected': self.lookup_val is None and not self.lookup_val_isnull,
                'query_string': cl.get_query_string({},
                    [self.lookup_kwarg, self.lookup_kwarg_isnull]),
                'display': _('All'),
                'hint': ''
            }
            for pk_val, val, hint in self.lookup_choices:
                yield {
                    'selected': self.lookup_val == smart_text(pk_val),
                    'query_string': cl.get_query_string({
                        self.lookup_kwarg: pk_val,
                    }, [self.lookup_kwarg_isnull]),
                    'display': val,
                    'hint': hint
                }
            if (isinstance(self.field, models.related.RelatedObject)
                    and self.field.field.null or hasattr(self.field, 'rel')
                        and self.field.null):
                yield {
                    'selected': bool(self.lookup_val_isnull),
                    'query_string': cl.get_query_string({
                        self.lookup_kwarg_isnull: 'True',
                    }, [self.lookup_kwarg]),
                    'display': EMPTY_CHANGELIST_VALUE,
                    'hint': ''
                }

    if custom_template:
        _FieldListFilter.template = custom_template
    return (p_name, _FieldListFilter)


class URIRefFieldFilter(AllValuesFieldListFilter):
    template = "rdflib_django/grouped_filter.html"

    def queryset(self, request, queryset):
        try:
            uri_ref = self.used_parameters.pop(self.lookup_kwarg, None)
            if uri_ref:
                self.used_parameters[self.lookup_kwarg] =  URIRef(uri_ref)
            return queryset.filter(**self.used_parameters)
        except ValidationError as e:
            raise IncorrectLookupParameters(e)

    def choices(self, cl):
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        yield {
            'selected': (self.lookup_val is None
                and self.lookup_val_isnull is None),
            'query_string': cl.get_query_string({},
                [self.lookup_kwarg, self.lookup_kwarg_isnull]),
            'display': _('All'),
        }
        include_none = False
        for val in self.lookup_choices:
            if val is None:
                include_none = True
                continue
            val = smart_text(val)
            prefix = val.split('#')
            yield {
                'selected': self.lookup_val == val,
                'query_string': cl.get_query_string({
                    self.lookup_kwarg: val,
                }, [self.lookup_kwarg_isnull]),
                'prefix': prefix[0] if len(prefix)>1 else "",
                'display': prefix[1] if len(prefix)>1 else val,
            }
        if include_none:
            yield {
                'selected': bool(self.lookup_val_isnull),
                'query_string': cl.get_query_string({
                    self.lookup_kwarg_isnull: 'True',
                }, [self.lookup_kwarg]),
                'display': EMPTY_CHANGELIST_VALUE,
                }

FieldListFilter.register(lambda f: isinstance(f, URIField), URIRefFieldFilter, take_priority=True)

class LiteralFieldFilter(AllValuesFieldListFilter):
    def queryset(self, request, queryset):
        try:
            uri_ref = self.used_parameters.pop(self.lookup_kwarg, None)
            if uri_ref:
                splitted = uri_ref.split("^^^^")
                literal = Literal(splitted[0], datatype=URIRef(splitted[1])) if len(splitted)>1 and splitted[1] else Literal(splitted[0])
                self.used_parameters[self.lookup_kwarg] = literal
            return queryset.filter(**self.used_parameters)
        except ValidationError as e:
            raise IncorrectLookupParameters(e)

    def choices(self, cl):
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        yield {
            'selected': (self.lookup_val is None
                and self.lookup_val_isnull is None),
            'query_string': cl.get_query_string({},
                [self.lookup_kwarg, self.lookup_kwarg_isnull]),
            'display': _('All'),
        }
        include_none = False
        for val in self.lookup_choices:
            if val is None:
                include_none = True
                continue
            val = smart_text(val)
            splitted = val.split("^^^^")
            yield {
                'selected': self.lookup_val == val,
                'query_string': cl.get_query_string({
                    self.lookup_kwarg: val,
                }, [self.lookup_kwarg_isnull]),
                'display': val if len(splitted)>1 and splitted[1] else splitted[0],
            }
        if include_none:
            yield {
                'selected': bool(self.lookup_val_isnull),
                'query_string': cl.get_query_string({
                    self.lookup_kwarg_isnull: 'True',
                }, [self.lookup_kwarg]),
                'display': EMPTY_CHANGELIST_VALUE,
            }

FieldListFilter.register(lambda f: isinstance(f, LiteralField), LiteralFieldFilter, take_priority=True)
