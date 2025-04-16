import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

# Add the root directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.api import api_router
from app.api.deps import get_current_active_admin_user, get_current_active_superuser, get_current_active_user, get_current_user
from app.core.config import settings
from app.db.models import User, UserRole
from app.db.session import get_session

# Test database for this specific test
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_organizations.db"

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)

# Create test session
test_session_maker = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_test_session() -> AsyncSession:
    async with test_session_maker() as session:
        yield session


# App for testing
def create_test_app():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(api_router, prefix=settings.API_V1_STR)
    return app


# Test auth class that always returns the provided user
class TestAuth:
    def __init__(self, user: User):
        self.user = user

    async def __call__(self, *args, **kwargs):
        return self.user


@pytest_asyncio.fixture(scope="function")
async def setup_test_db():
    # Create the test database and tables
    # Generate a unique database name for each test
    db_name = f"./test_organizations_{id(setup_test_db)}.db"
    
    # Remove test database if it exists
    if Path(db_name).exists():
        Path(db_name).unlink()
        
    # Create a connection engine for this specific test
    test_engine_local = create_async_engine(
        f"sqlite+aiosqlite:///{db_name}",
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )
    
    # Create test session maker for this test
    local_session_maker = sessionmaker(
        test_engine_local, class_=AsyncSession, expire_on_commit=False
    )
    
    # Provide the session maker
    global test_session_maker
    test_session_maker = local_session_maker
        
    async with test_engine_local.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # Clean up after tests
    async with test_engine_local.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        
    # Remove test database file
    if Path(db_name).exists():
        Path(db_name).unlink()
        
        
@pytest_asyncio.fixture
async def test_db(setup_test_db):
    async with test_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture
async def test_superuser(test_db):
    """Create and return a superuser for testing."""
    from app.services.user import UserService
    
    user_service = UserService(test_db)
    user = await user_service.create_user(
        username="testsuper",
        email="super@example.com",
        password="password123",
        role=UserRole.SUPERUSER,
    )
    return user


@pytest_asyncio.fixture
async def test_admin_user(test_db):
    """Create and return an admin user for testing."""
    from app.services.user import UserService
    
    user_service = UserService(test_db)
    user = await user_service.create_user(
        username="testadmin",
        email="admin@example.com",
        password="password123",
        role=UserRole.ADMIN,
    )
    return user


@pytest_asyncio.fixture
async def test_normal_user(test_db):
    """Create and return a normal user for testing."""
    from app.services.user import UserService
    
    user_service = UserService(test_db)
    user = await user_service.create_user(
        username="testuser",
        email="user@example.com",
        password="password123",
        role=UserRole.USER,
    )
    return user


@pytest_asyncio.fixture
async def superuser_client(setup_test_db, test_superuser):
    """Client with superuser authentication."""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Override the dependencies
    app.dependency_overrides[get_session] = get_test_session
    
    # Create a function that returns the superuser
    async def override_get_current_user():
        return test_superuser
        
    async def override_get_current_active_user():
        return test_superuser
        
    async def override_get_current_active_superuser():
        return test_superuser
        
    async def override_get_current_active_admin_user():
        return test_superuser
    
    # Apply the overrides
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    app.dependency_overrides[get_current_active_superuser] = override_get_current_active_superuser
    app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user
    
    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def admin_client(setup_test_db, test_admin_user):
    """Client with admin authentication."""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Override the dependencies
    app.dependency_overrides[get_session] = get_test_session
    
    # Create a function that returns the admin user
    async def override_get_current_user():
        return test_admin_user
        
    async def override_get_current_active_user():
        return test_admin_user
        
    async def override_get_current_active_admin_user():
        return test_admin_user
    
    # Apply the overrides
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    app.dependency_overrides[get_current_active_admin_user] = override_get_current_active_admin_user
    
    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def normal_client(setup_test_db, test_normal_user):
    """Client with normal user authentication."""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Override the dependencies
    app.dependency_overrides[get_session] = get_test_session
    
    # Create a function that returns the normal user
    async def override_get_current_user():
        return test_normal_user
        
    async def override_get_current_active_user():
        return test_normal_user
    
    # Apply the overrides
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_create_organization(superuser_client):
    # Generate a unique organization name for each test run
    import time
    org_name = f"Test Organization {time.time()}"
    
    # Test creating a new organization with superuser
    response = await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name, "description": "This is a test organization"}
    )
    
    # Print the response for debugging
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == org_name
    assert data["description"] == "This is a test organization"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_regular_user_cannot_create_organization(normal_client):
    # Regular users should not be able to create organizations
    response = await normal_client.post(
        "/api/v1/organizations/",
        json={"name": "Unauthorized Org", "description": "This should not be created"}
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_organization(superuser_client):
    # Generate a unique organization name
    import time
    org_name = f"Get Org {time.time()}"
    
    # First create an organization
    create_response = await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name, "description": "Organization to retrieve"}
    )
    
    org_id = create_response.json()["id"]
    
    # Now get the organization
    response = await superuser_client.get(
        f"/api/v1/organizations/{org_id}"
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == org_id
    assert data["name"] == org_name
    assert data["description"] == "Organization to retrieve"


@pytest.mark.asyncio
async def test_get_nonexistent_organization(superuser_client):
    # Try to get an organization that doesn't exist
    response = await superuser_client.get(
        "/api/v1/organizations/99999"
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_all_organizations(superuser_client):
    # Generate unique organization names
    import time
    timestamp = time.time()
    org_name1 = f"Org List 1 {timestamp}"
    org_name2 = f"Org List 2 {timestamp}"
    
    # Create multiple organizations
    await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name1, "description": "First org for list test"}
    )
    
    await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name2, "description": "Second org for list test"}
    )
    
    # Get all organizations
    response = await superuser_client.get(
        "/api/v1/organizations/"
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    
    # Check if our organizations are in the list
    org_names = [org["name"] for org in data]
    assert org_name1 in org_names
    assert org_name2 in org_names


@pytest.mark.asyncio
async def test_update_organization(superuser_client):
    # Generate unique organization names
    import time
    timestamp = time.time()
    org_name = f"Update Test Org {timestamp}"
    updated_name = f"Updated Org {timestamp}"
    
    # First create an organization
    create_response = await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name, "description": "Will be updated"}
    )
    
    org_id = create_response.json()["id"]
    
    # Now update the organization
    response = await superuser_client.put(
        f"/api/v1/organizations/{org_id}",
        json={"name": updated_name, "description": "Has been updated"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == org_id
    assert data["name"] == updated_name
    assert data["description"] == "Has been updated"


@pytest.mark.asyncio
async def test_delete_organization(superuser_client):
    # Generate a unique organization name
    import time
    org_name = f"Delete Test Org {time.time()}"
    
    # First create an organization
    create_response = await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name, "description": "Will be deleted"}
    )
    
    org_id = create_response.json()["id"]
    
    # Now delete the organization
    response = await superuser_client.delete(
        f"/api/v1/organizations/{org_id}"
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify the organization is gone
    get_response = await superuser_client.get(
        f"/api/v1/organizations/{org_id}"
    )
    
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_add_user_to_organization(superuser_client, test_normal_user):
    # Generate a unique organization name
    import time
    org_name = f"User Org {time.time()}"
    
    # First create an organization
    org_response = await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name, "description": "Organization for user assignment"}
    )
    
    assert org_response.status_code == status.HTTP_201_CREATED
    org_id = org_response.json()["id"]
    
    # Add user to organization
    uri = f"/api/v1/organizations/{org_id}/users/{test_normal_user.id}"
    
    response = await superuser_client.post(uri)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_normal_user.id
    assert data["organization_id"] == org_id


