"""add idempotency table, audit actor, composite indexes

Revision ID: 4b8ad0c2b01e
Revises: a1b4b0d08ce4
Create Date: 2026-04-05 18:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b8ad0c2b01e'
down_revision: Union[str, Sequence[str], None] = 'a1b4b0d08ce4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotency table
    op.create_table(
        'idempotency_keys',
        sa.Column('key', sa.String(length=100), primary_key=True, nullable=False),
        sa.Column('request_fingerprint', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('response_body', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='completed'),
        sa.Column('ttl_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_idempotency_ttl', 'idempotency_keys', ['ttl_expires_at'], unique=False)
    op.create_index('idx_idempotency_user', 'idempotency_keys', ['user_id'], unique=False)

    # Audit trail: actor_id + indexes
    op.add_column('financial_record_audits', sa.Column('actor_id', sa.String(length=36), nullable=True))
    op.create_index('idx_audit_actor_id', 'financial_record_audits', ['actor_id'], unique=False)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            'financial_record_audits',
            'old_state',
            existing_type=sa.Text(),
            type_=sa.JSON(),
            postgresql_using='old_state::json',
        )
        op.alter_column(
            'financial_record_audits',
            'new_state',
            existing_type=sa.Text(),
            type_=sa.JSON(),
            postgresql_using='new_state::json',
        )

    # Composite and helpful indexes for performance
    op.create_index('idx_records_created_by_date', 'financial_records', ['created_by', 'date'], unique=False)
    op.create_index('idx_records_category_type', 'financial_records', ['category', 'type'], unique=False)
    op.create_index('idx_records_created_at', 'financial_records', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_records_created_at', table_name='financial_records')
    op.drop_index('idx_records_category_type', table_name='financial_records')
    op.drop_index('idx_records_created_by_date', table_name='financial_records')
    op.drop_index('idx_audit_actor_id', table_name='financial_record_audits')
    op.drop_column('financial_record_audits', 'actor_id')
    op.drop_index('idx_idempotency_user', table_name='idempotency_keys')
    op.drop_index('idx_idempotency_ttl', table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            'financial_record_audits',
            'new_state',
            existing_type=sa.JSON(),
            type_=sa.Text(),
            postgresql_using='new_state::text',
        )
        op.alter_column(
            'financial_record_audits',
            'old_state',
            existing_type=sa.JSON(),
            type_=sa.Text(),
            postgresql_using='old_state::text',
        )
