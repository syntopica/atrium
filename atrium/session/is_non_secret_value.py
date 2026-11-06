"""Tell a value found after a credential label that is known not to be one."""

from atrium.session.is_code_expression_value import is_code_expression_value
from atrium.session.is_code_reference_value import is_code_reference_value
from atrium.session.is_tax_reference_value import is_tax_reference_value
from atrium.session.is_variable_name_value import is_variable_name_value


def is_non_secret_value(value: str) -> bool:
    """Whether the value is code, a reference into code, a variable name or a tax reference.

    Same rule as scribe's `isNonSecretValue`.
    """
    return (
        is_code_expression_value(value)
        or is_code_reference_value(value)
        or is_variable_name_value(value)
        or is_tax_reference_value(value)
    )
