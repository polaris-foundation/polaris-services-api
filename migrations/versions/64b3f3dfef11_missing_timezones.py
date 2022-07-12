"""missing timezones

Revision ID: 64b3f3dfef11
Revises: 80db87e665d5
Create Date: 2022-06-07 10:01:15.037976

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "64b3f3dfef11"
down_revision = "80db87e665d5"
branch_labels = None
depends_on = None


def upgrade():
    for tbl in (
        "delivery",
        "diagnosis",
        "dose",
        "dose_change",
        "dose_history",
        "drayson_health_product",
        "drayson_health_product_change",
        "history",
        "management_plan",
        "non_medication_action",
        "note",
        "observable_entity",
        "patient",
        "personal_address",
        "pregnancy",
        "readings_plan",
        "readings_plan_change",
        "record",
        "terms_agreement",
        "visit",
    ):
        op.alter_column(tbl, "created", type_=sa.DateTime(timezone=True))
        op.alter_column(tbl, "modified", type_=sa.DateTime(timezone=True))
        op.create_unique_constraint(f"{tbl}_uuid_key", tbl, ["uuid"])

    op.alter_column("patient", "first_name", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column("patient", "last_name", existing_type=sa.VARCHAR(), nullable=True)


def downgrade():
    op.alter_column("patient", "last_name", existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column("patient", "first_name", existing_type=sa.VARCHAR(), nullable=False)

    for tbl in (
        "visit",
        "terms_agreement",
        "record",
        "readings_plan_change",
        "readings_plan",
        "pregnancy",
        "personal_address",
        "patient",
        "observable_entity",
        "note",
        "non_medication_action",
        "management_plan",
        "history",
        "drayson_health_product_change",
        "drayson_health_product",
        "dose_history",
        "dose_change",
        "dose",
        "diagnosis",
        "delivery",
    ):
        op.drop_constraint(f"{tbl}_uuid_key", tbl, type_="unique")
        op.alter_column(tbl, "modified", type_=sa.DateTime(timezone=False))
        op.alter_column(tbl, "created", type_=sa.DateTime(timezone=False))
