"""
src/models/base.py
Base model for all database models
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the base class for all models
Base = declarative_base()
