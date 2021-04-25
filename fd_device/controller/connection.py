"""Connect to and receive messages from rabbitmq."""
import pika

from fd_device.settings import get_config


class Connection:  # pylint: disable=too-many-instance-attributes
    """Connect to server via RabbitMQ."""

    def __init__(self, logger):
        """Create the Connection object."""

        self.LOGGER = logger

        # store and manage internal state
        self._connection = None
        self._channel = None
        self._closing = False

        config = get_config()

        # connection parameters
        self._user = config.RABBITMQ_USER
        self._password = config.RABBITMQ_PASSWORD
        # self._host = host - this is set in the overwritten function
        self._port = 5672
        self._virtual_host = config.RABBITMQ_VHOST

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.

        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        self.LOGGER.info("Connecting to RabbitMQ")
        creds = pika.PlainCredentials(self._user, self._password)
        params = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            virtual_host=self._virtual_host,
            credentials=creds,
        )
        return pika.SelectConnection(
            parameters=params,
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed,
        )

    def on_connection_open(self, _unused_connection):
        """This method is called by pika once the connection to RabbitMQ has been established.

        It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type _unused_connection: pika.SelectConnection

        """
        self.LOGGER.debug("Connection opened")
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        """This method is called by pika if the connection to RabbitMQ can't be established.

        :param pika.SelectConnection _unused_connection: The connection
        :param Exception err: The error
        """
        self.LOGGER.error("Connection open failed: %s", err)
        self.reconnect()

    def on_connection_closed(self, _unused_connection, reason):
        """This method is invoked by pika when the connection to RabbitMQ is closed unexpectedly.

        Since it is unexpected, we will reconnect to RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param Exception reason: exception representing reason for loss of connection.

        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            self.LOGGER.warning("Connection closed, reopening in 5 seconds: %s", reason)
            self._connection.ioloop.call_later(5, self.reconnect)

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is closed.

        See the on_connection_closed method.
        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        # Create a new connection
        self._connection = self.connect()

        # There is now a new connection, needs a new ioloop to run
        self._connection.ioloop.start()

    def open_channel(self):
        """This method will open a new channel with RabbitMQ by issuing the Channel.Open RPC command.

        When RabbitMQ confirms the channel is open by sending the Channel.OpenOK RPC reply,
        the on_channel_open method will be invoked.
        """
        self.LOGGER.debug("Creating a new channel")
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.

        The channel object is passed in so we can make use of it.
        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        self.LOGGER.debug("Channel opened")
        self._channel = channel
        self.add_on_channel_close_callback()

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if RabbitMQ unexpectedly closes the channel."""
        self.LOGGER.debug("Adding channel close callback")
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, _channel, reason):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.

        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param str reason: The reason the channel was closed

        """
        if not self._closing:
            self.LOGGER.warning("Channel was closed: %s", reason)
            self._connection.close()

    def close_channel(self):
        """Invoke this command to close the channel with RabbitMQ by sending the Channel.Close RPC command."""
        self.LOGGER.debug("Closing the channel")
        if self._channel:
            self._channel.close()

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        self.LOGGER.debug("Closing connection")
        self._closing = True
        self._connection.close()

    def run(self):
        """Run the example code by connecting and then starting the IOLoop."""
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Stop the example by closing the channel and connection.

        We set a flag here so that we stop scheduling new messages to be
        published. The IOLoop is started because this method is
        invoked by the Try/Catch below when KeyboardInterrupt is caught.
        Starting the IOLoop again will allow the publisher to cleanly
        disconnect from RabbitMQ.
        """
        self.LOGGER.info("Stopping")
        self._closing = True
        self.close_channel()
        self.close_connection()
        self._connection.ioloop.start()
        self.LOGGER.info("Stopped")


class Message:
    """Receive messages from RabbitMQ."""

    def __init__(self, channel):
        """Instantiate a Message instance."""

        self.LOGGER = None

        self._channel = channel
        self._stopping = False
        self._consumer_tag = None

        self.exchange_name = None
        self.exchange_type = None
        self.routing_key = None
        self.queue_name = None

        # self.setup_exchange(self.exchange_name) must be called from the
        # class that inherits from this class.

    def set_stopping(self, state):
        """Set the _stopping state."""
        self._stopping = state

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC command.

        When it is complete, the on_exchange_declareok method will be invoked by pika.

        :param str|unicode exchange_name: The name of the exchange to declare
        """
        self.LOGGER.debug("Declaring exchange %s", exchange_name)
        self._channel.exchange_declare(
            callback=self.on_exchange_declareok,
            exchange=exchange_name,
            exchange_type=self.exchange_type,
        )

    def on_exchange_declareok(self, unused_frame):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC command.

        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame
        """
        self.LOGGER.debug("Exchange declared")
        self.setup_queue()

    def setup_queue(self):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC command.

        When it is complete, the on_queue_declareok method will be invoked by pika.

        :param str|unicode queue_name: The name of the queue to declare.
        """
        self.LOGGER.debug("Declaring reply queue")
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
        self.LOGGER.info(
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
        self.LOGGER.debug("Queue bound")
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
        self.LOGGER.debug("Issuing consumer related RPC commands")
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(
            on_message_callback=self.on_message, queue=self.queue_name
        )

    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the consumer for some reason.

        If RabbitMQ does cancel the consumer, on_consumer_cancelled will be invoked by pika.
        """
        self.LOGGER.debug("Adding consumer cancellation callback")
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):  # pylint: disable=no-self-use
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        self.LOGGER.warning("Consumer was cancelled remotely: %r", method_frame)
        if self._channel:
            self._channel.close()

    # pylint: disable=unused-argument
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

        self.LOGGER.debug(
            f"Received message # {basic_deliver.delivery_tag} from {properties.app_id}"
        )

    def acknowledge_message(self, delivery_tag):
        """Acknowledge the message delivery from RabbitMQ by sending a Basic.Ack RPC method for the delivery tag.

        :param int delivery_tag: The delivery tag from the Basic.Deliver frame

        """
        # self.LOGGER.debug(f'Acknowledging message {delivery_tag}')
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the Basic.Cancel RPC command."""
        if self._channel:
            self.LOGGER.debug("Sending a Basic.Cancel RPC command to RabbitMQ")
            self._channel.basic_cancel(
                consumer_tag=self._consumer_tag, callback=self.on_cancelok
            )

    def on_cancelok(self, unused_frame):  # pylint: disable=no-self-use
        """This method is invoked by pika when RabbitMQ acknowledges the cancellation of a consumer.

        At this point we will close the channel.
        This will invoke the on_channel_closed method once the channel has been
        closed, which will in-turn close the connection.

        :param pika.frame.Method unused_frame: The Basic.CancelOk frame
        """
        self.LOGGER.debug("RabbitMQ acknowledged the cancellation of the consumer")
