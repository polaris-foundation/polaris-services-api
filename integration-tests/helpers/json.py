import json
from pathlib import Path
from typing import Dict, List, Union

from behave.runner import Context
from jsonpatch import apply_patch


def substitute_variables(context: Context, json_patch: List) -> List:
    # Substitute variables in the JSON patch
    for p in json_patch:
        if "value_format" in p:
            if isinstance(p["value_format"], list):
                p["value"] = [v.format(context=context) for v in p["value_format"]]
            else:
                p["value"] = p["value_format"].format(context=context)
        if "value_format_sorted" in p:
            if isinstance(p["value_format_sorted"], list):
                p["value"] = sorted(
                    [v.format(context=context) for v in p["value_format_sorted"]]
                )
            else:
                p["value"] = p["value_format"].format(context=context)

    return json_patch


def load_patched_json(context: Context, data_filename: str) -> Union[List, Dict]:
    input_json_file = Path("data") / data_filename
    data = json.loads(input_json_file.read_text())

    # Data may be either the raw JSON, or can be a Dict with the template data and a list of patches.
    if set(data) == {"data", "patches"}:
        data = apply_patch(data["data"], substitute_variables(context, data["patches"]))

    return data


def load_json_test(context: Context, data_filename: str) -> Union[List, Dict]:
    """Load a file containing a json patch object, possibly with variable substitutions required."""
    input_json_file = Path("data") / data_filename
    data: List = json.loads(input_json_file.read_text())

    substitute_variables(context, data)
    return data
