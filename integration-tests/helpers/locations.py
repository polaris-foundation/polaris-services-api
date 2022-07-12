import re
import unicodedata
from datetime import datetime, timezone
from functools import partial
from typing import Dict

import draymed

HOSPITAL_SNOMED: str = draymed.codes.code_from_name("hospital", "location")
WARD_SNOMED: str = draymed.codes.code_from_name("ward", "location")
BAY_SNOMED: str = draymed.codes.code_from_name("bay", "location")
BED_SNOMED: str = draymed.codes.code_from_name("bed", "location")


def slugify(value: str) -> str:
    """
    Converts a string to ascii, lowercase, punctuation stripped, whitespace replaced by a single dash.
    """
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s_-]", "", value.lower())
    return re.sub(r"[\s_-]+", "-", value).strip("-_")


def location_factory(
    name: str,
    ods_code: str = None,
    location_type: str = WARD_SNOMED,
    product_name: str = "SEND",
    opened_date: datetime = None,
    parent: str = None,
    parent_ods_code: str = None,
    uuid: str = None,
) -> Dict:
    if opened_date is None:
        opened_date = datetime.now(tz=timezone.utc)

    if ods_code is None:
        ods_code = slugify(name)

    assert parent is None or parent_ods_code is None

    location: Dict = {
        "dh_products": [
            {
                "product_name": product_name,
                "opened_date": opened_date.isoformat(timespec="milliseconds"),
            }
        ],
        "location_type": location_type,
        "ods_code": ods_code,
        "display_name": name,
        "parent_ods_code": parent_ods_code,
        "parent": parent,
        "uuid": uuid,
    }
    return {k: v for k, v in location.items() if v is not None}


hospital_factory = partial(location_factory, location_type=HOSPITAL_SNOMED)
ward_factory = partial(location_factory, location_type=WARD_SNOMED)
bay_factory = partial(location_factory, location_type=BAY_SNOMED)
bed_factory = partial(location_factory, location_type=BED_SNOMED)
