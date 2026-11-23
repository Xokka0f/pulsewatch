from datetime import datetime


from sqlalchemy import String, Boolean, DateTime, BigInteger, Integer, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(200))
    expected_status: Mapped[int] = mapped_column(Integer, default=200)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="monitors")
    check_results: Mapped[list["CheckResult"]] = relationship(back_populates="monitor")
