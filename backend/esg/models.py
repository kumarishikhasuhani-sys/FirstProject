import uuid
from django.db import models


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DataSource(models.Model):
    SOURCE_TYPES = [('SAP', 'SAP'), ('UTILITY', 'Utility'), ('TRAVEL', 'Travel')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='data_sources')
    type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    name = models.CharField(max_length=255)
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} / {self.type} / {self.name}"


class IngestionJob(models.Model):
    STATUS_CHOICES = [
        ('UPLOADED', 'Uploaded'),
        ('PARSING', 'Parsing'),
        ('PARSED', 'Parsed'),
        ('FAILED', 'Failed'),
        ('PARTIALLY_PARSED', 'Partially Parsed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ingestion_jobs')
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='ingestion_jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPLOADED')
    uploaded_file = models.FileField(upload_to='uploads/')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=255, default='')
    total_rows = models.IntegerField(default=0)
    parsed_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    suspicious_rows = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} / {self.data_source.type} / {self.status}"


class RawRecord(models.Model):
    PARSE_STATUS_CHOICES = [('PARSED', 'Parsed'), ('FAILED', 'Failed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='raw_records')
    ingestion_job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='raw_records')
    row_number = models.IntegerField()
    source_type = models.CharField(max_length=20)
    raw_payload = models.JSONField()
    hash = models.CharField(max_length=64)
    parse_status = models.CharField(max_length=10, choices=PARSE_STATUS_CHOICES)
    parse_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('ingestion_job', 'row_number')

    def __str__(self):
        return f"Row {self.row_number} ({self.parse_status})"


class ActivityRecord(models.Model):
    STATUS_CHOICES = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    SCOPE_CHOICES = [
        ('SCOPE_1', 'Scope 1'),
        ('SCOPE_2', 'Scope 2'),
        ('SCOPE_3', 'Scope 3'),
    ]
    CATEGORY_CHOICES = [
        ('FUEL_COMBUSTION', 'Fuel Combustion'),
        ('ELECTRICITY', 'Electricity'),
        ('PROCUREMENT', 'Procurement'),
        ('FLIGHT', 'Flight'),
        ('HOTEL', 'Hotel'),
        ('GROUND', 'Ground'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='activity_records')
    ingestion_job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='activity_records')
    raw_record = models.OneToOneField(RawRecord, on_delete=models.CASCADE, related_name='activity_record')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_REVIEW')
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.CharField(max_length=255, null=True, blank=True)

    # Scope & category
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, null=True, blank=True)

    # Normalized quantities
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    unit_original = models.CharField(max_length=30, null=True, blank=True)
    quantity_normalized = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    unit_normalized = models.CharField(max_length=30, null=True, blank=True)

    # Attribution
    facility_id = models.CharField(max_length=100, null=True, blank=True)
    facility_name = models.CharField(max_length=255, null=True, blank=True)
    meter_id = models.CharField(max_length=100, null=True, blank=True)
    vendor = models.CharField(max_length=255, null=True, blank=True)
    cost_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cost_currency = models.CharField(max_length=10, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    # Travel-specific
    travel_mode = models.CharField(max_length=20, null=True, blank=True)
    origin = models.CharField(max_length=10, null=True, blank=True)
    destination = models.CharField(max_length=10, null=True, blank=True)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cabin_class = models.CharField(max_length=50, null=True, blank=True)
    nights = models.IntegerField(null=True, blank=True)

    # Procurement-specific
    material_group = models.CharField(max_length=100, null=True, blank=True)
    spend_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    spend_currency = models.CharField(max_length=10, null=True, blank=True)
    item_description = models.TextField(null=True, blank=True)

    # Flags & audit
    flags = models.JSONField(default=list)
    edited_fields = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} / {self.status} / {self.activity_date}"


class ActivityEditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='edit_logs')
    activity_record = models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name='edit_logs')
    edited_by = models.CharField(max_length=255)
    edited_at = models.DateTimeField(auto_now_add=True)
    before = models.JSONField()
    after = models.JSONField()
    reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Edit by {self.edited_by} at {self.edited_at}"
