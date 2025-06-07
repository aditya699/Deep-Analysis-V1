from pydantic import BaseModel

class KPIList(BaseModel):
    kpi_list: list[str]