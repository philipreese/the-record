import os
from sqlalchemy import func, Integer

# Detect database engine type from the environment URL
DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")

def get_date_expr(col):
    """Return dialect-specific date formatting expression (YYYY-MM-DD)."""
    if IS_POSTGRES:
        return func.to_char(func.to_timestamp(col), "YYYY-MM-DD")
    return func.date(col, "unixepoch", "localtime")

def get_hour_expr(col):
    """Return dialect-specific hour formatting expression (HH24)."""
    if IS_POSTGRES:
        return func.to_char(func.to_timestamp(col), "HH24")
    return func.strftime("%H", col, "unixepoch", "localtime")

def get_month_expr(col):
    """Return dialect-specific month formatting expression (YYYY-MM)."""
    if IS_POSTGRES:
        return func.to_char(func.to_timestamp(col), "YYYY-MM")
    return func.strftime("%Y-%m", col, "unixepoch", "localtime")

def get_month_num_expr(col):
    """Return dialect-specific month integer extraction (1-12)."""
    if IS_POSTGRES:
        return func.extract("month", func.to_timestamp(col))
    return func.cast(func.strftime("%m", col, "unixepoch", "localtime"), Integer)

def get_year_expr(col):
    """Return dialect-specific year formatting expression (YYYY)."""
    if IS_POSTGRES:
        return func.to_char(func.to_timestamp(col), "YYYY")
    return func.strftime("%Y", col, "unixepoch", "localtime")
