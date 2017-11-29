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
"""Unit Tests: Importer for IAM Explain."""

import os
import tempfile
import unittest
from tests.services.utils.gcp_env import gcp_configured
from tests.services.utils.gcp_env import gcp_env
from tests.services.utils.protect import copy_file_decrypt
from tests.unittest_utils import ForsetiTestCase
from google.cloud.forseti.services.dao import create_engine
from google.cloud.forseti.services.dao import ModelManager
from google.cloud.forseti.services.inventory.storage import InventoryState
from google.cloud.forseti.services.model.importer import importer


class ServiceConfig(object):
    """Helper class to implement dependency injection to IAM Explain services.
    """

    def __init__(self, db_connect_string):
        engine = create_engine(db_connect_string, echo=False)
        self.model_manager = ModelManager(engine)

    def run_in_background(self, function):
        """Runs a function in a thread pool in the background."""
        return function()


def get_db_file_path(db_name):
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, 'test_data', db_name)


def get_api_file_path(filename, passphrase):
    """Return the decrypted API recording."""
    fd, dstfilename = tempfile.mkstemp()
    try:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        encrypted_filename = os.path.join(module_dir, 'test_data', filename)
        return copy_file_decrypt(dstfilename, encrypted_filename, passphrase)
    finally:
        os.close(fd)


class ImporterTest(ForsetiTestCase):
    """Test importer based on database dump."""

    @unittest.skipUnless(gcp_configured(), "Don't replay when recordings run")
    def test_inventory_importer_basic(self):
        """Test the basic importer for the inventory."""

        env = gcp_env()
        db_connect = 'sqlite:///{}'.format(
            get_api_file_path('inventory_1_basic.db.encrypted',
                              env.passphrase))

        self.service_config = ServiceConfig(db_connect)

        self.source = 'INVENTORY'
        self.model_manager = self.service_config.model_manager
        self.model_name = self.model_manager.create(name=self.source)

        scoped_session, data_access = self.model_manager.get(self.model_name)
        with scoped_session as session:

            importer_cls = importer.by_source(self.source)
            import_runner = importer_cls(
                session,
                self.model_manager.model(self.model_name,
                                         expunge=False,
                                         session=session),
                data_access,
                self.service_config,
                inventory_id=1)
            import_runner.run()

        model = self.model_manager.model(self.model_name)
        self.assertIn(model.state,
                      [InventoryState.SUCCESS, InventoryState.PARTIAL_SUCCESS],
                      'Model state should be success or partial success')


if __name__ == '__main__':
    unittest.main()