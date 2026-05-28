from django.contrib import admin
from .models import Tenant, DataSource, IngestionJob, RawRecord, ActivityRecord, ActivityEditLog

admin.site.register(Tenant)
admin.site.register(DataSource)
admin.site.register(IngestionJob)
admin.site.register(RawRecord)
admin.site.register(ActivityRecord)
admin.site.register(ActivityEditLog)
