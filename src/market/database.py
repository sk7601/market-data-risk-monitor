"""Relational persistence; schema changes are managed by Alembic."""

import os
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Instrument(Base):
    __tablename__ = "instruments"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True)
    exchange: Mapped[str] = mapped_column(default="NYSE")
    currency: Mapped[str] = mapped_column(default="USD")


class Run(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str]
    status: Mapped[str] = mapped_column(default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted: Mapped[int] = mapped_column(default=0)
    rejected: Mapped[int] = mapped_column(default=0)
    message: Mapped[str | None]


class Price(Base):
    __tablename__ = "daily_prices"
    __table_args__ = (
        UniqueConstraint("instrument_id", "date", "source"),
        CheckConstraint("close > 0 AND low > 0 AND volume >= 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer)
    source: Mapped[str]
    adjustment: Mapped[str] = mapped_column(default="split_dividend_adjusted")
    run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Rule(Base):
    __tablename__ = "validation_rules"
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    description: Mapped[str]


class Issue(Base):
    __tablename__ = "data_quality_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"), index=True)
    symbol: Mapped[str] = mapped_column(index=True)
    date: Mapped[str | None]
    rule: Mapped[str] = mapped_column(ForeignKey("validation_rules.code"))
    severity: Mapped[str]
    explanation: Mapped[str]
    record: Mapped[dict] = mapped_column(JSON)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class Holding(Base):
    __tablename__ = "portfolio_holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "instrument_id"),
        CheckConstraint("weight >= 0 AND weight <= 1"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    weight: Mapped[float]


def engine(url: str | None = None):
    target = url or os.getenv("DATABASE_URL", "sqlite:///market.db")
    db = create_engine(target, poolclass=StaticPool if target == "sqlite://" else NullPool)
    if db.dialect.name == "sqlite":

        @event.listens_for(db, "connect")
        def enable_fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    return db


def sessions(url: str | None = None):
    return sessionmaker(engine(url), expire_on_commit=False)
