# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup, find_packages

setup(
    name='relengapi-docs',
    version='0.1.4',
    description='Documentation blueprint for relengapi',
    author='Dustin J. Mitchell',
    author_email='dustin@mozilla.com',
    url='',
    install_requires=[
        "Flask",
        "relengapi",
        "Sphinx",
    ],
    extras_require = {
        'test': [
            'nose',
            'mock'
        ]
    },
    packages=find_packages(),
    package_data={  # NOTE: these files must *also* be specified in MANIFEST.in
        'relengapi.blueprints.docs': [
            'src/*/*.rst',
            'src/conf.py',
            'templates/*.html',
        ],
    },
    zip_safe=False,
    include_package_data=True,
    namespace_packages=['relengapi', 'relengapi.blueprints'],
    entry_points={
        "relengapi_blueprints": [
            'docs = relengapi.blueprints.docs:bp',
        ],
    },
    license='MPL2',
)
