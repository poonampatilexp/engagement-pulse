from rest_framework import serializers
from apps.projects.models import Project, Risk, RiskSeverity, RiskStatus


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

