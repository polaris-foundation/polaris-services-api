from typing import Optional

from flask_batteries_included.sqldb import db
from sqlalchemy import and_, any_
from sqlalchemy.orm import Query

from dhos_services_api.sqlmodels import DraysonHealthProduct, pydantic_models
from dhos_services_api.sqlmodels.patient import (
    Patient,
    query_options_full_patient_response,
)


def _build_aggregation_query(
    active: Optional[bool], product_name: str, location_uuid: str
) -> Query:
    query = db.session.query(Patient)
    if active is True:
        query = query.filter(
            Patient.dh_products.any(
                and_(
                    DraysonHealthProduct.closed_date == None,
                    DraysonHealthProduct.product_name == product_name,
                )
            )
        )
    elif active is False:
        query = query.filter(
            Patient.dh_products.any(
                and_(
                    DraysonHealthProduct.closed_date != None,
                    DraysonHealthProduct.product_name == product_name,
                )
            )
        )
    else:
        query = query.filter(
            Patient.dh_products.any(DraysonHealthProduct.product_name == product_name)
        )

    query = query.filter(location_uuid == any_(Patient.locations))
    return query


def get_aggregated_patients(
    location_uuid: str, product_name: str, active: Optional[bool] = None
) -> list[dict]:
    query: Query = _build_aggregation_query(
        active=active, product_name=product_name, location_uuid=location_uuid
    )
    query = query.options(*query_options_full_patient_response())
    return [pydantic_models.PatientResponse.from_orm(p).dict() for p in query]
