"""
Dataset Generation Worker - Combines events into training datasets

This worker:
1. Consumes answer.generated, verification.completed, and reward.computed events
2. Aggregates related events by question+answer
3. Writes complete entries to JSONL training data files
"""

import os
import sys
import logging
import time
import threading
from typing import Dict, Any

# Add shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from shared.events.consumer import EventConsumer
from shared.events.schemas import (
    AnswerGeneratedEvent,
    VerificationCompletedEvent,
    RewardComputedEvent
)
from src.event_aggregator import EventAggregator
from src.dataset_writer import DatasetWriter, DPODatasetWriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetGenerationWorker:
    """
    Worker that generates training datasets from events.
    
    Workflow:
    1. Consume answer.generated, verification.completed, reward.computed events
    2. Aggregate events by question+answer
    3. When all events received, write to training data file
    """
    
    def __init__(
        self,
        rabbitmq_url: str,
        output_dir: str = "/app/data/training_data",
        dpo_output_dir: str = "/app/data/dpo_data",
        timeout_minutes: int = 5,
        cleanup_interval_seconds: int = 300,
        min_score_diff: float = 0.3,  # Increased from 0.15
        min_chosen_score: float = 0.7,  # New parameter
        enable_quality_filter: bool = True  # New parameter
    ):
        """
        Initialize Dataset Generation Worker.

        Args:
            rabbitmq_url: RabbitMQ connection URL
            output_dir: Directory to write training data files
            dpo_output_dir: Directory to write DPO data files
            timeout_minutes: How long to wait for all events
            cleanup_interval_seconds: How often to cleanup expired entries
            min_score_diff: Minimum score difference for DPO pairs (default: 0.3)
            min_chosen_score: Minimum score for chosen answer (default: 0.7)
            enable_quality_filter: Enable behavioral quality checks (default: True)
        """
        self.rabbitmq_url = rabbitmq_url
        self.cleanup_interval_seconds = cleanup_interval_seconds

        # Initialize aggregator and writers
        self.aggregator = EventAggregator(timeout_minutes=timeout_minutes)
        self.writer = DatasetWriter(output_dir=output_dir)
        self.dpo_writer = DPODatasetWriter(
            output_dir=dpo_output_dir,
            min_score_diff=min_score_diff,
            min_chosen_score=min_chosen_score,
            enable_quality_filter=enable_quality_filter
        )
        
        # Initialize event consumers (one per event type)
        self.consumers = []
        
        # Statistics
        self.stats = {
            "answer_events": 0,
            "verification_events": 0,
            "reward_events": 0,
            "complete_entries": 0,
            "expired_entries": 0,
        }
        
        logger.info("Dataset Generation Worker initialized")
    
    def process_answer_generated(self, event: AnswerGeneratedEvent) -> None:
        """Process answer.generated event."""
        try:
            correlation_id = getattr(event, 'correlation_id', 'N/A')
            batch_id = getattr(event, 'batch_id', 'N/A')

            logger.debug(f"[correlation_id={correlation_id}] [batch_id={batch_id}] Received answer.generated: {event.event_id}")
            self.stats["answer_events"] += 1

            complete_entry = self.aggregator.add_answer_generated(event)

            if complete_entry:
                self._write_complete_entry(complete_entry)

        except Exception as e:
            logger.error(f"Error processing answer.generated: {e}", exc_info=True)

    def process_verification_completed(self, event: VerificationCompletedEvent) -> None:
        """Process verification.completed event."""
        try:
            correlation_id = getattr(event, 'correlation_id', 'N/A')

            logger.debug(f"[correlation_id={correlation_id}] Received verification.completed: {event.event_id}")
            self.stats["verification_events"] += 1

            complete_entry = self.aggregator.add_verification_completed(event)

            if complete_entry:
                self._write_complete_entry(complete_entry)

        except Exception as e:
            logger.error(f"Error processing verification.completed: {e}", exc_info=True)
    
    def process_reward_computed(self, event: RewardComputedEvent) -> None:
        """Process reward.computed event."""
        try:
            logger.debug(f"Received reward.computed: {event.event_id}")
            self.stats["reward_events"] += 1
            
            complete_entry = self.aggregator.add_reward_computed(event)
            
            if complete_entry:
                self._write_complete_entry(complete_entry)
                
        except Exception as e:
            logger.error(f"Error processing reward.computed: {e}", exc_info=True)
    
    def _write_complete_entry(self, entry: Dict) -> None:
        """Write complete entry to dataset and try to create DPO pairs."""
        try:
            # Write standard training data
            self.writer.write_entry(entry)
            self.stats["complete_entries"] += 1

            # Try to create DPO pairs
            self.dpo_writer.add_entry(entry)

            logger.info(
                f"Complete entry written! "
                f"Total: {self.stats['complete_entries']} "
                f"(answer={self.stats['answer_events']}, "
                f"verification={self.stats['verification_events']}, "
                f"reward={self.stats['reward_events']})"
            )

        except Exception as e:
            logger.error(f"Error writing complete entry: {e}", exc_info=True)
    
    def cleanup_expired_entries(self):
        """Periodically cleanup expired entries."""
        while True:
            try:
                time.sleep(self.cleanup_interval_seconds)
                
                expired = self.aggregator.cleanup_expired()
                if expired > 0:
                    self.stats["expired_entries"] += expired
                    logger.warning(f"Cleaned up {expired} expired entries")
                
                # Log statistics
                logger.info(
                    f"Stats: {self.stats['complete_entries']} complete, "
                    f"{self.aggregator.get_stats()['pending_entries']} pending, "
                    f"{self.stats['expired_entries']} expired"
                )
                
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}", exc_info=True)
    
    def start(self):
        """Start consuming events."""
        logger.info("Starting Dataset Generation Worker...")
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self.cleanup_expired_entries, daemon=True)
        cleanup_thread.start()
        logger.info("Cleanup thread started")
        
        # Create consumers for each event type
        logger.info("Creating event consumers...")
        
        # Note: We need to create separate consumers for each event type
        # because EventConsumer.consume() is blocking
        # In production, you'd use multiple threads or processes
        
        # For now, we'll consume all events from a single queue
        # and route them based on event_type
        
        consumer = EventConsumer(rabbitmq_url=self.rabbitmq_url)

        def route_event(event):
            """Route event to appropriate handler based on type."""
            if isinstance(event, AnswerGeneratedEvent):
                self.process_answer_generated(event)
            elif isinstance(event, VerificationCompletedEvent):
                self.process_verification_completed(event)
            elif isinstance(event, RewardComputedEvent):
                self.process_reward_computed(event)
            else:
                logger.warning(f"Unknown event type: {type(event)}")

        # Subscribe to all relevant events using wildcard routing key
        logger.info("Subscribing to events: answer.*, verification.*, reward.*")

        # Subscribe to all event types using decorator
        @consumer.subscribe("answer.generated")
        def handle_answer(event):
            route_event(event)

        @consumer.subscribe("verification.completed")
        def handle_verification(event):
            route_event(event)

        @consumer.subscribe("reward.computed")
        def handle_reward(event):
            route_event(event)

        # Start consuming
        consumer.start()


