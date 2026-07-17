"""Add M-Pesa callback fields to deposits

Revision ID: 8dd32d3f8686
Revises:
Create Date: 2026-07-17 07:37:02.479636
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "8dd32d3f8686"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.add_column(
            sa.Column("checkout_request_id", sa.String(100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("merchant_request_id", sa.String(100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("callback_data", sa.Text(), nullable=True)
        )

        # Give the unique constraint a name
        batch_op.create_unique_constraint(
            "uq_deposits_checkout_request_id",
            ["checkout_request_id"]
        )


def downgrade():
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.drop_constraint(
            "uq_deposits_checkout_request_id",
            type_="unique"
        )
        batch_op.drop_column("callback_data")
        batch_op.drop_column("merchant_request_id")
        batch_op.drop_column("checkout_request_id")