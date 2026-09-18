from pydantic import BaseModel
from typing import List, Optional

class Item(BaseModel):
    name: str
    quantity: Optional[int] = 1
    price: float

class Extraction(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str
    time: Optional[str]
    itemsCount: int
    items: List[Item]
    paymentMethod: Optional[str]
    category: Optional[str]
    confidence: float

class Categorization(BaseModel):
    category: str
    confidence: float
    reasoning: Optional[str]

class PolicyCheck(BaseModel):
    rule: str
    status: str
    message: Optional[str]

class Flag(BaseModel):
    type: str
    message: str
    severity: str

class Compliance(BaseModel):
    status: str
    policyChecks: List[PolicyCheck]
    anomalies: List[Flag]

class Approval(BaseModel):
    recommendation: str
    reason: Optional[str]
    requiredApproval: Optional[str]
    alternativeAction: Optional[str]

class ParseResponse(BaseModel):
    receiptId: str
    extraction: Extraction
    categorization: Categorization
    compliance: Compliance
    approval: Approval
