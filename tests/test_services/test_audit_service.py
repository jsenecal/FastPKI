from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.db.models import AuditAction
from app.services.audit import AuditService

UTC = ZoneInfo("UTC")


@pytest.mark.asyncio
async def test_log_action_creates_entry(db):
    audit = AuditService(db)
    entry = await audit.log_action(
        action=AuditAction.CA_CREATE,
        user_id=1,
        username="testuser",
        organization_id=10,
        resource_type="ca",
        resource_id=42,
        detail="Created CA 'MyCA'",
    )
    assert entry.id is not None
    assert entry.action == AuditAction.CA_CREATE
    assert entry.user_id == 1
    assert entry.username == "testuser"
    assert entry.organization_id == 10
    assert entry.resource_type == "ca"
    assert entry.resource_id == 42
    assert entry.detail == "Created CA 'MyCA'"


@pytest.mark.asyncio
async def test_log_action_minimal_fields(db):
    audit = AuditService(db)
    entry = await audit.log_action(action=AuditAction.LOGIN_FAILURE)
    assert entry.id is not None
    assert entry.action == AuditAction.LOGIN_FAILURE
    assert entry.user_id is None
    assert entry.username is None
    assert entry.organization_id is None
    assert entry.resource_type is None
    assert entry.resource_id is None
    assert entry.detail is None


@pytest.mark.asyncio
async def test_log_action_login_failure_no_user_id(db):
    audit = AuditService(db)
    entry = await audit.log_action(
        action=AuditAction.LOGIN_FAILURE,
        username="unknown_user",
    )
    assert entry.user_id is None
    assert entry.username == "unknown_user"


@pytest.mark.asyncio
async def test_log_action_sets_created_at(db):
    audit = AuditService(db)
    before = datetime.now(UTC)
    entry = await audit.log_action(action=AuditAction.LOGIN_SUCCESS, user_id=1)
    after = datetime.now(UTC)
    assert entry.created_at is not None
    assert before <= entry.created_at.replace(tzinfo=UTC) <= after


@pytest.mark.asyncio
async def test_list_audit_logs_returns_all(db):
    audit = AuditService(db)
    await audit.log_action(action=AuditAction.CA_CREATE, user_id=1)
    await audit.log_action(action=AuditAction.CERT_CREATE, user_id=2)
    await audit.log_action(action=AuditAction.LOGIN_SUCCESS, user_id=3)

    logs = await audit.list_audit_logs()
    assert len(logs) == 3


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_action(db):
    audit = AuditService(db)
    await audit.log_action(action=AuditAction.CA_CREATE, user_id=1)
    await audit.log_action(action=AuditAction.CERT_CREATE, user_id=2)
    await audit.log_action(action=AuditAction.CA_CREATE, user_id=3)

    logs = await audit.list_audit_logs(action=AuditAction.CA_CREATE)
    assert len(logs) == 2
    assert all(log.action == AuditAction.CA_CREATE for log in logs)


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_user_id(db):
    audit = AuditService(db)
    await audit.log_action(action=AuditAction.CA_CREATE, user_id=1)
    await audit.log_action(action=AuditAction.CERT_CREATE, user_id=2)
    await audit.log_action(action=AuditAction.CA_DELETE, user_id=1)

    logs = await audit.list_audit_logs(user_id=1)
    assert len(logs) == 2
    assert all(log.user_id == 1 for log in logs)


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_organization_id(db):
    audit = AuditService(db)
    await audit.log_action(action=AuditAction.CA_CREATE, organization_id=10)
    await audit.log_action(action=AuditAction.CERT_CREATE, organization_id=20)
    await audit.log_action(action=AuditAction.CA_DELETE, organization_id=10)

    logs = await audit.list_audit_logs(organization_id=10)
    assert len(logs) == 2
    assert all(log.organization_id == 10 for log in logs)


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_resource_type(db):
    audit = AuditService(db)
    await audit.log_action(action=AuditAction.CA_CREATE, resource_type="ca")
    await audit.log_action(action=AuditAction.CERT_CREATE, resource_type="certificate")
    await audit.log_action(action=AuditAction.CA_DELETE, resource_type="ca")

    logs = await audit.list_audit_logs(resource_type="ca")
    assert len(logs) == 2
    assert all(log.resource_type == "ca" for log in logs)


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_resource_id(db):
    audit = AuditService(db)
    await audit.log_action(
        action=AuditAction.CA_CREATE, resource_type="ca", resource_id=1
    )
    await audit.log_action(
        action=AuditAction.CERT_CREATE, resource_type="certificate", resource_id=2
    )
    await audit.log_action(
        action=AuditAction.CA_DELETE, resource_type="ca", resource_id=1
    )

    logs = await audit.list_audit_logs(resource_id=1)
    assert len(logs) == 2
    assert all(log.resource_id == 1 for log in logs)


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_since(db):
    audit = AuditService(db)
    await audit.log_action(action=AuditAction.CA_CREATE)
    cutoff = datetime.now(UTC)
    await audit.log_action(action=AuditAction.CERT_CREATE)

    logs = await audit.list_audit_logs(since=cutoff)
    assert len(logs) == 1
    assert logs[0].action == AuditAction.CERT_CREATE


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_until(db):
    audit = AuditService(db)
    await audit.log_action(action=AuditAction.CA_CREATE)
    cutoff = datetime.now(UTC)
    await audit.log_action(action=AuditAction.CERT_CREATE)

    logs = await audit.list_audit_logs(until=cutoff)
    assert len(logs) == 1
    assert logs[0].action == AuditAction.CA_CREATE


@pytest.mark.asyncio
async def test_list_audit_logs_pagination(db):
    audit = AuditService(db)
    for i in range(5):
        await audit.log_action(action=AuditAction.CA_CREATE, user_id=i)

    page1 = await audit.list_audit_logs(skip=0, limit=2)
    page2 = await audit.list_audit_logs(skip=2, limit=2)
    page3 = await audit.list_audit_logs(skip=4, limit=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1


@pytest.mark.asyncio
async def test_list_audit_logs_ordered_newest_first(db):
    audit = AuditService(db)
    await audit.log_action(action=AuditAction.CA_CREATE, detail="first")
    await audit.log_action(action=AuditAction.CERT_CREATE, detail="second")
    await audit.log_action(action=AuditAction.CA_DELETE, detail="third")

    logs = await audit.list_audit_logs()
    assert logs[0].detail == "third"
    assert logs[1].detail == "second"
    assert logs[2].detail == "first"
