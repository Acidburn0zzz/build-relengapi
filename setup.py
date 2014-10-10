# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup, find_packages

data_patterns = [
    'templates/**.html',
    'static/**.jpg',
    'static/**.css',
    'static/**.js',
    'static/**.txt',
]

setup(
    name='relengapi-clobberer',
    version='0.0',
    description='Clobberer blueprint for relengapi',
    author='Morgan Phillips',
    author_email='mphillips@mozilla.com',
    url='',
    install_requires=[
        "Flask",
        "relengapi",
    ],
    extras_require={
        'test': [
            'nose',
            'mock'
        ]
    },
    packages=find_packages(),
    package_data={  # NOTE: these files must *also* be specified in MANIFEST.in
        'relengapi.blueprints.clobberer': data_patterns + [
            'docs/**.rst'
        ],
    },
    include_package_data=True,
    namespace_packages=['relengapi', 'relengapi.blueprints'],
    entry_points={
        "relengapi.blueprints": [
            'clobberer = relengapi.blueprints.clobberer:bp',
        ],
    },
    license='MPL2',
)
