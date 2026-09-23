"""create cart tables

Revision ID: 6b9bc53f22bf
Revises: 
Create Date: 2026-09-22 14:02:19.647330


"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b9bc53f22bf'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('carts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.String(length=255), nullable=False),
    sa.Column('customer_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id', name='uq_cart_carts_session_id')
    )
    op.create_index('idx_cart_carts_customer_id', 'carts', ['customer_id'], unique=False)
    op.create_table('cart_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cart_id', sa.UUID(), nullable=False),
    sa.Column('variant_id', sa.UUID(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_value', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_percent', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('tax_value', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('tax_percent', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('quantity > 0', name='ck_cart_items_positive_quantity'),
    sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], name='fk_cart_items_cart_id'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cart_id', 'variant_id', name='uq_cart_items_cart_id_variant_id')
    )
    op.create_index('idx_cart_items_cart_id', 'cart_items', ['cart_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_cart_items_cart_id', table_name='cart_items')
    op.drop_table('cart_items')
    op.drop_index('idx_cart_carts_customer_id', table_name='carts')
    op.drop_table('carts')
