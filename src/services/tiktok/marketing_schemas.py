from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
class Campaign(BaseModel):
    campaign_id: str = Field(..., description="Unique campaign identifier")
    campaign_name: str = Field(..., description="Campaign display name")
    objective_type: str = Field(..., description="Campaign objective (TRAFFIC, CONVERSIONS, etc.)")
    budget: Optional[float] = Field(None, description="Campaign budget in USD")
    status: str = Field(..., description="Campaign status (ENABLE, DISABLE, etc.)")
class AdReportMetrics(BaseModel):
    impressions: int = Field(default=0, description="Total ad impressions")
    clicks: int = Field(default=0, description="Total ad clicks")
    spend: float = Field(default=0.0, description="Total ad spend in USD")
    conversions: int = Field(default=0, description="Total conversions")
    ctr: float = Field(default=0.0, description="Click-through rate (%)")
    cpm: float = Field(default=0.0, description="Cost per mille (per 1000 impressions)")
    cpc: float = Field(default=0.0, description="Cost per click")
    conversion_rate: float = Field(default=0.0, description="Conversion rate (%)")
class AdReportRow(BaseModel):
    report_date: date = Field(..., description="Report date")
    metrics: AdReportMetrics = Field(..., description="Metrics for this date")
class AudienceReport(BaseModel):
    age_distribution: dict = Field(
        default_factory=dict,
        description='Age distribution (e.g., {"18-24": 0.25, "25-34": 0.40})'
    )
    gender_distribution: dict = Field(
        default_factory=dict,
        description='Gender distribution (e.g., {"male": 0.6, "female": 0.4})'
    )
    top_countries: List[dict] = Field(
        default_factory=list,
        description='Top countries (e.g., [{"country": "US", "percentage": 0.5}])'
    )
    top_interests: List[str] = Field(
        default_factory=list,
        description="Top audience interests/categories"
    )
class AdsMetricsPeriod(BaseModel):
    period: str = Field(..., description='Period name ("7d", "30d", "90d", "lifetime")')
    total_spend: float = Field(default=0.0, description="Total ad spend")
    total_impressions: int = Field(default=0, description="Total impressions")
    total_clicks: int = Field(default=0, description="Total clicks")
    total_conversions: int = Field(default=0, description="Total conversions")
    avg_ctr: float = Field(default=0.0, description="Average click-through rate")
    avg_cpm: float = Field(default=0.0, description="Average cost per mille")
    avg_conversion_rate: float = Field(default=0.0, description="Average conversion rate")
    campaigns_count: int = Field(default=0, description="Number of campaigns in period")
    top_campaigns: List[Campaign] = Field(
        default_factory=list,
        description="Top 5 campaigns by spend"
    )
