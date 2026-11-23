from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, BigInteger, Integer, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("monitors.id", ondelete="CASCADE"))
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_success: Mapped[bool] = mapped_column(Boolean)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    monitor: Mapped["Monitor"] = relationship(back_populates="check_results")