import numbers

from django import template

register = template.Library()


@register.filter(is_safe=True)
def format_number(value):
    """
    Convert an integer to a string containing an apostroph "'" every three digits
    and use a "." for decimal separation round to 1 digit.
    For example, 3000.123 becomes "3'000.1" and 45000 becomes "45'000".
    """
    if isinstance(value, numbers.Number):
        value = round(value, 1)
    num_str = str(value)

    # Split the string into integer and decimal parts.
    if '.' in num_str:
        integer_part, decimal_part = num_str.split('.')
    else:
        integer_part, decimal_part = num_str, None

    # Format the integer part with apostrophes as thousand-separators.
    formatted_integer = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            formatted_integer = "'" + formatted_integer
        formatted_integer = digit + formatted_integer

    # Combine the integer and decimal parts
    if decimal_part:
        result = formatted_integer + "." + decimal_part
    else:
        result = formatted_integer

    return result
