from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import (
    ActivityEditLog, ActivityRecord, DataSource, IngestionJob, RawRecord, Tenant,
)
from .serializers import (
    ActivityRecordDetailSerializer,
    ActivityRecordListSerializer,
    ActivityRecordPatchSerializer,
    DataSourceSerializer,
    IngestionJobSerializer,
    TenantSerializer,
    EDITABLE_FIELDS,
)


# ── Tenants ──────────────────────────────────────────────────────────────────

class TenantViewSet(ModelViewSet):
    queryset = Tenant.objects.all().order_by('name')
    serializer_class = TenantSerializer
    http_method_names = ['get', 'post', 'head', 'options']


# ── Data Sources ──────────────────────────────────────────────────────────────

class DataSourceViewSet(ModelViewSet):
    queryset = DataSource.objects.select_related('tenant').all()
    serializer_class = DataSourceSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs


# ── Ingestion Jobs ────────────────────────────────────────────────────────────

PARSER_MAP = {
    'SAP': 'sap',
    'UTILITY': 'utility',
    'TRAVEL': 'travel',
}


def _run_parser(source_type, file_bytes):
    module_name = PARSER_MAP.get(source_type)
    if not module_name:
        raise ValueError(f"Unknown source type: {source_type}")
    import importlib
    mod = importlib.import_module(f'esg.parsers.{module_name}')
    return mod.parse(file_bytes, source_type)


def _save_parsed_results(job, results):
    total = len(results)
    parsed = 0
    failed = 0
    suspicious = 0

    for item in results:
        raw = RawRecord.objects.create(
            tenant=job.tenant,
            ingestion_job=job,
            row_number=item['row_number'],
            source_type=job.data_source.type,
            raw_payload=item['raw_payload'],
            hash=item['hash'],
            parse_status=item['parse_status'],
            parse_error=item.get('parse_error'),
        )

        if item['parse_status'] == 'PARSED':
            parsed += 1
            ad = item['activity_data']
            flags = ad.pop('flags', [])
            if flags:
                suspicious += 1

            ActivityRecord.objects.create(
                tenant=job.tenant,
                ingestion_job=job,
                raw_record=raw,
                flags=flags,
                **{k: v for k, v in ad.items() if hasattr(ActivityRecord, k)},
            )
        else:
            failed += 1

    job.total_rows = total
    job.parsed_rows = parsed
    job.failed_rows = failed
    job.suspicious_rows = suspicious
    job.finished_at = timezone.now()
    if failed == total:
        job.status = 'FAILED'
    elif failed > 0:
        job.status = 'PARTIALLY_PARSED'
    else:
        job.status = 'PARSED'
    job.save()


