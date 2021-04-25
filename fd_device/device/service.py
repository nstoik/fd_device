"""Device service package."""
import json
import logging
import uuid

import pika

from fd_device.celery_runner import app
from fd_device.controller.connection import Connection, Message
from fd_device.database.base import get_session
from fd_device.database.device import Connection as db_Connection
from fd_device.database.device import Device
from fd_device.device.update import get_device_info

LOGGER = logging.getLogger("fd.device.service")


class DeviceConnection(Connection):
    """Communicate with the Server via RabbitMQ."""

    def __init__(self, logger):
        """Overwrite the Connection __init__."""
        super().__init__(logger)

        # pylint: disable=invalid-name
        self.HEARTBEAT_MESSGES = None
        self.SERVER_MESSAGES = None

        self._session = get_session()
        self._host = self._session.query(db_Connection.address).scalar()

    def on_channel_open(self, channel):
        """Overwrite the on_channel_open method.

        Run normal commands, then create the HEARTBEAT_MESSAGES
        and SERVER_MESSAGES objects.
        """
        super().on_channel_open(channel)

        self.HEARTBEAT_MESSGES = HeartbeatMessage(
            self._connection, self._channel, self._session
        )
        self.SERVER_MESSAGES = ServerMessage(self._channel)

    def stop(self):
        """Overwrite the stop method.

        Stop the HEARTBEAT_MESSAGES and SERVER_MESSAGES objects, then
        stop the rest of the items.
        """
        self.HEARTBEAT_MESSGES.set_stopping(True)
        self.SERVER_MESSAGES.set_stopping(True)
        self.SERVER_MESSAGES.stop_consuming()

        self._session.close()
        super().stop()


