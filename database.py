"""
Database models and operations for QR code research project.
Handles duplicate detection via QR content hashing.
"""
import hashlib
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

Base = declarative_base()


class QRCode(Base):
    """Master record for each unique QR code content"""
    __tablename__ = 'qr_codes'

    id = Column(Integer, primary_key=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA256 of QR content
    qr_content = Column(Text, nullable=False)  # The actual URL or text in the QR code
    first_seen = Column(DateTime, default=datetime.utcnow)
    times_found = Column(Integer, default=1)

    # Destination info (from first scan)
    destination_url = Column(Text)
    final_url = Column(Text)  # After redirects
    site_title = Column(String(500))

    # Classification
    classification = Column(String(100))  # promotional, scam, malicious, personal, etc.
    confidence_score = Column(Float)  # AI confidence in classification
    is_malicious = Column(Boolean, default=False)
    manual_review = Column(Boolean, default=False)  # Flag for low confidence requiring review

    # Relationships
    sightings = relationship("QRSighting", back_populates="qr_code", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QRCode(hash={self.content_hash[:8]}..., found={self.times_found}x)>"


class QRSighting(Base):
    """Each individual sighting/submission of a QR code"""
    __tablename__ = 'qr_sightings'

    id = Column(Integer, primary_key=True)
    qr_code_id = Column(Integer, ForeignKey('qr_codes.id'), nullable=False)

    # Location data from EXIF
    latitude = Column(Float)
    longitude = Column(Float)
    location_accuracy = Column(String(50))  # GPS, network, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Image metadata
    image_path = Column(String(500))
    device_model = Column(String(200))

    # Submission info
    submission_phone = Column(String(20))  # Who submitted it
    submission_method = Column(String(50), default='sms')  # sms, web, etc.

    # Screenshot
    screenshot_path = Column(String(500))

    # Relationship
    qr_code = relationship("QRCode", back_populates="sightings")

    def __repr__(self):
        return f"<QRSighting(id={self.id}, location=({self.latitude}, {self.longitude}), time={self.timestamp})>"


class DatabaseManager:
    """Handles all database operations"""

    def __init__(self, db_path='data/qr_research.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    @staticmethod
    def hash_qr_content(content):
        """Create SHA256 hash of QR content for duplicate detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def find_or_create_qr(self, qr_content):
        """
        Find existing QR code by content or create new one.
        Returns (qr_code, is_duplicate)
        """
        session = self.Session()
        try:
            content_hash = self.hash_qr_content(qr_content)
            qr_code = session.query(QRCode).filter_by(content_hash=content_hash).first()

            if qr_code:
                # Duplicate found!
                qr_code.times_found += 1
                session.commit()
                return qr_code, True
            else:
                # New QR code
                qr_code = QRCode(
                    content_hash=content_hash,
                    qr_content=qr_content
                )
                session.add(qr_code)
                session.commit()
                return qr_code, False
        finally:
            session.close()

    def add_sighting(self, qr_code_id, **kwargs):
        """Add a new sighting of a QR code"""
        session = self.Session()
        try:
            sighting = QRSighting(qr_code_id=qr_code_id, **kwargs)
            session.add(sighting)
            session.commit()
            return sighting
        finally:
            session.close()

    def update_qr_classification(self, qr_code_id, classification, confidence, is_malicious=False):
        """Update classification info for a QR code"""
        session = self.Session()
        try:
            qr_code = session.query(QRCode).get(qr_code_id)
            if qr_code:
                qr_code.classification = classification
                qr_code.confidence_score = confidence
                qr_code.is_malicious = is_malicious
                qr_code.manual_review = confidence < 0.7  # Flag low confidence for review
                session.commit()
        finally:
            session.close()

    def update_qr_destination(self, qr_code_id, destination_url, final_url, site_title):
        """Update destination info for a QR code"""
        session = self.Session()
        try:
            qr_code = session.query(QRCode).get(qr_code_id)
            if qr_code:
                qr_code.destination_url = destination_url
                qr_code.final_url = final_url
                qr_code.site_title = site_title
                session.commit()
        finally:
            session.close()

    def get_statistics(self):
        """Get summary statistics"""
        session = self.Session()
        try:
            total_qr_codes = session.query(QRCode).count()
            total_sightings = session.query(QRSighting).count()
            malicious_count = session.query(QRCode).filter_by(is_malicious=True).count()
            needs_review = session.query(QRCode).filter_by(manual_review=True).count()

            return {
                'total_unique_qr_codes': total_qr_codes,
                'total_sightings': total_sightings,
                'malicious_count': malicious_count,
                'needs_manual_review': needs_review
            }
        finally:
            session.close()


if __name__ == '__main__':
    # Test the database
    db = DatabaseManager()
    print("Database initialized successfully!")
    print(f"Stats: {db.get_statistics()}")
