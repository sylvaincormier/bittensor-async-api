from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DividendHistory(Base):
    """
    Model for storing dividend history and stake operations
    """
    __tablename__ = "dividend_history"
    
    id = Column(Integer, primary_key=True, index=True)
    netuid = Column(String, nullable=False)
    hotkey = Column(String, nullable=False)
    dividend = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # If a stake/unstake operation was performed
    stake_operation = Column(String, nullable=True)  # "stake" or "unstake"
    stake_amount = Column(Float, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<DividendHistory(id={self.id}, netuid={self.netuid}, hotkey={self.hotkey}, dividend={self.dividend})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "netuid": self.netuid,
            "hotkey": self.hotkey,
            "dividend": self.dividend,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "stake_operation": self.stake_operation,
            "stake_amount": self.stake_amount,
            "sentiment_score": self.sentiment_score
        }