def main():
    """Main entry point."""
    # Load configuration from environment
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://rlvr:rlvr_password@rabbitmq:5672/")
    output_dir = os.getenv("OUTPUT_DIR", "/app/data/training_data")
    dpo_output_dir = os.getenv("DPO_OUTPUT_DIR", "/app/data/dpo_data")
    timeout_minutes = int(os.getenv("TIMEOUT_MINUTES", "5"))
    cleanup_interval = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "300"))

    # DPO quality parameters (increased thresholds for better quality)
    min_score_diff = float(os.getenv("MIN_SCORE_DIFF", "0.3"))  # Increased from 0.15
    min_chosen_score = float(os.getenv("MIN_CHOSEN_SCORE", "0.7"))  # New parameter
    enable_quality_filter = os.getenv("ENABLE_QUALITY_FILTER", "true").lower() == "true"

    # Create and start worker
    worker = DatasetGenerationWorker(
        rabbitmq_url=rabbitmq_url,
        output_dir=output_dir,
        dpo_output_dir=dpo_output_dir,
        timeout_minutes=timeout_minutes,
        cleanup_interval_seconds=cleanup_interval,
        min_score_diff=min_score_diff,
        min_chosen_score=min_chosen_score,
        enable_quality_filter=enable_quality_filter
    )

    # Start consuming events
    worker.start()


if __name__ == "__main__":
    main()

