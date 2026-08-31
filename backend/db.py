from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./risk_investigator.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(Integer, primary_key=True)
    merchant_id = Column(String, unique=True, index=True)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("TransactionDay", back_populates="merchant")
    cases = relationship("RiskCase", back_populates="merchant")


class TransactionDay(Base):
    __tablename__ = "transaction_days"
    id = Column(Integer, primary_key=True)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), index=True)
    day = Column(Integer)
    txn_count = Column(Float)
    total_amount = Column(Float)
    refund_rate = Column(Float)
    unique_devices = Column(Float)
    failed_txn_rate = Column(Float)
    features = Column(JSON)          # engineered feature snapshot, for reproducibility

    merchant = relationship("Merchant", back_populates="transactions")


class RiskCase(Base):
    __tablename__ = "risk_cases"
    id = Column(Integer, primary_key=True)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), index=True)
    day = Column(Integer)
    xgb_proba = Column(Float)
    shap_top_feature = Column(String)
    status = Column(String, default="PENDING")   # PENDING, INVESTIGATED
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="cases")
    investigation = relationship("Investigation", back_populates="case", uselist=False)


class Investigation(Base):
    __tablename__ = "investigations"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), unique=True)
    transaction_finding = Column(String)
    merchant_finding = Column(String)
    retrieved_policies = Column(JSON)
    evidence_summary = Column(String)
    decision = Column(String)
    decision_confidence = Column(Float)
    explanation_matches_shap = Column(Boolean)
    reviewed_by_human = Column(Boolean, default=False)
    human_override_decision = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("RiskCase", back_populates="investigation")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()