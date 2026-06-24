"""Import all models so Alembic can detect them."""
from trend_intel.models.agent_configs import AgentConfig
from trend_intel.models.candidates import Candidate
from trend_intel.models.discovery_sources import DiscoverySource
from trend_intel.models.rankings import Ranking
from trend_intel.models.reports import Report
from trend_intel.models.run_steps import RunStep
from trend_intel.models.runs import Run
from trend_intel.models.scoring_methods import ScoringMethod
from trend_intel.models.tool_profiles import ToolProfile
from trend_intel.models.tools import Tool

__all__ = [
    "AgentConfig",
    "Candidate",
    "DiscoverySource",
    "Ranking",
    "Report",
    "RunStep",
    "Run",
    "ScoringMethod",
    "ToolProfile",
    "Tool",
]
