from enum import Enum
from dataclasses import dataclass
from typing import NamedTuple


class AuthFactor(Enum):
    """Authentication factor types."""

    PASSWORD = "password"
    TOTP = "totp"
    BIOMETRIC = "biometric"
    TRUSTED_DEVICE = "trusted_device"


class UserStatus(Enum):
    """User account status."""

    ACTIVE = "active"
    LOCKED = "locked"
    SUSPENDED = "suspended"


class DeviceTrust(Enum):
    """Device trust levels."""

    UNKNOWN = "unknown"
    REGISTERED = "registered"
    TRUSTED = "trusted"
    COMPROMISED = "compromised"


class AuthDecision(NamedTuple):
    """Authentication decision result."""

    granted: bool
    requires_additional_factor: bool
    lock_account: bool
    step_up_auth_needed: bool


def user_can_auth(user_status: UserStatus) -> bool:
    """Check if user can authenticate."""
    return user_status == UserStatus.ACTIVE


def device_trusted(device_trust: DeviceTrust) -> bool:
    """Check if device is trusted."""
    return device_trust == DeviceTrust.TRUSTED


def should_lock_account(failed_attempts: int, max_attempts: int) -> bool:
    """Check if account should be locked due to failed attempts."""
    return failed_attempts >= max_attempts


def needs_step_up(high_value_operation: bool, auth_level: int) -> bool:
    """Require step-up authentication for sensitive operations."""
    return high_value_operation and auth_level < 2


def determine_auth_result(
    user_status: UserStatus,
    device_trust: DeviceTrust,
    password_correct: bool,
    totp_correct: bool,
    failed_attempts: int,
    max_failed_attempts: int,
    requires_mfa: bool,
    high_value_operation: bool,
) -> AuthDecision:
    """
    Determine authentication result based on multiple factors.

    Core authentication decision logic for multi-factor authentication system.
    Enforces account lockout, step-up authentication, and trusted device policies.

    Args:
        user_status: Current status of the user account
        device_trust: Trust level of the device being used
        password_correct: Whether the password was correct
        totp_correct: Whether the TOTP code was correct
        failed_attempts: Number of failed authentication attempts
        max_failed_attempts: Maximum allowed failed attempts before lockout
        requires_mfa: Whether MFA is required for this user
        high_value_operation: Whether this is a high-value/sensitive operation

    Returns:
        AuthDecision with granted status and additional requirements
    """
    # Check if user is locked
    if user_status == UserStatus.LOCKED:
        return AuthDecision(
            granted=False,
            requires_additional_factor=False,
            lock_account=True,
            step_up_auth_needed=False,
        )

    if user_status == UserStatus.SUSPENDED:
        return AuthDecision(
            granted=False,
            requires_additional_factor=False,
            lock_account=False,
            step_up_auth_needed=False,
        )

    # User is Active - check authentication
    can_auth = user_can_auth(user_status)

    if not can_auth:
        return AuthDecision(
            granted=False,
            requires_additional_factor=False,
            lock_account=False,
            step_up_auth_needed=False,
        )

    # Check password first
    if not password_correct:
        should_lock = should_lock_account(failed_attempts + 1, max_failed_attempts)
        return AuthDecision(
            granted=False,
            requires_additional_factor=False,
            lock_account=should_lock,
            step_up_auth_needed=False,
        )

    # Password correct - check if MFA required
    if requires_mfa:
        # MFA required
        if not totp_correct:
            return AuthDecision(
                granted=False,
                requires_additional_factor=True,
                lock_account=False,
                step_up_auth_needed=False,
            )
        else:
            # MFA passed - check step-up for high-value ops
            needs_stepup = needs_step_up(high_value_operation, 2)
            return AuthDecision(
                granted=True,
                requires_additional_factor=False,
                lock_account=False,
                step_up_auth_needed=needs_stepup,
            )
    else:
        # MFA not required
        trusted = device_trusted(device_trust)

        if trusted:
            # Trusted device: allow with password only
            needs_stepup = needs_step_up(high_value_operation, 1)
            return AuthDecision(
                granted=True,
                requires_additional_factor=False,
                lock_account=False,
                step_up_auth_needed=needs_stepup,
            )
        else:
            # Untrusted device: require additional factor
            return AuthDecision(
                granted=False,
                requires_additional_factor=True,
                lock_account=False,
                step_up_auth_needed=False,
            )