class IngestionJobViewSet(ModelViewSet):
    queryset = IngestionJob.objects.select_related('tenant', 'data_source').all()
    serializer_class = IngestionJobSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset().order_by('-created_at')
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def create(self, request, *args, **kwargs):
        tenant_id = request.data.get('tenant_id')
        source_type = request.data.get('source_type')
        uploaded_file = request.FILES.get('file')

        if not all([tenant_id, source_type, uploaded_file]):
            return Response(
                {'error': 'tenant_id, source_type, and file are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found.'}, status=status.HTTP_404_NOT_FOUND)

        if source_type not in PARSER_MAP:
            return Response(
                {'error': f'source_type must be one of {list(PARSER_MAP)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data_source, _ = DataSource.objects.get_or_create(
            tenant=tenant,
            type=source_type,
            defaults={'name': f'{source_type} default'},
        )

        # Read bytes before model.save() moves the file pointer to EOF
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        job = IngestionJob.objects.create(
            tenant=tenant,
            data_source=data_source,
            uploaded_file=uploaded_file,
            created_by=request.data.get('created_by', 'analyst'),
            status='PARSING',
            started_at=timezone.now(),
        )

        try:
            results = _run_parser(source_type, file_bytes)
            _save_parsed_results(job, results)
        except Exception as exc:
            job.status = 'FAILED'
            job.finished_at = timezone.now()
            job.save()
            return Response(
                {'error': str(exc), 'job_id': str(job.id)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = self.get_serializer(job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── Activity Records ──────────────────────────────────────────────────────────

class ActivityRecordViewSet(ModelViewSet):
    http_method_names = ['get', 'patch', 'head', 'options', 'post']

    def get_queryset(self):
        qs = ActivityRecord.objects.select_related(
            'tenant', 'ingestion_job__data_source', 'raw_record'
        ).prefetch_related('edit_logs').order_by('-created_at')

        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        rec_status = self.request.query_params.get('status')
        if rec_status:
            qs = qs.filter(status=rec_status)

        source_type = self.request.query_params.get('source_type')
        if source_type:
            qs = qs.filter(ingestion_job__data_source__type=source_type)

        suspicious = self.request.query_params.get('suspicious')
        if suspicious == 'true':
            qs = qs.exclude(flags=[])

        job_id = self.request.query_params.get('job_id')
        if job_id:
            qs = qs.filter(ingestion_job_id=job_id)

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ActivityRecordDetailSerializer
        if self.action == 'partial_update':
            return ActivityRecordPatchSerializer
        return ActivityRecordListSerializer

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.status == 'APPROVED':
            return Response(
                {'error': 'Cannot edit an approved (locked) record.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Snapshot before
        before = {}
        after_data = {}
        for field in EDITABLE_FIELDS:
            val = getattr(instance, field)
            before[field] = val if not hasattr(val, 'isoformat') else val.isoformat()

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Snapshot after
        instance.refresh_from_db()
        changed = {}
        for field in request.data.keys():
            if field in EDITABLE_FIELDS:
                new_val = getattr(instance, field)
                after_data[field] = new_val if not hasattr(new_val, 'isoformat') else new_val.isoformat()
                if before.get(field) != after_data[field]:
                    changed[field] = True

        if changed:
            ActivityEditLog.objects.create(
                tenant=instance.tenant,
                activity_record=instance,
                edited_by=request.data.get('edited_by', 'analyst'),
                before={k: before[k] for k in changed},
                after={k: after_data[k] for k in changed},
                reason=request.data.get('reason'),
            )
            instance.edited_fields = {**instance.edited_fields, **changed}
            instance.save(update_fields=['edited_fields'])

        return Response(ActivityRecordDetailSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        instance = self.get_object()

        if instance.status == 'APPROVED':
            return Response({'error': 'Already approved.'}, status=status.HTTP_400_BAD_REQUEST)

        instance.status = 'APPROVED'
        instance.locked_at = timezone.now()
        instance.locked_by = request.data.get('approved_by', 'analyst')
        instance.save(update_fields=['status', 'locked_at', 'locked_by'])

        return Response(ActivityRecordDetailSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        instance = self.get_object()

        if instance.status == 'APPROVED':
            return Response({'error': 'Cannot reject an approved record.'}, status=status.HTTP_400_BAD_REQUEST)

        instance.status = 'REJECTED'
        instance.save(update_fields=['status'])
        return Response(ActivityRecordDetailSerializer(instance).data)


# ── Dashboard summary ─────────────────────────────────────────────────────────

class DashboardSummaryView(APIView):
    def get(self, request):
        tenant_id = request.query_params.get('tenant_id')
        qs = ActivityRecord.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        total = qs.count()
        pending = qs.filter(status='PENDING_REVIEW').count()
        approved = qs.filter(status='APPROVED').count()
        rejected = qs.filter(status='REJECTED').count()
        suspicious = qs.exclude(flags=[]).count()
        failed_raw = RawRecord.objects.filter(parse_status='FAILED')
        if tenant_id:
            failed_raw = failed_raw.filter(tenant_id=tenant_id)
        failed = failed_raw.count()

        return Response({
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'suspicious': suspicious,
            'failed': failed,
        })
