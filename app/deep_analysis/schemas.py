from pydantic import BaseModel

class KPIList(BaseModel):
    """
    Schema for the KPI List
    """
    kpi_list: list[str]

class KPIAnalysis(BaseModel):
    """
    Schema for the KPI Analysis
    """
    business_analysis: str
    code: str
    code_explanation: str
    analysis_steps: str