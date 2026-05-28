from rest_framework import serializers
from .models import Tenant, DataSource, IngestionJob, RawRecord, ActivityRecord, ActivityEditLog


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'created_at']


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'tenant', 'type', 'name', 'config', 'created_at']


class IngestionJobSerializer(serializers.ModelSerializer):
    source_type = serializers.CharField(source='data_source.type', read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            'id', 'tenant', 'data_source', 'source_type', 'status',
            'uploaded_file', 'started_at', 'finished_at', 'created_by',
            'total_rows', 'parsed_rows', 'failed_rows', 'suspicious_rows',
            'created_at',
        ]
        read_only_fields = [
            'status', 'started_at', 'finished_at',
            'total_rows', 'parsed_rows', 'failed_rows', 'suspicious_rows',
        ]


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ['id', 'row_number', 'source_type', 'raw_payload', 'hash',
                  'parse_status', 'parse_error', 'created_at']


class ActivityEditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityEditLog
        fields = ['id', 'edited_by', 'edited_at', 'before', 'after', 'reason']


class ActivityRecordListSerializer(serializers.ModelSerializer):
    source_type = serializers.CharField(source='ingestion_job.data_source.type', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            'id', 'tenant', 'tenant_name', 'ingestion_job', 'source_type',
            'status', 'scope', 'category',
            'activity_date', 'period_start', 'period_end',
            'quantity', 'unit_original', 'quantity_normalized', 'unit_normalized',
            'facility_id', 'facility_name', 'meter_id',
            'flags', 'locked_at', 'locked_by', 'created_at', 'updated_at',
        ]


class ActivityRecordDetailSerializer(serializers.ModelSerializer):
    raw_record = RawRecordSerializer(read_only=True)
    edit_logs = ActivityEditLogSerializer(many=True, read_only=True)
    source_type = serializers.CharField(source='ingestion_job.data_source.type', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            'id', 'tenant', 'tenant_name', 'ingestion_job', 'source_type',
            'raw_record', 'status', 'locked_at', 'locked_by',
            'scope', 'category',
            'activity_date', 'period_start', 'period_end',
            'quantity', 'unit_original', 'quantity_normalized', 'unit_normalized',
            'facility_id', 'facility_name', 'meter_id',
            'vendor', 'cost_amount', 'cost_currency', 'country', 'notes',
            'travel_mode', 'origin', 'destination', 'distance_km', 'cabin_class', 'nights',
            'material_group', 'spend_amount', 'spend_currency', 'item_description',
            'flags', 'edited_fields', 'created_at', 'updated_at',
            'edit_logs',
        ]


EDITABLE_FIELDS = [
    'scope', 'category', 'activity_date', 'period_start', 'period_end',
    'quantity', 'unit_original', 'quantity_normalized', 'unit_normalized',
    'facility_id', 'facility_name', 'meter_id', 'vendor',
    'cost_amount', 'cost_currency', 'country', 'notes',
    'travel_mode', 'origin', 'destination', 'distance_km', 'cabin_class', 'nights',
    'material_group', 'spend_amount', 'spend_currency', 'item_description',
    'flags',
]


class ActivityRecordPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityRecord
        fields = EDITABLE_FIELDS