@pytest.mark.asyncio
async def test_remove_user_from_organization(superuser_client, test_normal_user):
    # Generate a unique organization name
    import time
    org_name = f"User Remove Org {time.time()}"
    
    # First create an organization
    org_response = await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name, "description": "Organization for user removal"}
    )
    
    assert org_response.status_code == status.HTTP_201_CREATED
    org_id = org_response.json()["id"]
    
    # Add user to organization
    add_uri = f"/api/v1/organizations/{org_id}/users/{test_normal_user.id}"
    add_response = await superuser_client.post(add_uri)
    
    # Remove user from organization
    remove_uri = f"/api/v1/organizations/{org_id}/users/{test_normal_user.id}"
    
    response = await superuser_client.delete(remove_uri)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_normal_user.id
    assert data["organization_id"] is None


@pytest.mark.asyncio
async def test_get_organization_users(superuser_client):
    # Generate a unique organization name
    import time
    timestamp = time.time()
    org_name = f"Multi User Org {timestamp}"
    
    # First create an organization
    org_response = await superuser_client.post(
        "/api/v1/organizations/",
        json={"name": org_name, "description": "Organization with multiple users"}
    )
    
    org_id = org_response.json()["id"]
    
    # Import the user service
    from app.services.user import UserService
    
    # Create users
    user_ids = []
    for i in range(3):
        # Create a user directly with the service instead of the API
        async with test_session_maker() as db:
            user_service = UserService(db)
            test_user = await user_service.create_user(
                username=f"orguser{i}_{timestamp}",
                email=f"orguser{i}_{timestamp}@example.com",
                password="password123",
                role=UserRole.USER
            )
        user_ids.append(test_user.id)
        
        # Add user to organization
        await superuser_client.post(
            f"/api/v1/organizations/{org_id}/users/{user_ids[i]}"
        )
    
    # Get all users for the organization
    response = await superuser_client.get(
        f"/api/v1/organizations/{org_id}/users"
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    
    # Verify the user IDs match what we expect
    response_user_ids = [user["id"] for user in data]
    for user_id in user_ids:
        assert user_id in response_user_ids


@pytest.mark.asyncio
async def test_user_access_own_organization(admin_client, test_admin_user):
    # Generate a unique organization name
    import time
    org_name = f"Admin Org {time.time()}"
    
    # Create organization for the admin user
    org_response = await admin_client.post(
        "/api/v1/organizations/",
        json={"name": org_name, "description": "Organization for admin access test"}
    )
    
    org_id = org_response.json()["id"]
    
    # Add the admin user to their organization
    await admin_client.post(
        f"/api/v1/organizations/{org_id}/users/{test_admin_user.id}"
    )
    
    # Admin should be able to access their own organization
    response = await admin_client.get(
        f"/api/v1/organizations/{org_id}"
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == org_id