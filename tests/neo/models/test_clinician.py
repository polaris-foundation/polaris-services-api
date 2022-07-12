from typing import Callable

import pytest

from dhos_services_api.models.clinician import Clinician


@pytest.mark.usefixtures("app", "clean_up_neo4j_after_test")
class TestClinician:
    def test_new(self, gdm_location_uuid: str) -> None:
        clinician_details = {
            "first_name": "Dr",
            "last_name": "Dre",
            "phone_number": "07777777777",
            "job_title": "Producer",
            "nhs_smartcard_number": "123456",
            "locations": [gdm_location_uuid],
            "groups": ["GDM Superclinician"],
            "products": [{"product_name": "GDM", "opened_date": "2020-01-01"}],
        }
        clinician = Clinician.new(**clinician_details)
        clinician.save()
        assert clinician.first_name == clinician_details["first_name"]
        assert clinician.job_title == clinician_details["job_title"]

    def test_generate_password_hash(self, clinician_context: Callable) -> None:
        """
        Tests that password hash generation/comparison is working based on a known password, salt, and hash.
        Do not modify the expected password hash or salt as we are testing on behalf of any existing password
        hashes stored in the database.
        """
        plaintext_password: str = "Abc_123*!"
        password_salt: str = "QQI8G8HSIZ5UECVDYAWFUGZZS8X6VUZC"
        expected_hash: str = (
            "d4b08672d1cfd4212f123181eb1d541f8e064ddfc8943e7ed9fa3b23993db550fd2fff3e2a7074ebd0bdf0c0235c4d37c0838987c8"
            "dfd342981fe665f4ca638f9d3de0a534f2253652933581f92fa46a7cf3c54d250f0466004ae8e6a5f1cdfcd8f07cb7f3c55e86f1f2"
            "99c77c51ba694ad915bfead93818ea5b76eb8b1d4d0afc42916c0e3f71dc04ab2eae43c112ea6c010d5bd0d9221063dd3696b725ae"
            "30d7e40f4b5b15d324a94e89eccb2e028fff6b2435d0cdb9a654a3ed3acc270aa85f25e81f08ede1d820d5b2b3c59615580f09d3ed"
            "cdd810456ebd668fdd897636022c6d4c5804847e81b35662516de27e2f9f8722a9901c62e90c82471bd6f530"
        )

        with clinician_context("John", "Roberts", "211215", expiry="2019-03-11") as c:
            c.password_salt = password_salt
            password_hash: str = c.generate_password_hash(password=plaintext_password)
            assert password_hash == expected_hash
