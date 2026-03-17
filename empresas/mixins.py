"""
Multi-tenant mixins for Harmoni ERP views.

These mixins enforce row-level data isolation by automatically filtering
querysets based on the current empresa (request.empresa_actual).
"""
from django.core.exceptions import PermissionDenied


class EmpresaFilterMixin:
    """
    Mixin for class-based views that auto-filters querysets by empresa_actual.

    Works with any model that has an `empresa` FK field. If the model does not
    have an `empresa` field, the queryset is returned unfiltered.

    Usage:
        class PersonalListView(EmpresaFilterMixin, ListView):
            model = Personal
    """

    # Override to use a different lookup field (e.g., 'empresa_id')
    empresa_field = 'empresa'

    def get_queryset(self):
        qs = super().get_queryset()
        empresa = getattr(self.request, 'empresa_actual', None)
        if empresa and hasattr(qs.model, self.empresa_field):
            qs = qs.filter(**{self.empresa_field: empresa})
        return qs


class EmpresaRequiredMixin:
    """
    Mixin that requires an active empresa on the request.
    Returns 403 if no empresa is set.
    """

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request, 'empresa_actual', None):
            raise PermissionDenied(
                'No hay empresa activa. Seleccione una empresa o acceda via subdominio.'
            )
        return super().dispatch(request, *args, **kwargs)


class EmpresaCreateMixin:
    """
    Mixin for CreateView / form-based views that auto-sets the empresa field
    on the object being created.

    Usage:
        class PersonalCreateView(EmpresaCreateMixin, CreateView):
            model = Personal
            fields = [...]
    """

    empresa_field = 'empresa'

    def form_valid(self, form):
        empresa = getattr(self.request, 'empresa_actual', None)
        if empresa and hasattr(form.instance, self.empresa_field):
            setattr(form.instance, self.empresa_field, empresa)
        return super().form_valid(form)
