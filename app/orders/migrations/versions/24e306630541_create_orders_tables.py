"""create orders tables

Revision ID: 24e306630541
Revises: 
Create Date: 2026-09-22 14:11:39.628725



"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24e306630541'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('orders',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cart_id', sa.UUID(), nullable=False),
    sa.Column('customer_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('tax_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_orders_orders_cart_id', 'orders', ['cart_id'], unique=False)
    op.create_index('idx_orders_orders_customer_id', 'orders', ['customer_id'], unique=False)
    op.create_table('order_adjustments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('percent', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_orders_adjustments_order_id'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_orders_adjustments_order_id', 'order_adjustments', ['order_id'], unique=False)
    op.create_table('order_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('variant_id', sa.UUID(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_value', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_percent', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('tax_value', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('tax_percent', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_orders_items_order_id'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_orders_items_order_id', 'order_items', ['order_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_orders_items_order_id', table_name='order_items')
    op.drop_table('order_items')
    op.drop_index('idx_orders_adjustments_order_id', table_name='order_adjustments')
    op.drop_table('order_adjustments')
    op.drop_index('idx_orders_orders_customer_id', table_name='orders')
    op.drop_index('idx_orders_orders_cart_id', table_name='orders')
    op.drop_table('orders')
