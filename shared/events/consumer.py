"""
Event Consumer for RabbitMQ

Consumes events from RabbitMQ queues with automatic reconnection.
"""

import json
import logging
import time
from typing import Callable, Dict, Any, Optional, List
import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, AMQPChannelError, StreamLostError

from .schemas import deserialize_event, BaseEvent

logger = logging.getLogger(__name__)


class EventConsumer:
    """
    Event Consumer for RabbitMQ
    
    Usage:
        consumer = EventConsumer(rabbitmq_url="amqp://user:pass@localhost:5672/")
        
        @consumer.subscribe("answer.generated")
        def handle_answer(event: AnswerGeneratedEvent):
            print(f"Received: {event.question}")
        
        consumer.start()
    """
    
    def __init__(
        self,
        rabbitmq_url: str,
        exchange_name: str = "rlvr_events",
        queue_name: Optional[str] = None,
        prefetch_count: int = 1,
        max_retries: int = 5,
        retry_delay: int = 2
    ):
        """
        Initialize event consumer

        Args:
            rabbitmq_url: RabbitMQ connection URL
            exchange_name: Name of the exchange
            queue_name: Name of the queue (auto-generated if None)
            prefetch_count: Number of messages to prefetch
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
        self.handlers: Dict[str, List[Callable]] = {}
        
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

                # Set QoS
                self.channel.basic_qos(prefetch_count=self.prefetch_count)

                # Declare exchange
                self.channel.exchange_declare(
                    exchange=self.exchange_name,
                    exchange_type="topic",
                    durable=True
                )

                # Declare queue
                if self.queue_name:
                    self.channel.queue_declare(queue=self.queue_name, durable=True)
                else:
                    # Auto-generate queue name
                    result = self.channel.queue_declare(queue="", exclusive=True)
                    self.queue_name = result.method.queue

                logger.info(f"✅ Connected to RabbitMQ: {self.queue_name}")
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
                # Re-bind queues after reconnection
                self._bind_queues()
                return

            # Check if channel exists and is open
            if not self.channel or self.channel.is_closed:
                logger.warning("🔄 Channel lost, recreating...")
                self.channel = self.connection.channel()
                self.channel.basic_qos(prefetch_count=self.prefetch_count)

                # Re-declare exchange
                self.channel.exchange_declare(
                    exchange=self.exchange_name,
                    exchange_type="topic",
                    durable=True
                )

                # Re-bind queues
                self._bind_queues()

        except Exception as e:
            logger.error(f"❌ Error ensuring connection: {e}")
            self.connect()
            self._bind_queues()

    def _bind_queues(self):
        """Bind queue to all registered event types"""
        if not self.channel or not self.queue_name:
            return

        for event_type in self.handlers.keys():
            try:
                self.channel.queue_bind(
                    exchange=self.exchange_name,
                    queue=self.queue_name,
                    routing_key=event_type
                )
                logger.debug(f"Bound queue to event type: {event_type}")
            except Exception as e:
                logger.error(f"Failed to bind queue to {event_type}: {e}")
    
    def subscribe(self, event_type: str):
        """
        Decorator to subscribe to an event type
        
        Args:
            event_type: Event type to subscribe to (e.g., "answer.generated")
        
        Usage:
            @consumer.subscribe("answer.generated")
            def handle_answer(event):
                print(event.question)
        """
        def decorator(handler: Callable):
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            self.handlers[event_type].append(handler)
            logger.info(f"Registered handler for: {event_type}")
            return handler
        return decorator
    
    def bind_routing_keys(self):
        """Bind queue to routing keys based on registered handlers"""
        for event_type in self.handlers.keys():
            self.channel.queue_bind(
                exchange=self.exchange_name,
                queue=self.queue_name,
                routing_key=event_type
            )
            logger.info(f"Bound queue to routing key: {event_type}")
    
    def _handle_message(
        self,
        ch: BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes
    ):
        """Internal message handler"""
        try:
            # Deserialize message
            message_dict = json.loads(body)
            event = deserialize_event(message_dict)
            
            logger.info(f"Received event: {event.event_type} (id={event.event_id})")
            
            # Call registered handlers
            if event.event_type in self.handlers:
                for handler in self.handlers[event.event_type]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(
                            f"Handler error for {event.event_type}: {e}",
                            exc_info=True
                        )
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            # Reject and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start(self):
        """Start consuming messages with automatic reconnection"""
        if not self.channel:
            self.connect()

        # Bind routing keys
        self.bind_routing_keys()

        # Start consuming with reconnection loop
        logger.info(f"Starting consumer on queue: {self.queue_name}")

        while True:
            try:
                # Ensure connection before consuming
                self.ensure_connection()

                self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._handle_message
                )

                logger.info("✅ Consumer started, waiting for messages...")
                self.channel.start_consuming()

            except KeyboardInterrupt:
                logger.info("⏹️  Stopping consumer...")
                if self.channel and not self.channel.is_closed:
                    self.channel.stop_consuming()
                break

            except (AMQPConnectionError, AMQPChannelError, StreamLostError) as e:
                logger.error(f"❌ Connection lost during consumption: {e}")
                logger.info(f"🔄 Reconnecting in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
                # Connection will be re-established in next loop iteration

            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                logger.info(f"🔄 Reconnecting in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)

        # Cleanup
        self.disconnect()
    
    def disconnect(self):
        """Close connection to RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Disconnected from RabbitMQ")

