import uuid
from typing import Callable, Dict, List

import pytest
from neomodel import UniqueProperty

from dhos_services_api.models.patient import _latest_terms_agreement
from dhos_services_api.models.terms_agreement import TermsAgreement


class TestPatient:
    @pytest.mark.parametrize(
        "nhs1,hosp1,nhs2,hosp2",
        [
            ("123123123", "11111", "123123123", "222222"),
            ("123123123", "11111", "123123124", "11111"),
        ],
    )
    def test_patient_unique_fields_rejected(
        self, patient_context: Callable, nhs1: str, hosp1: str, nhs2: str, hosp2: str
    ) -> None:
        """This test bypasses our models and tests that the database constraints are present
        and will prevent duplicate patients with the same NHS number or the same hospital number."""
        with patient_context("Carol", nhs_number=nhs1, hospital_number=hosp1) as carol:
            with pytest.raises(UniqueProperty) as exc_info:
                with patient_context(
                    "Jane", nhs_number=nhs2, hospital_number=hosp2
                ) as jane:
                    pass

    @pytest.mark.parametrize(
        "nhs1,hosp1,nhs2,hosp2",
        [(None, "11111", None, "222222"), ("123123123", None, "123123124", None)],
    )
    def test_patient_unique_fields_none_ok(
        self, patient_context: Callable, nhs1: str, hosp1: str, nhs2: str, hosp2: str
    ) -> None:
        """This test bypasses our models and tests that the database constraints are present
        and will prevent duplicate patients with the same NHS number or the same hospital number
        but that None is permitted."""
        with patient_context("Carol", nhs_number=nhs1, hospital_number=hosp1) as carol:
            with patient_context(
                "Jane", nhs_number=nhs2, hospital_number=hosp2
            ) as jane:
                pass

    @pytest.mark.parametrize(
        "terms_agreements,expected",
        [
            (None, None),
            (
                [
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 4,
                        "tou_version": 3,
                    },
                    {
                        "product_name": "GDM",
                        "version": 9,
                    },
                ],
                {
                    "product_name": "GDM",
                    "patient_notice_version": 4,
                    "tou_version": 3,
                },
            ),
            (
                [
                    {
                        "product_name": "GDM",
                        "version": 2,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 5,
                        "tou_version": 3,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 2,
                        "tou_version": 1,
                    },
                ],
                {
                    "product_name": "GDM",
                    "patient_notice_version": 5,
                    "tou_version": 3,
                },
            ),
            (
                [
                    {
                        "product_name": "GDM",
                        "version": 1,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 5,
                        "tou_version": 3,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 2,
                        "tou_version": 1,
                    },
                ],
                {
                    "product_name": "GDM",
                    "patient_notice_version": 5,
                    "tou_version": 3,
                },
            ),
        ],
    )
    def test_latest_terms_agreement(
        self,
        terms_agreements: TermsAgreement,
        expected: Dict,
        patient_context: Callable,
    ) -> None:
        pid = uuid.uuid4()
        with patient_context("Carol", hospital_number=pid) as carol:
            if not terms_agreements:
                assert _latest_terms_agreement(terms_agreements) == expected
            else:
                terms: List[TermsAgreement] = []
                for term in terms_agreements:
                    if term.get("version"):
                        terms.append(
                            TermsAgreement.new(
                                product_name=term.get("product_name"),
                                version=term.get("version"),
                            )
                        )
                    else:
                        terms.append(
                            TermsAgreement.new_v2(
                                product_name=term.get("product_name"),
                                patient_notice_version=term.get(
                                    "patient_notice_version"
                                ),
                                tou_version=term.get("tou_version"),
                            )
                        )
                latest_terms = _latest_terms_agreement(terms)
                assert latest_terms is not None
                for key in expected:
                    assert expected[key] == latest_terms[key]
