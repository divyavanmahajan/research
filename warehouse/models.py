from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="operator")  # admin | operator

    pick_sessions = relationship("PickSession", back_populates="operator")


class Aisle(Base):
    __tablename__ = "aisles"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)  # A1, A2 …
    name = Column(String, nullable=False)

    racks = relationship("Rack", back_populates="aisle", cascade="all, delete-orphan")


class Rack(Base):
    __tablename__ = "racks"
    __table_args__ = (UniqueConstraint("aisle_id", "code"),)

    id = Column(Integer, primary_key=True, index=True)
    aisle_id = Column(Integer, ForeignKey("aisles.id"), nullable=False)
    code = Column(String, nullable=False)  # R1, R2 …
    name = Column(String, nullable=False)

    aisle = relationship("Aisle", back_populates="racks")
    levels = relationship("Level", back_populates="rack", cascade="all, delete-orphan")


class Level(Base):
    __tablename__ = "levels"
    __table_args__ = (UniqueConstraint("rack_id", "level_num"),)

    id = Column(Integer, primary_key=True, index=True)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=False)
    level_num = Column(Integer, nullable=False)  # 1 | 2 | 3

    rack = relationship("Rack", back_populates="levels")
    bins = relationship("Bin", back_populates="level", cascade="all, delete-orphan")


class Bin(Base):
    __tablename__ = "bins"
    __table_args__ = (UniqueConstraint("level_id", "code"),)

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False)
    code = Column(String, nullable=False)  # B1, B2 …
    size_category = Column(String, default="M")  # S | M | L | XL
    width_cm = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    depth_cm = Column(Float, nullable=False)

    level = relationship("Level", back_populates="bins")
    bin_items = relationship("BinItem", back_populates="bin", cascade="all, delete-orphan")

    @property
    def volume_cm3(self) -> float:
        return self.width_cm * self.height_cm * self.depth_cm

    @property
    def used_volume_cm3(self) -> float:
        return sum(bi.item.volume_cm3 * bi.quantity for bi in self.bin_items)

    @property
    def capacity_pct(self) -> float:
        vol = self.volume_cm3
        if vol == 0:
            return 0.0
        return min(100.0, self.used_volume_cm3 / vol * 100)

    @property
    def location_code(self) -> str:
        level = self.level
        rack = level.rack
        aisle = rack.aisle
        return f"{aisle.code}-{rack.code}-L{level.level_num}-{self.code}"


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    width_cm = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    depth_cm = Column(Float, nullable=False)

    bin_items = relationship("BinItem", back_populates="item", cascade="all, delete-orphan")
    pick_stops = relationship("PickStop", back_populates="item")

    @property
    def volume_cm3(self) -> float:
        return self.width_cm * self.height_cm * self.depth_cm


class BinItem(Base):
    __tablename__ = "bin_items"
    __table_args__ = (UniqueConstraint("bin_id", "item_id"),)

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    bin = relationship("Bin", back_populates="bin_items")
    item = relationship("Item", back_populates="bin_items")


class PickSession(Base):
    __tablename__ = "pick_sessions"

    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="draft")  # draft | open | completed

    operator = relationship("User", back_populates="pick_sessions")
    pick_items = relationship("PickItem", back_populates="session", cascade="all, delete-orphan")
    stops = relationship("PickStop", back_populates="session", cascade="all, delete-orphan",
                         order_by="PickStop.order_index")


class PickItem(Base):
    """Basket entry before route generation."""
    __tablename__ = "pick_items"
    __table_args__ = (UniqueConstraint("session_id", "item_id"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("pick_sessions.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity_requested = Column(Integer, default=1, nullable=False)

    session = relationship("PickSession", back_populates="pick_items")
    item = relationship("Item")


class PickStop(Base):
    """Ordered route stop after route generation."""
    __tablename__ = "pick_stops"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("pick_sessions.id"), nullable=False)
    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False)
    picked = Column(Boolean, default=False)

    session = relationship("PickSession", back_populates="stops")
    bin = relationship("Bin")
    item = relationship("Item", back_populates="pick_stops")