class ServerMessage(Message):
    """Receive and respond to messages."""

    def __init__(self, channel):
        """Override the __init__ method from Message class.

        Create the logger instance, and se the required config info.
        Call the setup_exchange function to start the communication.
        """
        super().__init__(channel)

        self.LOGGER = logging.getLogger("fd.device.service.messages")

        self.exchange_name = "device_messages"
        self.exchange_type = "topic"
        self.routing_key = "all.create"

        self.setup_exchange(self.exchange_name)

    def on_message(self, unused_channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ.

        The channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.

        :param pika.channel.Channel unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param str|unicode body: The message body

        """
        payload = json.loads(body)
        command = payload["command"]

        LOGGER.debug(f"Received {command} command with key {basic_deliver.routing_key}")
        if command == "create":
            info = get_device_info()
            LOGGER.info("sending create task")
            value = app.send_task(name="device.create", args=(info,))
            print(value)
            LOGGER.info("create task sent")
            # LOGGER.info(f'return value {value.get()}')

        self._channel.basic_ack(basic_deliver.delivery_tag)


class HeartbeatMessage(Message):
    """Send heartbeat messages to the server."""

    # pylint: disable=too-many-instance-attributes

    HEARTBEAT_INTERVAL = 5
    TIMEOUT = 3
    MAX_MISSED_TIMEOUTS = 3
    # state can be 'disconnected', 'connected', 'new'
    STATE = "disconnected"

    def __init__(self, connection, channel, session):
        """Overwrite the __init__ method from Message class.

        Creat the logger instance, and set the required config info.
        Call the setup_exchange function to start the communication.
        """
        super().__init__(channel)

        self.LOGGER = logging.getLogger("fd.device.service.heartbeat")

        self._connection = connection
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0
        self._response = False
        self._corr_id = None
        self._timeouts_missed = 0
        self._session = session
        self.device_id = self._session.query(Device.device_id).scalar()

        # communication parameters
        self.exchange_name = "heartbeat_messages"
        self.exchange_type = "direct"
        self.routing_key = "heartbeat"

        self.setup_exchange(self.exchange_name)

    def on_queue_declareok(self, method_frame):
        """Overwrite from the Message class.

        Instead of binding to the queue, issue a basic_consuming,
        and start publishing heartbeats instead.
        """

        self.queue_name = method_frame.method.queue
        self.LOGGER.debug("Queue declared with name %s", self.queue_name)
        self._channel.basic_consume(
            on_message_callback=self.on_reply_received,
            queue=self.queue_name,
            auto_ack=True,
        )
        self.start_publishing()

    def start_publishing(self):
        """This method will enable delivery confirmations and schedule the first message to be sent to RabbitMQ."""
        self.LOGGER.info("Issuing consumer related RPC commands")
        self.enable_delivery_confirmations()
        self.schedule_next_message()

    def enable_delivery_confirmations(self):
        """Send the Confirm.Select RPC method to RabbitMQ to enable delivery confirmations on the channel.

        The only way to turn this off is to close the channel and create a new one.

        When the message is confirmed from RabbitMQ, the
        on_delivery_confirmation method will be invoked passing in a Basic.Ack
        or Basic.Nack method from RabbitMQ that will indicate which messages it
        is confirming or rejecting.
        """
        self.LOGGER.debug("Issuing Confirm.Select RPC command")
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        """Invoked by pika when RabbitMQ responds to a Basic.Publish RPC command.

        It passes in either a Basic.Ack or Basic.Nack frame with
        the delivery tag of the message that was published. The delivery tag
        is an integer counter indicating the message number that was sent
        on the channel via Basic.Publish. Here we're just doing house keeping
        to keep track of stats and remove message numbers that we expect
        a delivery confirmation of from the list used to keep track of messages
        that are pending confirmation.

        :param pika.frame.Method method_frame: Basic.Ack or Basic.Nack frame
        """
        confirmation_type = method_frame.method.NAME.split(".")[1].lower()
        # self.LOGGER.debug(f'Received {confirmation_type} for delivery tag: {method_frame.method.delivery_tag}')
        if confirmation_type == "ack":
            self._acked += 1
        elif confirmation_type == "nack":
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)

        # self.LOGGER.debug(
        #     (
        #         f"Published {self._message_number} messages, "
        #         f"{len(self._deliveries)} to be confirmed, "
        #        f"{self._acked} were acked and {self._nacked} were nacked"
        #     )
        # )

    def schedule_next_message(self):
        """If not closing connection to RabbitMQ, schedule another message in PUBLISH_INTERVAL seconds."""
        if self._stopping:
            return
        # LOGGER.debug(f'Scheduling next message for {self.HEARTBEAT_INTERVAL} seconds')
        self._connection.ioloop.call_later(
            self.HEARTBEAT_INTERVAL, self.publish_message
        )

    def publish_message(self):
        """If the class is not stopping, publish a message to RabbitMQ.

        Appending a list of deliveries with the message number that was sent.
        This list will be used to check for delivery confirmations in the
        on_delivery_confirmations method.

        Once the message has been sent, schedule another message to be sent.
        The main reason I put scheduling in was just so you can get a good idea
        of how the process is flowing by slowing down and speeding up the
        delivery intervals by changing the PUBLISH_INTERVAL constant in the
        class.

        """
        if self._stopping:
            return

        self._response = False

        message = {"heartbeat": self._message_number}

        self._corr_id = str(uuid.uuid4())

        properties = pika.BasicProperties(
            app_id=self.device_id,
            content_type="application/json",
            reply_to=self.queue_name,
            correlation_id=self._corr_id,
        )

        self._channel.basic_publish(
            exchange=self.exchange_name,
            routing_key=self.routing_key,
            body=json.dumps(message, ensure_ascii=False),
            properties=properties,
        )
        self._message_number += 1
        self._deliveries.append(self._message_number)
        # self.LOGGER.debug(f'Published heartbeat message # {self._message_number}')
        self.schedule_next_message()

        self._connection.ioloop.call_later(self.TIMEOUT, self.check_timeout)

    def on_reply_received(self, _channel, _method, header, _body):
        """Method is triggered when a reply is received."""
        if self._corr_id == header.correlation_id:
            self._response = True
            self._timeouts_missed = 0
            if not self.STATE == "connected":
                self.STATE = "connected"
                self.LOGGER.info("STATE connected")

    def check_timeout(self):
        """Check timeout status and update the state of the device."""
        if not self._response:
            self._timeouts_missed += 1
            self.LOGGER.debug("Heartbeat timeout")

        if self._timeouts_missed == self.MAX_MISSED_TIMEOUTS + 1:
            self.LOGGER.warning(
                f"More than {self.MAX_MISSED_TIMEOUTS} timeouts missed. STATE disconnected"
            )
            self.STATE = "disconnected"


def run_connection():
    """Run the device connection."""

    device_connection = DeviceConnection(logger=LOGGER)

    try:
        device_connection.run()
    except KeyboardInterrupt:
        LOGGER.info("Stopping device connection")
        device_connection.stop()
