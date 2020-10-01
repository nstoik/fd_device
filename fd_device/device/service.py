""" device service package """
import logging
import time
import uuid
import json

import pika

from fd_device.settings import get_config
from fd_device.database.base import get_session
from fd_device.database.device import Connection, Device

from .rabbitmq_messages import ReceiveMessages

LOGGER = logging.getLogger('fd.device.service')


class DeviceConnection():
    """ connect to server via RabbitMQ """

    def __init__(self):

        self.HEARTBEAT = None
        self.MESSAGE_RECEIVER = None

        # store and manage internal state
        self._connection = None
        self._channel = None
        self._stopping = False
        self._closing = False
        self._session = None

        # retrieve variables from config and database
        config = get_config()
        self._session = get_session()
        host = self._session.query(Connection.address).scalar()
        
        # connection parameters
        self._user = config.RABBITMQ_USER
        self._password = config.RABBITMQ_PASSWORD
        self._host = host
        self._port = 5672
        self._virtual_host = config.RABBITMQ_VHOST

        return

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        LOGGER.info('Connecting to RabbitMQ')
        creds = pika.PlainCredentials(self._user, self._password)
        params = pika.ConnectionParameters(host=self._host, port=self._port,
                                           virtual_host=self._virtual_host, credentials=creds)
        return pika.SelectConnection(parameters=params,
                                     on_open_callback=self.on_connection_open,
                                     on_open_error_callback=self.on_connection_open_error,
                                     on_close_callback=self.on_connection_closed)
    
    def on_connection_open(self, _unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type _unused_connection: pika.SelectConnection

        """
        LOGGER.debug('Connection opened')
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        """This method is called by pika if the connection to RabbitMQ
        can't be established.
        :param pika.SelectConnection _unused_connection: The connection
        :param Exception err: The error
        """
        LOGGER.error('Connection open failed: %s', err)
        self.reconnect()

    def on_connection_closed(self, _unused_connection, reason):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param Exception reason: exception representing reason for loss of connection.

        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reopening in 5 seconds: %s', reason)
            self._connection.ioloop.call_later(5, self.reconnect)
    
    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0

        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        # Create a new connection
        self._connection = self.connect()

        # There is now a new connection, needs a new ioloop to run
        self._connection.ioloop.start()

    def open_channel(self):
        """This method will open a new channel with RabbitMQ by issuing the
        Channel.Open RPC command. When RabbitMQ confirms the channel is open
        by sending the Channel.OpenOK RPC reply, the on_channel_open method
        will be invoked.

        """
        LOGGER.debug('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        LOGGER.debug('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.HEARTBEAT = Heartbeat(self._connection, self._channel, self._session)
        self.MESSAGE_RECEIVER = ReceiveMessages(self._channel)

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.

        """
        LOGGER.debug('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param str reason: The reason the channel was closed

        """
        if not self._closing:
            LOGGER.warning('Channel was closed: %s', reason)
            self._connection.close()

    def close_channel(self):
        """Invoke this command to close the channel with RabbitMQ by sending
        the Channel.Close RPC command.

        """
        LOGGER.debug('Closing the channel')
        if self._channel:
            self._channel.close()

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        LOGGER.debug('Closing connection')
        self._closing = True
        self._connection.close()

    def run(self):
        """Run the example code by connecting and then starting the IOLoop.

        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Stop the example by closing the channel and connection. We
        set a flag here so that we stop scheduling new messages to be
        published. The IOLoop is started because this method is
        invoked by the Try/Catch below when KeyboardInterrupt is caught.
        Starting the IOLoop again will allow the publisher to cleanly
        disconnect from RabbitMQ.

        """
        LOGGER.info('Stopping')
        self._stopping = True
        self.HEARTBEAT.set_stopping(True)
        self.MESSAGE_RECEIVER.stop_consuming()
        self.close_channel()
        self.close_connection()
        self._connection.ioloop.start()
        self._session.close()
        LOGGER.info('Stopped')


class Heartbeat():

    HEARTBEAT_INTERVAL = 5
    TIMEOUT = 3
    MAX_MISSED_TIMEOUTS = 3
    # state can be 'disconnected', 'connected', 'new'
    STATE = "disconnected"

    def __init__(self, connection, channel, session):

        self.LOGGER = LOGGER

        # store and manage internal state
        self._connection = connection
        self._channel = channel
        self._stopping = False
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0
        self._response = False
        self._corr_id = None
        self._timeouts_missed = 0
        self._session = session

        device_id = self._session.query(Device.id).scalar()

        # communication parameters
        self.exchange_name = 'heartbeat_events'
        self.exchange_type = 'direct'
        self.routing_key = 'heartbeat'
        self.reply_queue_name = None
        self.device_id = device_id

        self.setup_exchange(self.exchange_name)

    def set_stopping(self, state):
        """Set the _stopping state"""
        self._stopping = state

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.

        :param str|unicode exchange_name: The name of the exchange to declare

        """
        self.LOGGER.debug('Declaring exchange %s', exchange_name)
        self._channel.exchange_declare(exchange=exchange_name,
                                       exchange_type=self.exchange_type,
                                       callback=self.on_exchange_declareok)

    def on_exchange_declareok(self, _unused_frame,):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
        command.

        :param pika.Frame.Method _unused_frame: Exchange.DeclareOk response frame

        """
        self.LOGGER.debug('Exchange declared')
        self.setup_reply_queue()
    
    def setup_reply_queue(self):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC
        command. When it is complete, the on_queue_declareok method will
        be invoked by pika.

        :param str|unicode queue_name: The name of the queue to declare.

        """
        self.LOGGER.debug('Declaring reply queue')
        self._channel.queue_declare(queue='',
                                    callback=self.on_queue_declareok,
                                    exclusive=True,
                                    auto_delete=True)

    def on_queue_declareok(self, method_frame):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.

        :param pika.frame.Method method_frame: The Queue.DeclareOk frame

        """
        self.reply_queue_name = method_frame.method.queue
        self.LOGGER.debug('Reply queue declared with name %s',
                         self.reply_queue_name)
        self._channel.basic_consume(on_message_callback=self.on_reply_received,
                                    queue=self.reply_queue_name,
                                    auto_ack=True)
        self.start_publishing()        

    def start_publishing(self):
        """This method will enable delivery confirmations and schedule the
        first message to be sent to RabbitMQ

        """
        self.LOGGER.info('Issuing consumer related RPC commands')
        self.enable_delivery_confirmations()
        self.schedule_next_message()

    def enable_delivery_confirmations(self):
        """Send the Confirm.Select RPC method to RabbitMQ to enable delivery
        confirmations on the channel. The only way to turn this off is to close
        the channel and create a new one.

        When the message is confirmed from RabbitMQ, the
        on_delivery_confirmation method will be invoked passing in a Basic.Ack
        or Basic.Nack method from RabbitMQ that will indicate which messages it
        is confirming or rejecting.

        """
        self.LOGGER.debug('Issuing Confirm.Select RPC command')
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        """Invoked by pika when RabbitMQ responds to a Basic.Publish RPC
        command, passing in either a Basic.Ack or Basic.Nack frame with
        the delivery tag of the message that was published. The delivery tag
        is an integer counter indicating the message number that was sent
        on the channel via Basic.Publish. Here we're just doing house keeping
        to keep track of stats and remove message numbers that we expect
        a delivery confirmation of from the list used to keep track of messages
        that are pending confirmation.

        :param pika.frame.Method method_frame: Basic.Ack or Basic.Nack frame

        """
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        #self.LOGGER.debug(f'Received {confirmation_type} for delivery tag: {method_frame.method.delivery_tag}')
        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        #self.LOGGER.debug(f'Published {self._message_number} messages, {len(self._deliveries)} to be confirmed, {self._acked} were acked and {self._nacked} were nacked')

    def schedule_next_message(self):
        """If we are not closing our connection to RabbitMQ, schedule another
        message to be delivered in PUBLISH_INTERVAL seconds.

        """
        if self._stopping:
            return
        # LOGGER.debug(f'Scheduling next message for {self.HEARTBEAT_INTERVAL} seconds')
        self._connection.ioloop.call_later(self.HEARTBEAT_INTERVAL, self.publish_message)

    def publish_message(self):
        """If the class is not stopping, publish a message to RabbitMQ,
        appending a list of deliveries with the message number that was sent.
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

        message = {'heartbeat': self._message_number}

        self._corr_id = str(uuid.uuid4())

        properties = pika.BasicProperties(app_id=self.device_id,
                                          content_type='application/json',
                                          reply_to=self.reply_queue_name,
                                          correlation_id=self._corr_id)

        self._channel.basic_publish(exchange=self.exchange_name, 
                                    routing_key=self.routing_key,
                                    body=json.dumps(message, ensure_ascii=False),
                                    properties=properties)
        self._message_number += 1
        self._deliveries.append(self._message_number)
        #self.LOGGER.debug(f'Published heartbeat message # {self._message_number}')
        self.schedule_next_message()

        self._connection.ioloop.call_later(self.TIMEOUT, self.check_timeout)

    def on_reply_received(self, channel, method, header, body):
        if self._corr_id == header.correlation_id:
            self._response = True
            self._timeouts_missed = 0
            if not self.STATE == 'connected':
                self.STATE = 'connected'
                self.LOGGER.info('STATE connected')

    def check_timeout(self):
        if not self._response:
            self._timeouts_missed += 1
            self.LOGGER.debug('Heartbeat timeout')

        if self._timeouts_missed == self.MAX_MISSED_TIMEOUTS + 1:
            self.LOGGER.warn(f'More than {self.MAX_MISSED_TIMEOUTS} timeouts missed. STATE disconnected')
            self.STATE = 'disconnected'

    
def run_connection():
    """ run the device connection """
    device_connection = DeviceConnection() 

    try:
        device_connection.run()
    except KeyboardInterrupt:
        LOGGER.info("Stopping device connection")
        device_connection.stop()
