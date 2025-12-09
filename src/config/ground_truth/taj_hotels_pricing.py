"""
Ground Truth Price Table for Taj Hotels

This data serves as the verifiable reward source for RLVR training.
Prices are extracted from the kome-text.pdf document.

Note: In production, this could be loaded from a database or YAML file.
For the prototype, we keep it as a Python dict for simplicity.
"""

TAJ_PRICE_TRUTH = {
    "taj mahal palace": {"min": 24000, "max": 65000},
    "taj lake palace": {"min": 45000, "max": 95000},
    "taj falaknuma palace": {"min": 40000, "max": 110000},
    "taj exotica resort & spa": {"min": 22000, "max": 75000},
    "taj bengal": {"min": 13000, "max": 35000},
    "taj coromandel": {"min": 12000, "max": 45000},
}

# Aliases for better matching
TAJ_HOTEL_ALIASES = {
    "taj mahal palace mumbai": "taj mahal palace",
    "taj mahal palace colaba": "taj mahal palace",
    "taj lake palace udaipur": "taj lake palace",
    "taj falaknuma palace hyderabad": "taj falaknuma palace",
    "taj exotica goa": "taj exotica resort & spa",
    "taj exotica resort": "taj exotica resort & spa",
    "taj bengal kolkata": "taj bengal",
    "taj coromandel chennai": "taj coromandel",
}
