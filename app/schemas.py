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
    time: Optional[str] = None
    itemsCount: int
    items: List[Item]
    paymentMethod: Optional[str] = None
    category: Optional[str] = None
    confidence: float

class Categorization(BaseModel):
    category: str
    confidence: float
    reasoning: Optional[str] = None

class PolicyCheck(BaseModel):
    rule: str
    status: str
    message: Optional[str] = None

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
    reason: Optional[str] = None
    requiredApproval: Optional[str] = None
    alternativeAction: Optional[str] = None

class ParseResponse(BaseModel):
    receiptId: str
    extraction: Extraction
    categorization: Categorization
    compliance: Compliance
    approval: Approval

class BulkUploadResponse(BaseModel):
    batchId: str
    processed: int
    approved: int
    flagged: int
    totalAmount: float
    processingTime: str
    results: List[ParseResponse]

class AnalyticsSummary(BaseModel):
    totalReceipts: int
    todayExpenses: float
    thisMonthExpenses: float
    averageApprovalTime: str = "2 min"
    anomalyRate: str
    approvalRate: str

class CategoryTrend(BaseModel):
    category: str
    count: int
    total: float

class DepartmentTrend(BaseModel):
    department: str
    count: int
    total: float

class EmployeeTrend(BaseModel):
    employeeId: str
    count: int
    total: float

class AnalyticsTrends(BaseModel):
    byCategory: List[CategoryTrend]
    byDepartment: List[DepartmentTrend]
    byEmployee: List[EmployeeTrend]

class FlaggedReceiptItem(BaseModel):
    receiptId: str
    employeeId: str
    vendor: str
    amount: float
    reason: Optional[str] = None
    status: str

class AnalyticsDashboardResponse(BaseModel):
    summary: AnalyticsSummary
    trends: AnalyticsTrends
    flagged: List[FlaggedReceiptItem]

