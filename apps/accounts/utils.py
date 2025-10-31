"""
Utility functions for Chilean RUT validation and formatting.
"""
import re
from django.core.exceptions import ValidationError


def clean_rut(rut: str) -> str:
    """
    Remove formatting from RUT (dots, hyphens) and convert to uppercase.

    Args:
        rut: RUT string (e.g., "12.345.678-9" or "12345678-9")

    Returns:
        str: Cleaned RUT (e.g., "123456789")

    Example:
        >>> clean_rut("12.345.678-9")
        "123456789"
    """
    if not rut:
        return ""
    return rut.replace(".", "").replace("-", "").replace(" ", "").upper()


def format_rut(rut: str) -> str:
    """
    Format RUT with dots and hyphen (12.345.678-9).

    Args:
        rut: RUT string (cleaned or unformatted)

    Returns:
        str: Formatted RUT

    Example:
        >>> format_rut("123456789")
        "12.345.678-9"
    """
    cleaned = clean_rut(rut)
    if len(cleaned) < 2:
        return cleaned

    # Split into number and check digit
    number = cleaned[:-1]
    check_digit = cleaned[-1]

    # Add thousand separators
    reversed_number = number[::-1]
    groups = [reversed_number[i:i+3] for i in range(0, len(reversed_number), 3)]
    formatted_number = '.'.join(groups)[::-1]

    return f"{formatted_number}-{check_digit}"


def calculate_rut_check_digit(rut_number: str) -> str:
    """
    Calculate RUT check digit using modulo 11 algorithm.

    Args:
        rut_number: RUT number without check digit (e.g., "12345678")

    Returns:
        str: Check digit ('0'-'9' or 'K')

    Example:
        >>> calculate_rut_check_digit("12345678")
        "5"
    """
    if not rut_number or not rut_number.isdigit():
        return ""

    # Modulo 11 algorithm
    reversed_digits = [int(d) for d in reversed(rut_number)]
    factors = [2, 3, 4, 5, 6, 7]

    total = sum(d * factors[i % 6] for i, d in enumerate(reversed_digits))
    remainder = total % 11
    check_value = 11 - remainder

    # Convert to check digit character
    if check_value == 11:
        return '0'
    elif check_value == 10:
        return 'K'
    else:
        return str(check_value)


def validate_rut(rut: str) -> bool:
    """
    Validate Chilean RUT using modulo 11 algorithm.

    Args:
        rut: RUT string (e.g., "12.345.678-9" or "12345678-9")

    Returns:
        bool: True if valid, False otherwise

    Example:
        >>> validate_rut("12.345.678-5")
        True
        >>> validate_rut("12.345.678-9")
        False
    """
    # Clean RUT
    cleaned = clean_rut(rut)

    # Must be 8 or 9 characters (7-8 digits + check digit)
    if len(cleaned) < 8 or len(cleaned) > 9:
        return False

    # Split into number and check digit
    rut_number = cleaned[:-1]
    provided_check_digit = cleaned[-1]

    # Validate number part is numeric
    if not rut_number.isdigit():
        return False

    # Calculate expected check digit
    expected_check_digit = calculate_rut_check_digit(rut_number)

    # Compare
    return provided_check_digit == expected_check_digit


def validate_rut_field(rut: str) -> str:
    """
    Django validator for RUT field.
    Raises ValidationError if RUT is invalid.

    Args:
        rut: RUT string to validate

    Returns:
        str: Cleaned RUT if valid

    Raises:
        ValidationError: If RUT is invalid

    Example:
        >>> validate_rut_field("12.345.678-5")
        "123456785"
    """
    if not rut:
        raise ValidationError("RUT es requerido")

    cleaned = clean_rut(rut)

    # Length validation
    if len(cleaned) < 8 or len(cleaned) > 9:
        raise ValidationError(
            "RUT debe tener entre 8 y 9 caracteres (7-8 dígitos + dígito verificador)"
        )

    # Format validation
    rut_number = cleaned[:-1]
    if not rut_number.isdigit():
        raise ValidationError("RUT debe contener solo dígitos")

    # Check digit validation
    if not validate_rut(rut):
        raise ValidationError("RUT inválido: dígito verificador no coincide")

    return cleaned


# Test RUT values for development
TEST_RUTS = {
    'valid': [
        "11.111.111-1",
        "22.222.222-2",
        "12.345.678-5",  # Primary test RUT
        "76.123.456-K",
    ],
    'invalid': [
        "12.345.678-9",  # Wrong check digit
        "11.111.111-2",  # Wrong check digit
        "123",           # Too short
        "123456789012",  # Too long
        "abcd.efgh-i",   # Non-numeric
    ]
}
