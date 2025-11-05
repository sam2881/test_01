"""
User Management Service
A comprehensive user management system with authentication, validation, and database operations
"""
import re
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from enum import Enum


class UserRole(Enum):
    """User role enumeration"""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    PENDING_VERIFICATION = "pending_verification"


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass


class DatabaseError(Exception):
    """Custom exception for database errors"""
    pass


class User:
    """
    User entity representing a system user
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        status: UserStatus = UserStatus.PENDING_VERIFICATION,
        created_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.status = status
        self.created_at = created_at or datetime.now()
        self.last_login = last_login
        self.failed_login_attempts = 0
        self.locked_until: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

    def is_active(self) -> bool:
        """Check if user account is active"""
        return self.status == UserStatus.ACTIVE

    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if self.locked_until and datetime.now() < self.locked_until:
            return True
        return False


class UserValidator:
    """
    Validates user input data
    """

    # Validation rules
    USERNAME_MIN_LENGTH = 3
    USERNAME_MAX_LENGTH = 30
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128

    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]+$')

    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"

        if len(email) > 254:
            return False, "Email is too long"

        if not cls.EMAIL_REGEX.match(email):
            return False, "Invalid email format"

        return True, None

    @classmethod
    def validate_username(cls, username: str) -> Tuple[bool, Optional[str]]:
        """
        Validate username format

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not username:
            return False, "Username is required"

        if len(username) < cls.USERNAME_MIN_LENGTH:
            return False, f"Username must be at least {cls.USERNAME_MIN_LENGTH} characters"

        if len(username) > cls.USERNAME_MAX_LENGTH:
            return False, f"Username must not exceed {cls.USERNAME_MAX_LENGTH} characters"

        if not cls.USERNAME_REGEX.match(username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"

        return True, None

    @classmethod
    def validate_password(cls, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength

        Requirements:
        - Minimum length
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"

        if len(password) < cls.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {cls.PASSWORD_MIN_LENGTH} characters"

        if len(password) > cls.PASSWORD_MAX_LENGTH:
            return False, f"Password must not exceed {cls.PASSWORD_MAX_LENGTH} characters"

        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        return True, None


class PasswordHasher:
    """
    Handles password hashing and verification
    """

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash password using SHA-256 with salt

        Args:
            password: Plain text password
            salt: Optional salt (generates new one if not provided)

        Returns:
            Tuple of (password_hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)

        hash_input = f"{password}{salt}".encode('utf-8')
        password_hash = hashlib.sha256(hash_input).hexdigest()

        return password_hash, salt

    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """
        Verify password against stored hash

        Args:
            password: Plain text password to verify
            password_hash: Stored password hash
            salt: Salt used for hashing

        Returns:
            True if password matches, False otherwise
        """
        calculated_hash, _ = PasswordHasher.hash_password(password, salt)
        return calculated_hash == password_hash


class UserManagementService:
    """
    Main service for user management operations
    """

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    def __init__(self):
        # In-memory storage (would be database in production)
        self.users: Dict[int, User] = {}
        self.username_index: Dict[str, int] = {}
        self.email_index: Dict[str, int] = {}
        self.password_salts: Dict[int, str] = {}
        self.next_user_id = 1

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER
    ) -> User:
        """
        Create a new user account

        Args:
            username: Desired username
            email: User email address
            password: Plain text password
            role: User role (default: USER)

        Returns:
            Created User object

        Raises:
            ValidationError: If validation fails
            DatabaseError: If user already exists
        """
        # Validate inputs
        is_valid, error = UserValidator.validate_username(username)
        if not is_valid:
            raise ValidationError(f"Invalid username: {error}")

        is_valid, error = UserValidator.validate_email(email)
        if not is_valid:
            raise ValidationError(f"Invalid email: {error}")

        is_valid, error = UserValidator.validate_password(password)
        if not is_valid:
            raise ValidationError(f"Invalid password: {error}")

        # Check for duplicates
        if username.lower() in self.username_index:
            raise DatabaseError(f"Username '{username}' already exists")

        if email.lower() in self.email_index:
            raise DatabaseError(f"Email '{email}' already registered")

        # Hash password
        password_hash, salt = PasswordHasher.hash_password(password)

        # Create user
        user = User(
            user_id=self.next_user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            status=UserStatus.PENDING_VERIFICATION
        )

        # Store user
        self.users[user.user_id] = user
        self.username_index[username.lower()] = user.user_id
        self.email_index[email.lower()] = user.user_id
        self.password_salts[user.user_id] = salt

        self.next_user_id += 1

        return user

    def authenticate_user(self, username: str, password: str) -> User:
        """
        Authenticate user with username and password

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            Authenticated User object

        Raises:
            AuthenticationError: If authentication fails
        """
        # Find user by username or email
        user_id = self.username_index.get(username.lower()) or self.email_index.get(username.lower())

        if not user_id or user_id not in self.users:
            raise AuthenticationError("Invalid username or password")

        user = self.users[user_id]

        # Check if account is locked
        if user.is_locked():
            locked_minutes = int((user.locked_until - datetime.now()).total_seconds() / 60)
            raise AuthenticationError(f"Account is locked. Try again in {locked_minutes} minutes")

        # Check if account is active
        if not user.is_active():
            raise AuthenticationError(f"Account is {user.status.value}")

        # Verify password
        salt = self.password_salts.get(user_id)
        if not salt or not PasswordHasher.verify_password(password, user.password_hash, salt):
            user.failed_login_attempts += 1

            # Lock account after max attempts
            if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                raise AuthenticationError(
                    f"Too many failed login attempts. Account locked for {self.LOCKOUT_DURATION_MINUTES} minutes"
                )

            raise AuthenticationError("Invalid username or password")

        # Successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now()

        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        user_id = self.username_index.get(username.lower())
        return self.users.get(user_id) if user_id else None

    def update_user_role(self, user_id: int, new_role: UserRole) -> bool:
        """
        Update user role

        Args:
            user_id: User ID
            new_role: New role to assign

        Returns:
            True if successful, False if user not found
        """
        user = self.users.get(user_id)
        if not user:
            return False

        user.role = new_role
        return True

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if successful

        Raises:
            AuthenticationError: If old password is incorrect
            ValidationError: If new password is invalid
        """
        user = self.users.get(user_id)
        if not user:
            raise AuthenticationError("User not found")

        # Verify old password
        salt = self.password_salts.get(user_id)
        if not salt or not PasswordHasher.verify_password(old_password, user.password_hash, salt):
            raise AuthenticationError("Current password is incorrect")

        # Validate new password
        is_valid, error = UserValidator.validate_password(new_password)
        if not is_valid:
            raise ValidationError(f"Invalid new password: {error}")

        # Hash and update password
        password_hash, new_salt = PasswordHasher.hash_password(new_password)
        user.password_hash = password_hash
        self.password_salts[user_id] = new_salt

        return True

    def suspend_user(self, user_id: int) -> bool:
        """Suspend user account"""
        user = self.users.get(user_id)
        if not user:
            return False

        user.status = UserStatus.SUSPENDED
        return True

    def activate_user(self, user_id: int) -> bool:
        """Activate user account"""
        user = self.users.get(user_id)
        if not user:
            return False

        user.status = UserStatus.ACTIVE
        return True

    def delete_user(self, user_id: int) -> bool:
        """
        Soft delete user account

        Args:
            user_id: User ID to delete

        Returns:
            True if successful, False if user not found
        """
        user = self.users.get(user_id)
        if not user:
            return False

        user.status = UserStatus.DELETED
        return True

    def list_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        limit: int = 100
    ) -> List[User]:
        """
        List users with optional filters

        Args:
            role: Filter by role
            status: Filter by status
            limit: Maximum number of users to return

        Returns:
            List of User objects
        """
        users = list(self.users.values())

        if role:
            users = [u for u in users if u.role == role]

        if status:
            users = [u for u in users if u.status == status]

        return users[:limit]

    def get_user_count(self) -> Dict[str, int]:
        """
        Get count of users by status

        Returns:
            Dictionary with status counts
        """
        counts = {status.value: 0 for status in UserStatus}

        for user in self.users.values():
            counts[user.status.value] += 1

        counts['total'] = len(self.users)
        return counts


if __name__ == "__main__":
    # Demo usage
    print("User Management Service Demo")
    print("=" * 50)

    service = UserManagementService()

    # Create users
    try:
        admin = service.create_user("admin_user", "admin@example.com", "Admin@123!", UserRole.ADMIN)
        print(f"✓ Created admin user: {admin.username}")

        user1 = service.create_user("john_doe", "john@example.com", "SecurePass1!")
        print(f"✓ Created user: {user1.username}")

        # Activate users
        service.activate_user(admin.user_id)
        service.activate_user(user1.user_id)

        # Authenticate
        authenticated = service.authenticate_user("john_doe", "SecurePass1!")
        print(f"✓ Authenticated: {authenticated.username}")

        # Get user count
        counts = service.get_user_count()
        print(f"✓ User counts: {counts}")

    except (ValidationError, AuthenticationError, DatabaseError) as e:
        print(f"✗ Error: {e}")
