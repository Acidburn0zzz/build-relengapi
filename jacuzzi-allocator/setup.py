# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup, find_packages

setup(
    name='relengapi-jacuzzi-allocator',
    version='0.0',
    description='Jacuzzi Allocator API',
    author='Dustin J. Mitchell',
    author_email='dustin@mozilla.com',
    url='',
    install_requires=[
        "Flask",
        "relengapi",
    ],
    packages=find_packages(),
    include_package_data=True,
    namespace_packages=['relengapi', 'relengapi.blueprints'],
    entry_points={
        "relengapi_blueprints": [
            'jacuzzi-allocator = relengapi.blueprints.jacuzzi_allocator:bp',
        ],
    },
)
