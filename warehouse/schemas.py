from pydantic import BaseModel, field_validator
from typing import Optional


# ── Auth ────────────────────────────────────────────────────────────────────

class LoginForm(BaseModel):
    username: str
    password: str


# ── Users ───────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("admin", "operator"):
            raise ValueError("role must be admin or operator")
        return v


# ── Aisles ──────────────────────────────────────────────────────────────────

class AisleCreate(BaseModel):
    code: str
    name: str


# ── Racks ───────────────────────────────────────────────────────────────────

class RackCreate(BaseModel):
    code: str
    name: str


# ── Levels ──────────────────────────────────────────────────────────────────

class LevelCreate(BaseModel):
    level_num: int

    @field_validator("level_num")
    @classmethod
    def valid_level(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError("level_num must be 1, 2, or 3")
        return v


# ── Bins ────────────────────────────────────────────────────────────────────

class BinCreate(BaseModel):
    code: str
    size_category: str = "M"
    width_cm: float
    height_cm: float
    depth_cm: float

    @field_validator("size_category")
    @classmethod
    def valid_size(cls, v: str) -> str:
        if v not in ("S", "M", "L", "XL"):
            raise ValueError("size_category must be S, M, L, or XL")
        return v

    @field_validator("width_cm", "height_cm", "depth_cm")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimensions must be positive")
        return v


# ── Items ───────────────────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = ""
    width_cm: float
    height_cm: float
    depth_cm: float

    @field_validator("width_cm", "height_cm", "depth_cm")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimensions must be positive")
        return v


# ── Inventory ────────────────────────────────────────────────────────────────

class AddInventory(BaseModel):
    bin_id: int
    item_id: int
    quantity: int

    @field_validator("quantity")
    @classmethod
    def positive_qty(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v


class RemoveInventory(BaseModel):
    bin_id: int
    item_id: int
    quantity: int

    @field_validator("quantity")
    @classmethod
    def positive_qty(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v


# ── Pick ─────────────────────────────────────────────────────────────────────

class BasketAddItem(BaseModel):
    item_id: int
    quantity: int

    @field_validator("quantity")
    @classmethod
    def positive_qty(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v
