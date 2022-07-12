from typing import Any, Dict, List

from flask_batteries_included.helpers import timestamp

from dhos_services_api.models.patient import Patient


class PatientValidator:

    whitelist = (
        "allowed_to_text",
        "first_name",
        "last_name",
        "phone_number",
        "nhs_number",
        "email_address",
        "ethnicity",
        "sex",
        "dod",
        "highest_education_level",
        "other_notes",
        "uuid",
        "allowed_to_email",
        "ethnicity_other",
        "highest_education_level_other",
        "accessibility_considerations_other",
    )

    def __init__(self, patient_data: Dict[str, Any]) -> None:
        self.hospital_number = patient_data.get("hospital_number", None)
        self.dob = timestamp.parse_iso8601_to_date(patient_data.get("dob", None))
        self.patient_data = patient_data

    def exists_by_hospital_num(self, product_name: str) -> bool:

        if not self.hospital_number:
            return False

        patients_by_mrn: List[Patient] = Patient.nodes.filter(
            hospital_number=self.hospital_number
        )

        matching_patients = [
            p
            for p in patients_by_mrn
            for x in p.dh_products
            if x.product_name == product_name and x.closed_date_ is None
        ]

        return len(matching_patients) > 0

    def exists_by_details(self, product_name: str) -> bool:

        if not self.dob:
            return False

        fields = {
            k: self.patient_data[k]
            for k in self.patient_data
            if not isinstance(self.patient_data[k], (list, dict))
            and k in self.whitelist
        }

        if "dod" in fields:
            fields["dod_"] = timestamp.parse_iso8601_to_date_typesafe(fields.pop("dod"))

        patients = Patient.nodes.filter(dob_=self.dob, **fields)

        matching_patients = [
            p
            for p in patients
            for x in p.dh_products
            if x.product_name == product_name and x.closed_date_ is None
        ]

        return len(matching_patients) > 0

    @staticmethod
    def exists_by_nhs_number(nhs_number: str, product_name: str) -> bool:

        patients_by_nhs_no: List[Patient] = Patient.nodes.filter(nhs_number=nhs_number)

        matching_patients = [
            p
            for p in patients_by_nhs_no
            for x in p.dh_products
            if x.product_name == product_name and x.closed_date_ is None
        ]

        return len(matching_patients) > 0
