"""Architecture registry exports."""

from .debate import run_debate
from .ensemble import run_ensemble
from .parallel_roles import run_parallel_roles
from .sas import run_sas
from .sequential import run_sequential
from .subtask_parallel import run_subtask_parallel

__all__ = [
    "run_sas",
    "run_sequential",
    "run_subtask_parallel",
    "run_parallel_roles",
    "run_debate",
    "run_ensemble",
]
