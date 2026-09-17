from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), default="bottle")  # "bottle" (ເປັນຕຸກ) or "set" (ເປັນຊຸດ)
    description = Column(Text, default="")
    price = Column(Integer, nullable=False)  # in LAK (ກີບ)
    unit_label = Column(String(100), default="ຕຸກ")
    image_url = Column(String(255), default="")
    is_popular = Column(Boolean, default=False)
    deposit_note = Column(String(255), default="")
    is_active = Column(Boolean, default=True)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(50), unique=True, index=True)
    customer_name = Column(String(150), nullable=False)
    customer_phone = Column(String(50), nullable=False)
    address_note = Column(Text, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    items_summary = Column(Text, default="")
    total_amount = Column(Integer, nullable=False)
    slip_image = Column(String(255), default="")
    status = Column(String(50), default="pending")  # pending, approved, delivering, completed, rejected
    admin_note = Column(Text, default="")
    sheet_synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, nullable=True)
    product_name = Column(String(200), nullable=False)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Integer, nullable=False, default=0)
    order = relationship("Order", back_populates="items")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(150), nullable=False)
    role = Column(String(50), default="admin")  # "admin", "staff", "driver"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

