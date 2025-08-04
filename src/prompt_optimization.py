"""
Prompt Optimization System for Self-Optimizing Agents

This module provides tools for monitoring evaluation metrics and collecting
high-quality responses for dataset creation and prompt optimization.
"""

import asyncio
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import opik
from opik import opik_context
from opik import Opik
import json
import os
from opik_utils import is_opik_tracking_enabled, get_opik_tracking_status



@dataclass
class ResponseData:
    """Data structure for storing response information."""
    question: str
    answer: str
    usefulness_score: float
    question_number: Optional[int] = None
    additional_metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None





class PromptOptimizationManager:
    """
    Manages prompt optimization by monitoring evaluation metrics and collecting
    high-quality responses in a combined dataset for multi-dimensional optimization.
    """
    
    def __init__(self, dataset_name: str = "soa_prompt_optimization", default_threshold: float = 0.8):
        """
        Initialize the prompt optimization manager.
        
        Args:
            dataset_name: Name of the combined dataset for all metrics
            default_threshold: Default threshold for considering a response high-quality
        """
        self.dataset_name = dataset_name
        self.default_threshold = default_threshold
        self.dataset = None
        self._dataset_initialized = False
        self.thresholds = {
            "usefulness": 0.8,
            "answerrelevance": 0.9,
            "hallucination": 0.1,  # Lower is better
            "moderation": 0.7,
        }
    
    def _initialize_dataset(self) -> None:
        """
        Initialize or connect to the combined Opik dataset.
        """
        try:
            # Check if Opik tracking is enabled
            if not is_opik_tracking_enabled():
                print("[INFO] Opik tracking is disabled, skipping dataset initialization")
                self.dataset = None
                self._dataset_initialized = True
                return
            
            # Ensure Opik is configured for cloud usage if credentials are available
            import os
            opik_api_key = os.environ.get("OPIK_API_KEY")
            opik_workspace = os.environ.get("OPIK_WORKSPACE")
            
            if opik_api_key and opik_workspace:
                # Configure Opik for cloud usage
                opik.configure(use_local=False)
                print(f"[INFO] Opik configured for cloud usage with workspace: {opik_workspace}")
            else:
                print("[WARNING] OPIK_API_KEY or OPIK_WORKSPACE not set, using local configuration")
                opik.configure(use_local=True)
            
            # Create Opik client and get or create dataset
            client = Opik()
            self.dataset = client.get_or_create_dataset(name=self.dataset_name)
            self._dataset_initialized = True
            print(f"[INFO] Connected to combined Opik dataset: {self.dataset_name}")
                
        except Exception as e:
            print(f"[WARNING] Failed to initialize Opik dataset '{self.dataset_name}': {e}")
            self.dataset = None
            self._dataset_initialized = True  # Mark as initialized to avoid retrying
    
    async def collect_response_with_metrics(
        self,
        question: str,
        answer: str,
        metrics: Dict[str, float],
        question_number: Optional[int] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        baml_collector: Any = None,
        function_name: str = None
    ) -> None:
        """
        Collect response with all metrics in a combined dataset for multi-dimensional optimization.
        
        This method should be called after all metrics have been run and the span
        has been updated with feedback scores.
        
        Args:
            question: The input question
            answer: The generated answer
            metrics: Dictionary of metric names and their scores
            question_number: Optional question number for tracking
            additional_metadata: Additional metadata to store with the response
            baml_collector: Optional BAML collector to extract request data for optimization
            function_name: Optional function name filter for BAML request extraction
        """
        # Check if Opik tracking is enabled
        if not is_opik_tracking_enabled():
            print("[INFO] Opik tracking is disabled, skipping response collection")
            return
        
        # Initialize dataset if not already done
        if not self._dataset_initialized:
            self._initialize_dataset()
        
        if self.dataset is None:
            print("[WARNING] Dataset not initialized, skipping response collection")
            return
        
        try:
            if not metrics:
                print("[DEBUG] No metrics provided")
                return
            

            
            # Check if any metric meets its threshold (for logging purposes)
            high_quality_metrics = []
            for metric_name, score in metrics.items():
                threshold = self.thresholds.get(metric_name, self.default_threshold)
                if metric_name == "hallucination":
                    # For hallucination, lower is better
                    if score <= threshold:
                        high_quality_metrics.append(f"{metric_name}: {score:.3f} (≤{threshold})")
                else:
                    # For other metrics, higher is better
                    if score >= threshold:
                        high_quality_metrics.append(f"{metric_name}: {score:.3f} (≥{threshold})")
            
            if high_quality_metrics:
                print(f"[INFO] High-quality metrics found: {', '.join(high_quality_metrics)}")
            
            # Always add to dataset for comprehensive optimization data
            await self._add_to_dataset(
                question=question,
                answer=answer,
                metrics=metrics,
                question_number=question_number,
                additional_metadata=additional_metadata
            )
                
        except Exception as e:
            print(f"[ERROR] Error collecting response with metrics: {e}")
    

    
    async def _add_to_dataset(
        self,
        question: str,
        answer: str,
        metrics: Dict[str, float],
        question_number: Optional[int] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a response with all metrics to the combined dataset.
        
        Args:
            question: The input question
            answer: The generated answer
            metrics: Dictionary of all metric scores
            question_number: Optional question number for tracking
            additional_metadata: Additional metadata to store
        """
        try:
            # Prepare the dataset item with all metrics
            dataset_item = {
                "input": question,
                "output": answer,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "question_number": question_number,
                    "dataset_name": self.dataset_name,
                    **(additional_metadata or {})
                }
            }
            

            
            # Add to dataset using Opik SDK
            self.dataset.insert([dataset_item])
            
            metric_summary = ", ".join([f"{name}: {score:.3f}" for name, score in metrics.items()])
            print(f"[SUCCESS] Added response to dataset '{self.dataset_name}' with metrics: {metric_summary}")
            
        except Exception as e:
            print(f"[ERROR] Failed to add response to dataset: {e}")
    
    async def get_dataset_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the combined dataset.
        
        Returns:
            Dictionary containing dataset statistics for all metrics
        """
        # Initialize dataset if not already done
        if not self._dataset_initialized:
            self._initialize_dataset()
        
        if self.dataset is None:
            return {"error": "Dataset not initialized"}
        
        try:
            # Get dataset items
            items_json = self.dataset.to_json()
            
            # Parse JSON string to list
            if isinstance(items_json, str):
                items = json.loads(items_json)
            else:
                items = items_json
            
            if not items:
                return {
                    "total_items": 0,
                    "metrics": {}
                }
            
            # Calculate statistics for all metrics
            all_metrics = {}
            total_items = len(items)
            
            # Collect all unique metric names from the dataset
            metric_names = set()
            for item in items:
                if "metrics" in item and isinstance(item["metrics"], dict):
                    metric_names.update(item["metrics"].keys())
            
            # Calculate stats for each metric
            for metric_name in metric_names:
                metric_scores = []
                for item in items:
                    if "metrics" in item and isinstance(item["metrics"], dict):
                        score = item["metrics"].get(metric_name)
                        if score is not None:
                            metric_scores.append(score)
                
                if metric_scores:
                    threshold = self.thresholds.get(metric_name, self.default_threshold)
                    
                    # For hallucination, lower is better
                    if metric_name == "hallucination":
                        items_above_threshold = len([score for score in metric_scores if score <= threshold])
                    else:
                        items_above_threshold = len([score for score in metric_scores if score >= threshold])
                    
                    all_metrics[metric_name] = {
                        "count": len(metric_scores),
                        "average": sum(metric_scores) / len(metric_scores),
                        "highest": max(metric_scores),
                        "lowest": min(metric_scores),
                        "threshold": threshold,
                        "items_above_threshold": items_above_threshold
                    }
            
            return {
                "total_items": total_items,
                "metrics": all_metrics
            }
            
        except Exception as e:
            return {"error": f"Failed to get dataset stats: {e}"}
    
    async def list_dataset_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List items in the combined dataset.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of dataset items
        """
        # Initialize dataset if not already done
        if not self._dataset_initialized:
            self._initialize_dataset()
        
        if self.dataset is None:
            return []
        
        try:
            items_json = self.dataset.to_json()
            
            # Parse JSON string to list
            if isinstance(items_json, str):
                items = json.loads(items_json)
            else:
                items = items_json
                
            return items[:limit] if items else []
            
        except Exception as e:
            print(f"[ERROR] Failed to list dataset items: {e}")
            return []


# Global instance for easy access
prompt_optimizer = PromptOptimizationManager()


async def collect_response_with_metrics(
    question: str,
    answer: str,
    metrics: Dict[str, float],
    question_number: Optional[int] = None,
    additional_metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Convenience function to collect responses with all metrics in the combined dataset.
    
    Args:
        question: The input question
        answer: The generated answer
        metrics: Dictionary of all metric scores
        question_number: Optional question number for tracking
        additional_metadata: Additional metadata to store
    """
    await prompt_optimizer.collect_response_with_metrics(
        question=question,
        answer=answer,
        metrics=metrics,
        question_number=question_number,
        additional_metadata=additional_metadata
    )


# Example usage and testing functions
async def test_dataset_functionality():
    """Test the dataset functionality."""
    print("Testing Prompt Optimization Manager...")
    
    # Test dataset stats
    stats = await prompt_optimizer.get_dataset_stats()
    print(f"Dataset stats: {stats}")
    
    # Test listing items
    items = await prompt_optimizer.list_dataset_items(limit=5)
    print(f"Dataset items (first 5): {len(items)} items found")


if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_dataset_functionality()) 