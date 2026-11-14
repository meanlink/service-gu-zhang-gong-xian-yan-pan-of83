from sqlalchemy import String, JSON, Double, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Dataset(Base):
    __tablename__ = 'datasets'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    source: Mapped[str] = mapped_column(String(200), default='manual.json')
    records: Mapped[list] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    visibility: Mapped[str] = mapped_column(String(20), default='private')
    scope_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Double)
class DatasetGrant(Base):
    __tablename__ = 'dataset_grants'
    __table_args__ = (UniqueConstraint('dataset_id', 'user_id', name='uq_dataset_grant'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey('datasets.id'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    granted_by: Mapped[str] = mapped_column(String(150))
    created_at: Mapped[float] = mapped_column(Double)
