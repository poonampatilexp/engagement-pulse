import pytest
from scoring_service import recalculate_project_score
import models


def test_scoring_weights_and_recalculation(db_session):
    # Verify default scoring weights exist
    sev_weights = {
        sw.severity: sw.weight
        for sw in db_session.query(models.SeverityWeight).all()
    }
    assert sev_weights["low"] == 1
    assert sev_weights["medium"] == 2
    assert sev_weights["high"] == 3
    assert sev_weights["critical"] == 4

    stat_weights = {
        sw.status: sw.weight
        for sw in db_session.query(models.StatusWeight).all()
    }
    assert stat_weights["open"] == 3
    assert stat_weights["mitigating"] == 2
    assert stat_weights["closed"] == 0

    # Test recalculate_project_score on existing project if available
    project = db_session.query(models.Project).first()
    if project:
        score = recalculate_project_score(db_session, project.id)
        assert 0 <= score <= 100
        assert project.risk_score == score

