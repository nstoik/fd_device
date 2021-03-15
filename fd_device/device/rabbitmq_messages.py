"""Recieve and process messages from rabbitmq."""
import json
import logging

from fd_device.celery_runner import app
from fd_device.device.update import get_device_info

LOGGER = logging.getLogger("fd.device.messages")


class ReceiveMessages:
    """Class that receievs and processes messages."""

    def __init__(self, channel):
        """Create the ReceieveMessages object."""

        self._channel = channel
        self._consumer_tag = None

        self.exchange_name = "device_messages"
        self.exchange_type = "topic"
        self.queue_name = None
        self.routing_key = "all.create"

        self.setup_exchange(self.exchange_name)

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC command.

        When it is complete, the on_exchange_declareok method will be invoked by pika.

        :param str|unicode exchange_name: The name of the exchange to declare
        """
        LOGGER.debug("Declaring exchange %s", exchange_name)
        self._channel.exchange_declare(
            callback=self.on_exchange_declareok,
            exchange=exchange_name,
            exchange_type=self.exchange_type,
        )

    def on_exchange_declareok(self, unused_frame):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC command.

        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame
        """
        LOGGER.debug("Exchange declared")
        self.setup_queue()

    def setup_queue(self):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC command.

        When it is complete, the on_queue_declareok method will be invoked by pika.

        :param str|unicode queue_name: The name of the queue to declare.
        """
        LOGGER.debug("Declaring reply queue")
        self._channel.queue_declare(
            queue="", callback=self.on_queue_declareok, exclusive=True, auto_delete=True
        )

    def on_queue_declareok(self, method_frame):
        """Method invoked by pika when the Queue.Declare RPC call made in setup_queue has completed.

        In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.

        :param pika.frame.Method method_frame: The Queue.DeclareOk frame
        """
        self.queue_name = method_frame.method.queue
        LOGGER.info(
            "Binding %s to %s with %s",
            self.exchange_name,
            self.queue_name,
            self.routing_key,
        )
        self._channel.queue_bind(
            callback=self.on_bindok,
            queue=self.queue_name,
            exchange=self.exchange_name,
            routing_key=self.routing_key,
        )

    def on_bindok(self, unused_frame):
        """Invoked by pika when the Queue.Bind method has completed.

        At this point we will start consuming messages by calling start_consuming
        which will invoke the needed RPC commands to start the process.

        :param pika.frame.Method unused_frame: The Queue.BindOk response frame
        """
        LOGGER.debug("Queue bound")
        self.start_consuming()

    def start_consuming(self):
        """This method sets up the consumer.

        First calling add_on_cancel_callback so that the object is notified if RabbitMQ
        cancels the consumer. It then issues the Basic.Consume RPC command
        which returns the consumer tag that is used to uniquely identify the
        consumer with RabbitMQ. We keep the value to use it when we want to
        cancel consuming. The on_message method is passed in as a callback pika
        will invoke when a message is fully received.
        """
        LOGGER.debug("Issuing consumer related RPC commands")
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(
            on_message_callback=self.on_message, queue=self.queue_name
        )

    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the consumer for some reason.

        If RabbitMQ does cancel the consumer, on_consumer_cancelled will be invoked by pika.
        """
        LOGGER.debug("Adding consumer cancellation callback")
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        LOGGER.warning("Consumer was cancelled remotely: %r", method_frame)

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the Basic.Cancel RPC command."""
        if self._channel:
            LOGGER.debug("Sending a Basic.Cancel RPC command to RabbitMQ")
            self._channel.basic_cancel(
                consumer_tag=self._consumer_tag, callback=self.on_cancelok
            )

    def on_cancelok(self, unused_frame):
        """This method is invoked by pika when RabbitMQ acknowledges the cancellation of a consumer.

        At this point we will close the channel.
        This will invoke the on_channel_closed method once the channel has been
        closed, which will in-turn close the connection.

        :param pika.frame.Method unused_frame: The Basic.CancelOk frame
        """
        LOGGER.debug("RabbitMQ acknowledged the cancellation of the consumer")

    def on_message(self, channel, method, header, body):
        """This method is invoked when a message is received."""

        payload = json.loads(body)
        command = payload["command"]

        LOGGER.debug(f"Received {command} command with key {method.routing_key}")
        if command == "create":
            info = get_device_info()
            LOGGER.info("sending create task")
            value = app.send_task(name="device.create", args=(info,))
            print(value)
            LOGGER.info("create task sent")
            # LOGGER.info(f'return value {value.get()}')

        self._channel.basic_ack(method.delivery_tag)
