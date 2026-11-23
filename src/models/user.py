from datetime import datetime


from sqlalchemy import String, Boolean, DateTime, BigInteger, Integer, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(254),unique=True)
    username: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean,default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=text("now()"))

    monitors:Mapped[list["Monitor"]] = relationship(back_populates="user")