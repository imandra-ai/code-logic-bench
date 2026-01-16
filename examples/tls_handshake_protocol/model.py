from enum import Enum, auto
from dataclasses import dataclass


class CipherSuite(Enum):
    """TLS cipher suite options."""

    AES_256_GCM = auto()
    AES_128_GCM = auto()


class CertificateStatus(Enum):
    """Certificate validation status."""

    VALID = auto()
    INVALID = auto()


class KeyExchangeGroup(Enum):
    """Key exchange group options."""

    SECP256R1 = auto()
    X25519 = auto()


class HandshakeOutcome(Enum):
    """Possible outcomes of a TLS handshake."""

    FULL_HANDSHAKE_SUCCESS = auto()
    SESSION_RESUMPTION_SUCCESS = auto()
    SECURITY_DOWNGRADE = auto()
    CERTIFICATE_FAILURE = auto()
    COMPATIBILITY_FAILURE = auto()
    REPLAY_ATTACK = auto()
    INVALID_STATE = auto()


@dataclass
class HandshakeDecision:
    """Result of handshake determination."""

    outcome: HandshakeOutcome
    forward_secrecy: bool
    cipher_strength: int
    can_proceed: bool


def cipher_strength(cipher: CipherSuite) -> int:
    """Return the strength in bits of the given cipher suite."""
    return {
        CipherSuite.AES_256_GCM: 256,
        CipherSuite.AES_128_GCM: 128,
    }[cipher]


def has_compatible_cipher(
    client_cipher: CipherSuite, server_cipher: CipherSuite
) -> bool:
    """Check if client and server cipher suites are compatible."""
    return client_cipher == server_cipher


def has_compatible_group(
    client_group: KeyExchangeGroup, server_group: KeyExchangeGroup
) -> bool:
    """Check if client and server key exchange groups are compatible."""
    return client_group == server_group


def provides_forward_secrecy(group: KeyExchangeGroup) -> bool:
    """Check if the key exchange group provides forward secrecy."""
    return group == KeyExchangeGroup.X25519


def minimum_cipher_strength_for_policy(security_policy_level: int) -> int:
    """Determine minimum acceptable cipher strength based on security policy."""
    if security_policy_level >= 3:
        return 256
    elif security_policy_level >= 2:
        return 192
    else:
        return 128


def resumption_allowed_by_policy(security_policy_level: int, session_age: int) -> bool:
    """Check if resumption is allowed based on security policy."""
    # High security policy overrides resumption
    if security_policy_level >= 4:
        return False
    # Sessions aged 86400-86410 are ambiguous
    elif 86400 <= session_age <= 86410:
        return False
    else:
        return session_age < 86400


def determine_handshake_outcome(
    client_cipher: CipherSuite,
    server_cipher: CipherSuite,
    client_group: KeyExchangeGroup,
    server_group: KeyExchangeGroup,
    cert_status: CertificateStatus,
    has_session_ticket: bool,
    ticket_is_valid: bool,
    resumption_policy_ok: bool,
    replay_detected: bool,
    security_policy_level: int,
    error_count: int,
) -> HandshakeDecision:
    """
    Determine the outcome of a TLS 1.3 handshake.

    This function evaluates all aspects of a TLS handshake including cipher suite
    compatibility, certificate validity, session resumption, and security policies
    to determine whether the handshake succeeds and what properties it provides.
    """
    # Check for replay attack first (security critical)
    if replay_detected:
        return HandshakeDecision(
            outcome=HandshakeOutcome.REPLAY_ATTACK,
            forward_secrecy=False,
            cipher_strength=0,
            can_proceed=False,
        )

    # Check error threshold
    if error_count >= 3:
        return HandshakeDecision(
            outcome=HandshakeOutcome.INVALID_STATE,
            forward_secrecy=False,
            cipher_strength=0,
            can_proceed=False,
        )

    # Check basic compatibility
    if not has_compatible_cipher(client_cipher, server_cipher):
        return HandshakeDecision(
            outcome=HandshakeOutcome.COMPATIBILITY_FAILURE,
            forward_secrecy=False,
            cipher_strength=0,
            can_proceed=False,
        )

    if not has_compatible_group(client_group, server_group):
        return HandshakeDecision(
            outcome=HandshakeOutcome.COMPATIBILITY_FAILURE,
            forward_secrecy=False,
            cipher_strength=0,
            can_proceed=False,
        )

    # security_policy_level changes requirements
    min_strength = minimum_cipher_strength_for_policy(security_policy_level)
    actual_strength = cipher_strength(client_cipher)

    # Check if cipher meets policy requirements
    if actual_strength < min_strength:
        return HandshakeDecision(
            outcome=HandshakeOutcome.SECURITY_DOWNGRADE,
            forward_secrecy=False,
            cipher_strength=actual_strength,
            can_proceed=False,
        )

    # Attempt session resumption if ticket exists
    if has_session_ticket:
        # Valid ticket BUT policy can override
        if ticket_is_valid and resumption_policy_ok:
            return HandshakeDecision(
                outcome=HandshakeOutcome.SESSION_RESUMPTION_SUCCESS,
                forward_secrecy=False,  # PSK doesn't provide forward secrecy
                cipher_strength=actual_strength,
                can_proceed=True,
            )
        else:
            # Ticket invalid or policy blocks it, fall through to full handshake
            if cert_status == CertificateStatus.INVALID:
                return HandshakeDecision(
                    outcome=HandshakeOutcome.CERTIFICATE_FAILURE,
                    forward_secrecy=False,
                    cipher_strength=0,
                    can_proceed=False,
                )
            else:
                fs = provides_forward_secrecy(client_group)
                # High security policy requires forward secrecy
                if security_policy_level >= 4 and not fs:
                    return HandshakeDecision(
                        outcome=HandshakeOutcome.SECURITY_DOWNGRADE,
                        forward_secrecy=False,
                        cipher_strength=actual_strength,
                        can_proceed=False,
                    )
                else:
                    return HandshakeDecision(
                        outcome=HandshakeOutcome.FULL_HANDSHAKE_SUCCESS,
                        forward_secrecy=fs,
                        cipher_strength=actual_strength,
                        can_proceed=True,
                    )

    # No session ticket, perform full handshake
    else:
        if cert_status == CertificateStatus.INVALID:
            return HandshakeDecision(
                outcome=HandshakeOutcome.CERTIFICATE_FAILURE,
                forward_secrecy=False,
                cipher_strength=0,
                can_proceed=False,
            )
        else:
            fs = provides_forward_secrecy(client_group)
            # High security policy requires forward secrecy
            if security_policy_level >= 4 and not fs:
                return HandshakeDecision(
                    outcome=HandshakeOutcome.SECURITY_DOWNGRADE,
                    forward_secrecy=False,
                    cipher_strength=actual_strength,
                    can_proceed=False,
                )
            else:
                return HandshakeDecision(
                    outcome=HandshakeOutcome.FULL_HANDSHAKE_SUCCESS,
                    forward_secrecy=fs,
                    cipher_strength=actual_strength,
                    can_proceed=True,
                )
