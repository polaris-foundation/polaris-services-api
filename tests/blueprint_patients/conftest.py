import pytest
from flask_sqlalchemy import SQLAlchemy


@pytest.fixture
def uses_sql_database(_db: SQLAlchemy) -> None:
    _db.session.commit()
    _db.drop_all()
    _db.create_all()


@pytest.fixture
def minimal_patient() -> dict:
    return {
        "accessibility_considerations": [],
        "allowed_to_text": True,
        "dh_products": [
            {
                "opened_date": "2019-04-29",
                "product_name": "GDM",
            }
        ],
        "dob": "1992-04-23",
        "email_address": "",
        "ethnicity": "185988007",
        "first_name": "Diane",
        "highest_education_level": "426769009",
        "hospital_number": "147777799",
        "last_name": "Smith",
        "locations": ["location_uuid_1"],
        "other_notes": "",
        "personal_addresses": [
            {
                "address_line_1": "School House Stony Bridge Park",
                "address_line_2": "",
                "address_line_3": "",
                "address_line_4": "",
                "lived_from": "2013-12-31",
                "locality": "Oxford",
                "postcode": "OX5 3NA",
                "region": "Oxfordshire",
            }
        ],
        "phone_number": "07123456789",
        "record": {},
        "sex": "248152002",
        "height_in_mm": 1666,
        "weight_in_g": 68800,
    }
