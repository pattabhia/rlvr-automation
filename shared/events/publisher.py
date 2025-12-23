"""
Event Publisher for RabbitMQ

Publishes events to RabbitMQ exchange with automatic reconnection.
"""

import json
import logging
import time
from typing import Dict, Any, Optional
import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, AMQPChannelError, StreamLostError

from .schemas import BaseEvent

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Event Publisher for RabbitMQ
    
    Usage:
        publisher = EventPublisher(rabbitmq_url="amqp://user:pass@localhost:5672/")
        await publisher.publish(event)
    """
    
    def __init__(
        self,
        rabbitmq_url: str,
        exchange_name: str = "rlvr_events",
        exchange_type: str = "topic",
        max_retries: int = 5,
        retry_delay: int = 2
    ):
        """
        Initialize event publisher

        Args:
            rabbitmq_url: RabbitMQ connection URL
            exchange_name: Name of the exchange
            exchange_type: Type of exchange (topic, fanout, direct)
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
        
    def connect(self):
        """Establish connection to RabbitMQ with retry logic"""
        for attempt in range(self.max_retries):
            try:
                # Configure connection parameters with heartbeat
                parameters = pika.URLParameters(self.rabbitmq_url)
                parameters.heartbeat = 600  # 10 minutes
                parameters.blocked_connection_timeout = 300  # 5 minutes
                parameters.connection_attempts = 3
                parameters.retry_delay = 2

                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()

                # Declare exchange
                self.channel.exchange_declare(
                    exchange=self.exchange_name,
                    exchange_type=self.exchange_type,
                    durable=True
                )

                logger.info(f"✅ Connected to RabbitMQ: {self.exchange_name}")
                return

            except (AMQPConnectionError, AMQPChannelError, StreamLostError) as e:
                logger.warning(
                    f"⚠️  Connection attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"❌ Failed to connect to RabbitMQ after {self.max_retries} attempts"
                    )
                    raise

    def ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        try:
            # Check if connection exists and is open
            if not self.connection or self.connection.is_closed:
                logger.warning("🔄 Connection lost, reconnecting...")
                self.connect()
                return

            # Check if channel exists and is open
            if not self.channel or self.channel.is_closed:
                logger.warning("🔄 Channel lost, recreating...")
                self.channel = self.connection.channel()

                # Re-declare exchange
                self.channel.exchange_declare(
                    exchange=self.exchange_name,
                    exchange_type=self.exchange_type,
                    durable=True
                )

        except Exception as e:
            logger.error(f"❌ Error ensuring connection: {e}")
            self.connect()
    
    def disconnect(self):
        """Close connection to RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    def publish(
        self,
        event: BaseEvent,
        routing_key: Optional[str] = None,
        max_publish_retries: int = 3
    ):
        """
        Publish event to RabbitMQ with automatic reconnection and retry

        Args:
            event: Event to publish
            routing_key: Routing key (defaults to event_type)
            max_publish_retries: Maximum retry attempts for publishing
        """
        # Use event_type as routing key if not specified
        if routing_key is None:
            routing_key = event.event_type

        # Serialize event
        message = json.dumps(event.to_dict())

        # Retry publishing with reconnection
        last_error = None
        for attempt in range(max_publish_retries):
            try:
                # Ensure connection is alive before each attempt
                self.ensure_connection()

                # Publish
                self.channel.basic_publish(
                    exchange=self.exchange_name,
                    routing_key=routing_key,
                    body=message,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Persistent
                        content_type="application/json",
                        headers={
                            "event_type": event.event_type,
                            "event_id": event.event_id,
                            "timestamp": event.timestamp
                        }
                    )
                )

                logger.info(
                    f"Published event: {event.event_type} "
                    f"(id={event.event_id}, routing_key={routing_key})"
                )
                return  # Success!

            except (AMQPConnectionError, AMQPChannelError, StreamLostError) as e:
                last_error = e
                logger.warning(
                    f"⚠️  Publish attempt {attempt + 1}/{max_publish_retries} failed: {e}"
                )

                # Force reconnection on next attempt
                try:
                    if self.connection and not self.connection.is_closed:
                        self.connection.close()
                except:
                    pass
                self.connection = None
                self.channel = None

                if attempt < max_publish_retries - 1:
                    time.sleep(1)  # Brief delay before retry

            except Exception as e:
                # Non-connection errors - don't retry
                logger.error(f"Failed to publish event: {e}")
                raise

        # All retries failed
        logger.error(f"❌ Failed to publish event after {max_publish_retries} attempts")
        raise last_error
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

