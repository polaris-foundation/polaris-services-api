from datetime import datetime
from typing import Dict, List, Optional

from flask_batteries_included.sqldb import db
from sqlalchemy import func
from sqlalchemy.sql import text

from dhos_services_api.sqlmodels.drayson_health_product import DraysonHealthProduct


def get_active_patient_count(
    product_name: str,
    end_date: Optional[str] = None,
    start_date: Optional[str] = None,
) -> List[Dict]:
    if not (_start_date := start_date):
        _start_date = _earliest_product_date(product_name=product_name)

    if not (_end_date := end_date):
        _end_date = datetime.today().strftime("%Y-%m-%d")

    return _get_active_patient_count_sql(
        product_name=product_name,
        start_date=_start_date,
        end_date=_end_date,
    )


def _get_active_patient_count_sql(
    product_name: str,
    start_date: str,
    end_date: str,
) -> List[Dict]:

    statement = text(
        """
        SELECT year_week, count(dhp.*)
        FROM (
            SELECT to_char(i::date, 'IYYY-IW') AS year_week from generate_series(:start_date, :end_date, '1 day'::interval) i
            GROUP BY year_week
        ) d
        LEFT JOIN drayson_health_product dhp on d.year_week >= to_char(dhp.opened_date, 'IYYY-IW') AND (
            dhp.closed_date is null OR
            d.year_week <= to_char(dhp.closed_date, 'IYYY-IW')
        ) AND dhp.product_name = :product_name
        GROUP BY d.year_week
        ORDER BY d.year_week
    """
    )
    results: list = db.session.execute(
        statement,
        {
            "start_date": start_date,
            "end_date": end_date,
            "product_name": product_name,
        },
    )

    return [{"year_week": r[0], "count": r[1]} for r in results]


def _earliest_product_date(product_name: str) -> str:
    statement = text(
        """
        SELECT opened_date
        FROM drayson_health_product
        WHERE product_name = :product_name
        ORDER BY opened_date ASC
        LIMIT 1
    """
    )
    results: list = db.session.execute(
        statement,
        {
            "product_name": product_name,
        },
    ).first()

    return (
        results[0].strftime("%Y-%m-%d")
        if results
        else datetime.today().strftime("%Y-%m-%d")
    )


def get_created_patient_count(
    product_name: str,
    end_date: Optional[str] = None,
    start_date: Optional[str] = None,
) -> List[Dict]:
    if not (_start_date := start_date):
        _start_date = _earliest_product_date(product_name=product_name)

    if not (_end_date := end_date):
        _end_date = datetime.today().strftime("%Y-%m-%d")

    return _get_created_patient_count_sql(
        product_name=product_name,
        start_date=_start_date,
        end_date=_end_date,
    )


def _get_created_patient_count_sql(
    product_name: str,
    start_date: str,
    end_date: str,
) -> List[Dict]:

    results = (
        db.session.query(
            DraysonHealthProduct.opened_date, func.count(DraysonHealthProduct.uuid)
        )
        .filter(
            DraysonHealthProduct.product_name == product_name,
            DraysonHealthProduct.opened_date >= start_date,  # type: ignore
            DraysonHealthProduct.opened_date <= end_date,  # type: ignore
        )
        .group_by(DraysonHealthProduct.opened_date)
        .order_by(DraysonHealthProduct.opened_date)
    )

    return [{"date": r[0].isoformat(), "count": r[1]} for r in results]
