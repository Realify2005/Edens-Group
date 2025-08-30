"""
SQLAlchemy models for mental health services data.

This module defines the database schema for mental health services,
including support for vector embeddings and semantic search capabilities.
"""
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, Boolean, DECIMAL, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from database import Base


class ServiceSearchView(Base):
    """
    Mental health service database model.
    
    Maps to the service_search_view table containing 599 mental health services
    with comprehensive service information, location data, and vector embeddings
    for semantic search capabilities.
    
    This model supports both traditional filtering (by location, cost, service type)
    and modern vector similarity search for intelligent service recommendations.

    """
    __tablename__ = "service_search_view"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Original CSV columns
    organisation_name = Column(Text, index=True)
    campus_name = Column(Text)
    service_name = Column(Text, index=True)
    region_name = Column(Text)
    email = Column(Text)
    phone = Column(Text)
    website = Column(Text)
    notes = Column(Text)
    expected_wait_time = Column(Text)
    opening_hours_24_7 = Column(Boolean)
    opening_hours_standard = Column(Boolean)
    opening_hours_extended = Column(Boolean)
    op_hours_extended_details = Column(Text)
    address = Column(Text)
    suburb = Column(Text, index=True)
    state = Column(Text, index=True)
    postcode = Column(Text, index=True)
    cost = Column(Text, index=True)
    delivery_method = Column(Text)
    level_of_care = Column(Text)
    referral_pathway = Column(Text)
    service_type = Column(Text, index=True)
    target_population = Column(Text, index=True)
    workforce_type = Column(Text)
    
    # Your additional columns
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    created_at = Column(DateTime, default=func.now())
    
    # Vector search column
    embedding = Column(Vector(1536), nullable=True)
    
    def __repr__(self):
        return f"<Service(id={self.id}, name='{self.service_name}', org='{self.organisation_name}')>"
    
    @property
    def display_name(self) -> str:
        """Human-readable service name for responses"""
        if self.service_name and self.organisation_name:
            return f"{self.service_name} - {self.organisation_name}"
        return self.service_name or self.organisation_name or "Unknown Service"
    
    @property
    def location_display(self) -> str:
        """Human-readable location for responses"""
        location_parts = []
        if self.suburb:
            location_parts.append(self.suburb)
        if self.state:
            location_parts.append(self.state)
        if self.postcode:
            location_parts.append(self.postcode)
        return ", ".join(location_parts) or "Location not specified"