import typing
from cloud_pipelines import components


# If the component function wants to return some outputs via return values, then these outputs need to be described via NamedTuple
class Outputs(typing.NamedTuple):
    source_line_count: int
    result_line_count: int


def filter_text(
    text_path: components.InputPath(),  # The InputPath() annotation makes the system pass a local input path where the function can read the input data.
    filtered_text_path: components.OutputPath(),  # The OutputPath() annotation makes the system pass a local output path where the function should write the output data.
    pattern: str = ".*",
) -> Outputs:
    """Filters text.

    Filtering is performed using regular expressions.

    Args:
        text_path: The source text
        pattern: The regular expression pattern
        filtered_text_path: The filtered text
    """
    # Function must be self-contained.
    # So all import statements must be inside the function.
    import os
    import re
    import sys

    regex = re.compile(pattern)

    os.makedirs(os.path.dirname(filtered_text_path), exist_ok=True)
    source_line_count = 0
    result_line_count = 0
    with open(text_path, "r") as reader:
        with open(filtered_text_path, "w") as writer:
            for line in reader:
                source_line_count += 1
                if regex.search(line):
                    result_line_count += 1
                    writer.write(line)

    # Return small values as a normal tuple. Do not use Outputs
    return (source_line_count, result_line_count)
