from django.contrib import admin
from unfold.admin import ModelAdmin
from sla.models import SLAMetric


@admin.register(SLAMetric)
class SLAMetricAdmin(ModelAdmin):
    list_display = ('provider', 'metric_type', 'value', 'period_start', 'period_end', 'measured_at')
    list_filter = ('metric_type',)
    search_fields = ('provider__company_name',)
    readonly_fields = ('measured_at',)
    raw_id_fields = ('provider',)
