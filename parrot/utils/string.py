import re


def kebab_case(string):
    """Converts a string to kebab case.

    Args:
      string: The string to convert.

    Returns:
      The string in kebab case.
    """

    string = re.sub(r"(_|-)+", " ", string).lower()
    return "-".join(string.split())
