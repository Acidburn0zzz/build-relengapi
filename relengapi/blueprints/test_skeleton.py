# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from nose.tools import eq_
from relengapi.testing import TestContext

test_context = TestContext()
@test_context
def test_hello(client):
    rv = client.get('/skel')
    eq_(rv.status_code, 200)
    eq_(json.loads(rv.data), {'message': 'hello world'})
