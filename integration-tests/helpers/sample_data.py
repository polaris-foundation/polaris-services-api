import random
import string
from typing import Dict, List

from behave.runner import Context
from helpers.dates import offset_date


def random_string(length: int, letters: bool = True, digits: bool = True) -> str:
    choices: str = ""
    if letters:
        choices += string.ascii_letters
    if digits:
        choices += string.digits
    return "".join(random.choice(choices) for _ in range(length))


def nhs_number() -> str:
    """
    An NHS number must be 10 digits, where the last digit is a check digit using the modulo 11 algorithm
    (see https://datadictionary.nhs.uk/attributes/nhs_number.html).
    """
    first_nine: str = random_string(length=9, letters=False, digits=True)
    digits: List[int] = list(map(int, list(first_nine)))
    total = sum((10 - i) * digit for i, digit in enumerate(digits))
    check_digit = 11 - (total % 11)
    if check_digit == 10:
        # Invalid - try again
        return nhs_number()
    if check_digit == 11:
        check_digit = 0
    return first_nine + str(check_digit)


def patient_data(
    context: Context,
    accessibility_discussed_with: str = None,
    location: str = None,
    dob: str = "1970-01-01",
    allowed_to_text: bool = True,
) -> Dict:
    create_patient_context_variables(context, accessibility_discussed_with)
    data: Dict = {
        "allowed_to_text": allowed_to_text,
        "allowed_to_email": None,
        "first_name": "jane",
        "last_name": "Doez",
        "phone_number": "07123456789",
        "dob": dob,
        "nhs_number": nhs_number(),
        "hospital_number": "a1b2c3d4e5f6",
        "email_address": "Jane@email.com",
        "dh_products": [
            {
                "product_name": "GDM",
                "opened_date": "1970-01-01",
                "accessibility_discussed": context.accessibility_discussed,
                "accessibility_discussed_with": context.accessibility_discussed_with,
                "accessibility_discussed_date": context.accessibility_discussed_date,
            }
        ],
        "personal_addresses": [
            {
                "address_line_1": "42 Some Street",
                "address_line_2": "",
                "address_line_3": "",
                "address_line_4": "",
                "locality": "Oxford",
                "region": "Oxfordshire",
                "postcode": "OX3 5TF",
                "country": "England",
                "lived_from": "1970-01-01",
                "lived_until": "1970-01-01",
            }
        ],
        "ethnicity": "13233008",
        "sex": "23456",
        "height_in_mm": 1555,
        "weight_in_g": 737,
        "highest_education_level": "473461003",
        "accessibility_considerations": [],
        "other_notes": "",
        "record": {
            "notes": [],
            "history": {"gravidity": 1, "parity": 1},
            "pregnancies": [
                {
                    "estimated_delivery_date": context.estimated_delivery_date,
                    "planned_delivery_place": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                    "length_of_postnatal_stay_in_days": 2,
                    "colostrum_harvesting": True,
                    "expected_number_of_babies": 1,
                    "deliveries": [
                        {
                            "birth_outcome": "123456",
                            "outcome_for_baby": "234567",
                            "neonatal_complications": ["123456"],
                            "neonatal_complications_other": "123456",
                            "admitted_to_special_baby_care_unit": False,
                            "birth_weight_in_grams": 1000,
                            "length_of_postnatal_stay_for_baby": 2,
                            "apgar_1_minute": 123,
                            "apgar_5_minute": 321,
                            "feeding_method": "132",
                            "patient": {},
                        }
                    ],
                    "height_at_booking_in_mm": 2000,
                    "weight_at_diagnosis_in_g": 10000,
                    "weight_at_booking_in_g": 10000,
                    "weight_at_36_weeks_in_g": 10000,
                }
            ],
            "diagnoses": [
                {
                    "sct_code": "1234567890",
                    "diagnosed": "1970-01-01",
                    "episode": 1,
                    "presented": "1970-01-01",
                    "diagnosis_tool": ["1234567890"],
                    "diagnosis_tool_other": "1234567890",
                    "risk_factors": ["1234567890"],
                    "observable_entities": [
                        {
                            "sct_code": "123456789",
                            "date_observed": "1970-01-01",
                            "value_as_string": "A value",
                        }
                    ],
                    "management_plan": {
                        "start_date": "1970-01-01",
                        "end_date": "1970-01-01",
                        "sct_code": "386359008",
                        "doses": [
                            {
                                "medication_id": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                                "dose_amount": 1.5,
                                "routine_sct_code": "12345",
                            }
                        ],
                        "actions": [{"action_sct_code": "12345"}],
                    },
                    "readings_plan": {
                        "start_date": "1970-01-01",
                        "end_date": "1970-01-01",
                        "sct_code": "33747003",
                        "days_per_week_to_take_readings": 7,
                        "readings_per_day": 4,
                    },
                }
            ],
        },
        "locations": [location],
    }
    return data


def minimal_patient_data(
    context: Context,
    accessibility_discussed_with: str = None,
    location: str = None,
    dob: str = "1970-01-01",
    allowed_to_text: bool = True,
) -> Dict:
    """Create a minimal patient"""
    create_patient_context_variables(context, accessibility_discussed_with)

    data: Dict = {
        "allowed_to_text": allowed_to_text,
        "allowed_to_email": None,
        "first_name": "Betty",
        "last_name": "Burrell",
        "phone_number": "07123456789",
        "dob": dob,
        "nhs_number": nhs_number(),
        "hospital_number": "a1b2c3d4e5f6",
        "email_address": "bburrell@example.com",
        "dh_products": [
            {
                "product_name": "GDM",
                "opened_date": "1970-01-01",
                "accessibility_discussed": context.accessibility_discussed,
                "accessibility_discussed_with": context.accessibility_discussed_with,
                "accessibility_discussed_date": context.accessibility_discussed_date,
            }
        ],
        "personal_addresses": [
            {
                "address_line_1": "33 Scarcroft Road",
                "address_line_2": "",
                "address_line_3": "",
                "address_line_4": "",
                "locality": "Oxford",
                "region": "Oxfordshire",
                "postcode": "OX3 5TF",
                "country": "England",
                "lived_from": "1970-01-01",
                "lived_until": "1970-01-01",
            }
        ],
        "ethnicity": "13233008",
        "sex": "23456",
        "height_in_mm": None,
        "weight_in_g": None,
        "highest_education_level": "473461003",
        "accessibility_considerations": [],
        "other_notes": "",
        "record": {"notes": [], "history": {}, "pregnancies": [], "diagnoses": []},
        "locations": [location],
    }
    return data


def create_patient_context_variables(
    context: Context, accessibility_discussed_with: str = None
) -> None:
    """Variable parts of the patient record"""
    context.accessibility_discussed_date = (
        offset_date(weeks=-4) if accessibility_discussed_with else None
    )
    context.accessibility_discussed_with = accessibility_discussed_with
    context.accessibility_discussed = accessibility_discussed_with is not None
    context.estimated_delivery_date = offset_date(weeks=2)


def location_data() -> Dict:
    return {
        "address_line_1": "Headley Way",
        "address_line_2": "Headington",
        "address_line_3": "An address fragment",
        "address_line_4": "A fourth address fragment",
        "country": "UK",
        "dh_products": [{"opened_date": "2018-08-01", "product_name": "GDM"}],
        "display_name": "Big old Hospital",
        "locality": "Oxford",
        "location_type": "D0000009",
        "ods_code": "BOH",
        "postcode": "OX3 9DU",
        "region": "Oxfordshire",
    }
