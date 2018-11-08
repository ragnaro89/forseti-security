# Copyright 2017 The Forseti Security Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Notifier gRPC service. """

from Queue import Queue

from google.cloud.forseti.notifier import notifier
from google.cloud.forseti.services.notifier import notifier_pb2
from google.cloud.forseti.services.notifier import notifier_pb2_grpc
from google.cloud.forseti.common.util import logger

LOGGER = logger.get_logger(__name__)


class GrpcNotifier(notifier_pb2_grpc.NotifierServicer):
    """Notifier gRPC implementation."""

    HANDLE_KEY = 'handle'

    def _get_handle(self, context):
        """Return the handle associated with the gRPC call.

        Args:
            context (object): Context of the request.

        Returns:
            str: The model handle.
        """

        metadata = context.invocation_metadata()
        metadata_dict = {}
        for key, value in metadata:
            metadata_dict[key] = value
        return metadata_dict[self.HANDLE_KEY]

    def __init__(self, notifier_api, service_config, tracer=None):
        """Init.

        Args:
            notifier_api (Notifier): Notifier api implementation.
            service_config (ServiceConfig): Forseti 2.0 service configs.
        """
        super(GrpcNotifier, self).__init__()
        self.notifier = notifier_api
        self.service_config = service_config
        self.tracer = tracer

    def Ping(self, request, _):
        """Provides the capability to check for service availability.

        Args:
            request (PingRequest): The ping request.
            _ (object): Context of the request.

        Returns:
            PingReply: The response to the ping request.
        """

        return notifier_pb2.PingReply(data=request.data)

    @tracing.trace(lambda x: x.tracer)
    def Run(self, request, _):
        """Run notifier.

        Args:
            request (RunRequest): The run request.
            _ (object): Context of the request.

        Yields:
            Progress: The progress of the notifier.
        """
        progress_queue = Queue()

        LOGGER.info('Run notifier service with inventory index id: %s',
                    request.inventory_index_id)
        self.service_config.run_in_background(
            lambda: self._run_notifier(request.inventory_index_id,
                                       progress_queue))

        for progress_message in iter(progress_queue.get, None):
            yield notifier_pb2.Progress(server_message=progress_message)

    @tracing.trace(lambda x: x.tracer)
    def _run_notifier(self, inventory_index_id, progress_queue):
        """Run notifier.

        Args:
            inventory_index_id (int64): Inventory index id.
            progress_queue (Queue): Progress queue.
        """
        try:
            self.notifier.run(
                inventory_index_id,
                progress_queue,
                self.service_config)
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.exception(e)
            progress_queue.put('Error occurred during the '
                               'notification process.')
            progress_queue.put(None)


class GrpcNotifierFactory(object):
    """Factory class for Notifier service gRPC interface"""

    def __init__(self, config):
        """Init.

        Args:
            config (ServiceConfig): The service config.
        """
        self.config = config

    def create_and_register_service(self, server):
        """Create and register the Notifier service.

        Args:
            server (object): The server object.

        Returns:
             object: The service object.
        """
        service = GrpcNotifier(notifier_api=notifier,
                               service_config=self.config)
        notifier_pb2_grpc.add_NotifierServicer_to_server(service, server)
        LOGGER.info('Service %s created and registered', service)
        return service
