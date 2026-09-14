from django.db import models


class SLAMetric(models.Model):
    """Service level metrics per provider (US-103, US-105, US-106)."""

    class MetricType(models.TextChoices):
        RESPONSE_TIME = 'RESPONSE_TIME', 'Quote Response Time'
        QUALITY_SCORE = 'QUALITY_SCORE', 'Service Quality Score'
        ON_TIME_RATE = 'ON_TIME_RATE', 'On-Time Arrival Rate'
        COMPLETION_RATE = 'COMPLETION_RATE', 'Trip Completion Rate'
        CUSTOMER_SATISFACTION = 'CUSTOMER_SATISFACTION', 'Customer Satisfaction Score'

    provider = models.ForeignKey(
        'accounts.ProviderCompany',
        on_delete=models.CASCADE,
        related_name='sla_metrics'
    )
    metric_type = models.CharField(
        max_length=30,
        choices=MetricType.choices
    )
    value = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Metric value (percentage, score, or duration in minutes)."
    )
    period_start = models.DateField()
    period_end = models.DateField()
    measured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SLA Metric'
        verbose_name_plural = 'SLA Metrics'
        ordering = ['-measured_at']

    def __str__(self):
        return f"{self.provider.company_name} - {self.get_metric_type_display()}: {self.value}"
