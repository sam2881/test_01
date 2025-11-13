import pytest
from user_management_service import UserManagementService

@pytest.fixture
def user_service():
    return UserManagementService()

@pytest.fixture
def user_data():
    return {
        'email': 'test@example.com',
        'password': 'Test@1234',
        'name': 'Test User'
    }

def test_validate_email(user_service):
    """Test email validation with valid and invalid formats"""
    assert user_service.validate_email('test@example.com')
    assert not user_service.validate_email('invalid_email')

def test_validate_password(user_service):
    """Test password validation with all security requirements"""
    assert user_service.validate_password('Test@1234') == (True, "")
    assert user_service.validate_password('test') == (False, "Password must be at least 8 characters")
    assert user_service.validate_password('TEST@1234') == (False, "Password must contain lowercase letter")
    assert user_service.validate_password('Test1234') == (False, "Password must contain a special character")

def test_create_user(user_service, user_data):
    """Test user creation (success and failure cases)"""
    user = user_service.create_user(**user_data)
    assert user['success']
    assert user['email'] == user_data['email']
    assert user['name'] == user_data['name']

    with pytest.raises(ValueError, match="User already exists"):
        user_service.create_user(**user_data)

def test_authenticate(user_service, user_data):
    """Test authentication (valid/invalid credentials)"""
    user_service.create_user(**user_data)
    assert user_service.authenticate(user_data['email'], user_data['password'])
    assert not user_service.authenticate(user_data['email'], 'wrong_password')

def test_user_crud_operations(user_service, user_data):
    """Test user CRUD operations (get, update, delete)"""
    user_service.create_user(**user_data)

    user = user_service.get_user(user_data['email'])
    assert user['email'] == user_data['email']
    assert user['name'] == user_data['name']

    assert user_service.update_user(user_data['email'], name='Updated User')
    updated_user = user_service.get_user(user_data['email'])
    assert updated_user['name'] == 'Updated User'

    assert user_service.delete_user(user_data['email'])
    assert user_service.get_user(user_data['email']) is None

def test_edge_cases(user_service):
    """Test edge cases (empty values, null values, SQL injection attempts)"""
    with pytest.raises(ValueError, match="Invalid email format"):
        user_service.create_user('', 'Test@1234', 'Test User')

    with pytest.raises(ValueError, match="Password must be at least 8 characters"):
        user_service.create_user('test@example.com', '', 'Test User')

    with pytest.raises(TypeError):
        user_service.create_user(None, 'Test@1234', 'Test User')

    with pytest.raises(ValueError, match="Password must be at least 8 characters"):
        user_service.create_user('test@example.com', None, 'Test User')

    with pytest.raises(ValueError, match="Invalid email format"):
        user_service.create_user('test@example.com; DROP TABLE users;', 'Test@1234', 'Test User')

def test_inactive_user_authentication(user_service, user_data):
    """Test inactive user authentication"""
    user_service.create_user(**user_data)
    user_service.update_user(user_data['email'], is_active=False)
    assert not user_service.authenticate(user_data['email'], user_data['password'])