"""
User Management Service
Handles user authentication, authorization, and profile management
"""
import hashlib
import re
from typing import Optional, Dict, Any
from datetime import datetime


class UserManagementService:
    """Service for managing user operations"""

    def __init__(self):
        self.users = {}  # In-memory storage (use DB in production)

    def validate_email(self, email: str) -> bool:
        """
        Validate email format

        Args:
            email: Email address to validate

        Returns:
            bool: True if valid, False otherwise
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_password(self, password: str) -> tuple[bool, str]:
        """
        Validate password strength

        Requirements:
        - At least 8 characters
        - Contains uppercase and lowercase
        - Contains at least one digit
        - Contains at least one special character

        Args:
            password: Password to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        if not any(c.isupper() for c in password):
            return False, "Password must contain uppercase letter"

        if not any(c.islower() for c in password):
            return False, "Password must contain lowercase letter"

        if not any(c.isdigit() for c in password):
            return False, "Password must contain a digit"

        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            return False, "Password must contain a special character"

        return True, ""

    def hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """
        Create a new user account

        Args:
            email: User email address
            password: User password
            name: User full name

        Returns:
            dict: User creation result

        Raises:
            ValueError: If validation fails
        """
        # Validate email
        if not self.validate_email(email):
            raise ValueError("Invalid email format")

        # Check if user exists
        if email in self.users:
            raise ValueError("User already exists")

        # Validate password
        is_valid, error = self.validate_password(password)
        if not is_valid:
            raise ValueError(error)

        # Create user
        user = {
            'email': email,
            'password_hash': self.hash_password(password),
            'name': name,
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }

        self.users[email] = user

        return {
            'success': True,
            'email': email,
            'name': name,
            'created_at': user['created_at']
        }

    def authenticate(self, email: str, password: str) -> bool:
        """
        Authenticate user with email and password

        Args:
            email: User email
            password: User password

        Returns:
            bool: True if authenticated, False otherwise
        """
        if email not in self.users:
            return False

        user = self.users[email]

        if not user.get('is_active', False):
            return False

        password_hash = self.hash_password(password)
        return user['password_hash'] == password_hash

    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user details by email

        Args:
            email: User email

        Returns:
            dict or None: User details without password
        """
        if email not in self.users:
            return None

        user = self.users[email].copy()
        user.pop('password_hash', None)  # Remove sensitive data
        return user

    def update_user(self, email: str, **kwargs) -> bool:
        """
        Update user information

        Args:
            email: User email
            **kwargs: Fields to update (name, is_active)

        Returns:
            bool: True if updated, False if user not found
        """
        if email not in self.users:
            return False

        allowed_fields = {'name', 'is_active'}
        for key, value in kwargs.items():
            if key in allowed_fields:
                self.users[email][key] = value

        return True

    def delete_user(self, email: str) -> bool:
        """
        Delete user account

        Args:
            email: User email

        Returns:
            bool: True if deleted, False if user not found
        """
        if email not in self.users:
            return False

        del self.users[email]
        return True

    def list_users(self) -> list:
        """
        List all users

        Returns:
            list: List of users without passwords
        """
        users_list = []
        for email, user in self.users.items():
            user_copy = user.copy()
            user_copy.pop('password_hash', None)
            users_list.append(user_copy)
        return users_list
