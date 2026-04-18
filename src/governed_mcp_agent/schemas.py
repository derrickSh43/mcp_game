from pydantic import BaseModel, Field


class SecurityReviewRequest(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    system_name: str = Field(min_length=3, max_length=120)
    environment: str = Field(pattern="^(dev|staging|prod)$")
    requested_action: str = Field(min_length=5, max_length=200)
    contains_sensitive_data: bool = False