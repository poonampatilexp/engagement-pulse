from rest_framework import serializers
from apps.projects.models import (
    Project,
    Risk,
    RiskSeverity,
    RiskStatus,
    CSVImportJob,
    JobStatus,
)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id',
            'organisation',
            'name',
            'risk_score',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organisation',
            'risk_score',
            'created_at',
            'updated_at',
        ]


class RiskSerializer(serializers.ModelSerializer):
    severity = serializers.ChoiceField(choices=RiskSeverity.choices)
    status = serializers.ChoiceField(choices=RiskStatus.choices, default=RiskStatus.OPEN)

    class Meta:
        model = Risk
        fields = [
            'id',
            'project',
            'title',
            'description',
            'severity',
            'status',
            'owner',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'project',
            'created_at',
            'updated_at',
        ]


class CSVImportJobSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source='id', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)

    class Meta:
        model = CSVImportJob
        fields = [
            'id',
            'job_id',
            'project',
            'project_name',
            'filename',
            'status',
            'total_rows',
            'processed_rows',
            'error_details',
            'created_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class CSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    def validate_file(self, value):
        if not value.name.lower().endswith('.csv'):
            raise serializers.ValidationError('Only .csv files are supported.')
        if value.size == 0:
            raise serializers.ValidationError('The uploaded CSV file is empty.')
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('File size exceeds the 10MB limit.')
        return value


