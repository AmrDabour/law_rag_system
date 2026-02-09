"""
Pipeline Base Classes
Generic pipeline infrastructure for ingestion and query pipelines
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time
import logging
import traceback

logger = logging.getLogger(__name__)

# Generic type for pipeline data
T = TypeVar('T')


class StepStatus(str, Enum):
    """Pipeline step execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a single pipeline step"""
    step_name: str
    status: StepStatus
    duration_ms: float
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of complete pipeline execution"""
    success: bool
    data: Any
    steps: List[StepResult]
    total_duration_ms: float
    started_at: str
    completed_at: str
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def failed_steps(self) -> List[StepResult]:
        """Get list of failed steps"""
        return [s for s in self.steps if s.status == StepStatus.FAILED]
    
    @property
    def successful_steps(self) -> List[StepResult]:
        """Get list of successful steps"""
        return [s for s in self.steps if s.status == StepStatus.SUCCESS]


class PipelineStep(ABC):
    """
    Base class for pipeline steps.
    Each step processes input data and returns output data.
    """
    
    def __init__(self, name: str):
        """
        Initialize pipeline step.
        
        Args:
            name: Human-readable step name
        """
        self.name = name
        self.logger = logging.getLogger(f"pipeline.{name}")
    
    @abstractmethod
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process input data and return output.
        
        Args:
            data: Input data from previous step
            context: Shared context dict for passing data between steps
            
        Returns:
            Processed output data
        """
        pass
    
    def validate_input(self, data: Any) -> bool:
        """
        Validate input data before processing.
        Override in subclass for custom validation.
        
        Args:
            data: Input data to validate
            
        Returns:
            True if valid
        """
        return True
    
    def get_data_size(self, data: Any) -> Optional[int]:
        """
        Get size/count of data for logging.
        
        Args:
            data: Data to measure
            
        Returns:
            Size or None
        """
        if data is None:
            return 0
        if isinstance(data, (list, tuple)):
            return len(data)
        if isinstance(data, dict):
            return len(data)
        if isinstance(data, str):
            return len(data)
        if isinstance(data, bytes):
            return len(data)
        return None


class Pipeline:
    """
    Generic pipeline orchestrator.
    Executes a sequence of PipelineSteps with error handling and logging.
    """
    
    def __init__(self, name: str):
        """
        Initialize pipeline.
        
        Args:
            name: Pipeline name for logging
        """
        self.name = name
        self.steps: List[PipelineStep] = []
        self.logger = logging.getLogger(f"pipeline.{name}")
    
    def add_step(self, step: PipelineStep) -> 'Pipeline':
        """
        Add a step to the pipeline.
        
        Args:
            step: PipelineStep to add
            
        Returns:
            Self for chaining
        """
        self.steps.append(step)
        return self
    
    def run(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = True,
    ) -> PipelineResult:
        """
        Run the complete pipeline.
        
        Args:
            input_data: Initial input data
            context: Optional shared context dict
            stop_on_error: Stop pipeline on first error
            
        Returns:
            PipelineResult with all step results
        """
        started_at = datetime.now()
        pipeline_start = time.time()
        
        current_data = input_data
        context = context or {}
        step_results: List[StepResult] = []
        errors: List[str] = []
        
        self.logger.info(f"🚀 Starting pipeline: {self.name}")
        self.logger.info(f"   Steps: {len(self.steps)}")
        
        for i, step in enumerate(self.steps, 1):
            step_start = time.time()
            self.logger.info(f"   [{i}/{len(self.steps)}] {step.name}...")
            
            try:
                # Validate input
                if not step.validate_input(current_data):
                    raise ValueError(f"Invalid input for step: {step.name}")
                
                input_size = step.get_data_size(current_data)
                
                # Process
                output_data = step.process(current_data, context)
                
                output_size = step.get_data_size(output_data)
                duration_ms = (time.time() - step_start) * 1000
                
                step_results.append(StepResult(
                    step_name=step.name,
                    status=StepStatus.SUCCESS,
                    duration_ms=duration_ms,
                    input_size=input_size,
                    output_size=output_size,
                ))
                
                self.logger.info(f"       ✓ {step.name} ({duration_ms:.0f}ms)")
                
                # Update current data for next step
                current_data = output_data
                
            except Exception as e:
                duration_ms = (time.time() - step_start) * 1000
                error_msg = f"{step.name}: {str(e)}"
                
                step_results.append(StepResult(
                    step_name=step.name,
                    status=StepStatus.FAILED,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                
                errors.append(error_msg)
                self.logger.error(f"       ✗ {step.name} FAILED: {e}")
                self.logger.debug(traceback.format_exc())
                
                if stop_on_error:
                    break
        
        completed_at = datetime.now()
        total_duration = (time.time() - pipeline_start) * 1000
        success = len(errors) == 0
        
        if success:
            self.logger.info(f"✅ Pipeline completed successfully ({total_duration:.0f}ms)")
        else:
            self.logger.error(f"❌ Pipeline failed with {len(errors)} error(s)")
        
        return PipelineResult(
            success=success,
            data=current_data,
            steps=step_results,
            total_duration_ms=total_duration,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            errors=errors,
            metadata={
                "pipeline_name": self.name,
                "total_steps": len(self.steps),
                "completed_steps": len([s for s in step_results if s.status == StepStatus.SUCCESS]),
            }
        )
