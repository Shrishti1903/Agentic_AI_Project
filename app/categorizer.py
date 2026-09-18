"""Receipt Categorization Engine.

Classifies expenses into one of the 7 PRD categories:
- Travel
- Meals & Entertainment
- Office Supplies
- Professional Development
- Client Expenses
- Equipment
- Other

Uses vendor signature matching and line-item keyword heuristics.
"""
from typing import List, Dict, Any, Optional
from app.schemas import Categorization, Item

CATEGORY_RULES = {
    "Travel": {
        "vendors": [
            "uber", "lyft", "delta", "united", "american airlines", "southwest",
            "british airways", "marriott", "hilton", "hyatt", "airbnb", "hertz",
            "enterprise", "avis", "amtrak", "taxi", "cab", "hotel", "airline"
        ],
        "keywords": [
            "flight", "hotel", "lodging", "room night", "car rental", "fare", "toll",
            "parking", "transit", "ticket", "baggage", "rideshare"
        ]
    },
    "Meals & Entertainment": {
        "vendors": [
            "chipotle", "starbucks", "mcdonald", "subway", "burger king", "wendy",
            "panera", "dunkin", "domino", "pizza", "doordash", "uber eats", "grubhub",
            "cheesecake factory", "restaurant", "cafe", "bistro", "diner", "grill",
            "bakery", "tacos", "sushi", "pub", "bar"
        ],
        "keywords": [
            "burger", "burrito", "bowl", "salad", "pizza", "coffee", "latte", "tea",
            "breakfast", "lunch", "dinner", "meal", "drink", "soda", "sandwich",
            "beverage", "combo", "entree", "appetizer", "dessert"
        ]
    },
    "Office Supplies": {
        "vendors": [
            "office depot", "staples", "officemax", "quill", "paper source"
        ],
        "keywords": [
            "notebook", "paper", "pen", "pens", "stapler", "toner", "cartridge",
            "folder", "binder", "envelope", "sticky note", "whiteboard", "markers"
        ]
    },
    "Professional Development": {
        "vendors": [
            "coursera", "udemy", "edx", "pluralsight", "linkedin learning", "o'reilly",
            "oreilly", "datacamp", "harvard business publishing"
        ],
        "keywords": [
            "course", "conference", "certification", "training", "workshop", "seminar",
            "tutorial", "subscription", "book", "exam fee", "webinar"
        ]
    },
    "Client Expenses": {
        "vendors": [],
        "keywords": [
            "client gift", "client dinner", "client lunch", "client entertainment",
            "billable to client", "client meeting"
        ]
    },
    "Equipment": {
        "vendors": [
            "apple", "best buy", "dell", "lenovo", "hp", "micro center", "logitech",
            "b&h photo", "herman miller", "steelcase"
        ],
        "keywords": [
            "laptop", "macbook", "monitor", "display", "keyboard", "mouse", "headset",
            "headphones", "docking station", "cable", "adapter", "desk", "ergonomic chair",
            "webcam", "hard drive", "ssd", "ram", "server"
        ]
    }
}


def categorize_expense(
    vendor: str,
    items: Optional[List[Item | Dict[str, Any]]] = None,
    notes: Optional[str] = None
) -> Categorization:
    """Categorize an expense based on vendor name and item details."""
    vendor_lower = (vendor or "").lower().strip()
    notes_lower = (notes or "").lower().strip()

    # Extract all item names and lower-case them
    item_names = []
    if items:
        for itm in items:
            if isinstance(itm, dict):
                name = itm.get("name", "") or itm.get("description", "")
            else:
                name = itm.name
            if name:
                item_names.append(name.lower().strip())

    combined_item_text = " ".join(item_names) + " " + notes_lower

    # 1. Check for explicit Client Expenses first if explicitly noted
    if any(kw in combined_item_text for kw in CATEGORY_RULES["Client Expenses"]["keywords"]):
        return Categorization(
            category="Client Expenses",
            confidence=0.92,
            reasoning="Expense keywords indicate client-billable engagement"
        )

    # 2. Check vendor matches across categories
    for cat, rules in CATEGORY_RULES.items():
        for v in rules["vendors"]:
            if v in vendor_lower:
                return Categorization(
                    category=cat,
                    confidence=0.95,
                    reasoning=f"Vendor '{vendor}' strongly matches {cat} profile"
                )

    # 3. Check item keyword matches across categories
    for cat, rules in CATEGORY_RULES.items():
        matched_kws = [kw for kw in rules["keywords"] if kw in combined_item_text]
        if matched_kws:
            return Categorization(
                category=cat,
                confidence=0.85,
                reasoning=f"Items ({', '.join(matched_kws[:3])}) identify {cat}"
            )

    # 4. Fallback if vendor is a general marketplace like Amazon
    if "amazon" in vendor_lower:
        # Check if equipment vs office supplies
        for cat in ["Equipment", "Office Supplies", "Professional Development"]:
            matched_kws = [kw for kw in CATEGORY_RULES[cat]["keywords"] if kw in combined_item_text]
            if matched_kws:
                return Categorization(
                    category=cat,
                    confidence=0.88,
                    reasoning=f"Amazon purchase classified as {cat} based on: {', '.join(matched_kws[:2])}"
                )
        return Categorization(
            category="Office Supplies",
            confidence=0.70,
            reasoning="Amazon general purchase defaulted to Office Supplies"
        )

    # 5. Default fallback
    return Categorization(
        category="Other",
        confidence=0.50,
        reasoning="Vendor and items did not match specific category heuristics"
    )
