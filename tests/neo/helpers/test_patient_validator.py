from dhos_services_api.helpers.patient_validator import PatientValidator
from dhos_services_api.models.patient import Patient


class TestPatientValidator:
    def test_exists_by_details(self, patient: Patient) -> None:
        patient.dod = "2020-08-21"
        patient.save()
        patient_details = {
            "dod": "2020-08-21",
            "dob": patient.dob,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
        }
        validator = PatientValidator(patient_details)
        assert validator.exists_by_details("GDM") is False
        assert validator.exists_by_details("SEND") is True
