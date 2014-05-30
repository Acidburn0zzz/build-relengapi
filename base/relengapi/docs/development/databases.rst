Using Databases
===============

Releng API uses `SQLAlchemy Core <http://sqlalchemy.org/>`_ to access databases.
Releng API does not use the SQLAlchemy ORM.

The system supports multiple, independent databases, each identified by a short name.
Of course, it's impossible to perform joins between independent databases.
The base defines one, ``relengapi``, that should serve as the default location for new tables.
Blueprints can define other databases, or add tables to existing databases.

The same database access object is available at ``current_app.db`` and ``g.db``; callers can use whichever is easier.

Users configure the SQLAlchemy database URIs using the ``SQLALCHEMY_DATABASE_URIS`` configuration parameter, which is a dictionary mapping database names to URLs.

Adding Tables
-------------

RelengAPI supports SQLAlchemy's declarative mapping syntax, with a small twist to support multiple databases:
instead of calling ``sqlalchemy.ext.declarative.declarative_base()`` to get a base class, call ``relengapi.db.declarative_base(dbname)``.

For example::

    from relengapi import db

    class User(db.declarative_base('relengapi')):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String(100))
        password = Column(String(100))

Many-to-Many Relationships
--------------------------

The `SQLAlchemy Documentation <http://docs.sqlalchemy.org/en/rel_0_9/orm/relationships.html#many-to-many>`_ describes most of the details of setting up many-to-many relationships.
In RelengAPI, the metadata for the association table needs to be fetched from the declarative base:

.. code-block:: none

    allocations = Table(
        'allocations', db.declarative_base('jacuzzi_allocator').metadata,
        ...
    )

The linked tables are defined as described above.


Using Tables
------------

Use of the ORM layer requires a session.
The session is available from ``g.db.session(dbname)``, given the database name.
For example::

    @bp.route('/add/foo')
    def add_foo():
        session = g.db.session('relengapi')

        u = User()
        u.name = 'Foo'
        u.password = 'sekrit'
        session.add(u)
        session.commit()

        return 'ok'

As you might expect, bad things will happen if you try to use tables from one database with a session for another database.

As a shortcut, each table object has a ``query`` property which is automatically bound to the table and session; this is similar to the property provided by Flask-SQLAlchemy::

    @bp.route('/get/foo')
    def get_foo():
        u = User.query.filter_by(name='Foo').first()
        return jsonify(userid=u.id)

Engines, MetaData, etc.
-----------------------

Although most uses of the database should occur by the ORM methods described above, some operations require more data.

The engine for a database is available from the ``current_app.db.engine(dbname)`` method::

    eng = current_app.db.engine('relengapi')

The list of database names is at ``current_app.db.database_names``.

The known metadata for each database is in ``current_app.db.metadata``, keyed by database name.

Alternative Column types
------------------------

Relengapi provides some custom Column types that can be used in SQL Models.

These can be used like any other column in SQLAlchemy ORMs::

    from relengapi.db import SomeColumn
    class Widget(db.declarative_base('...')):
        someField = sa.Column(SomeColumn, ...)

UTCDateTime Column
..................

A DateTime column where values are always stored and retrieved in UTC. Specifically
the datetime objects returned are always timezone aware (with pytz.UTC set). On
inserts into the table it automatically converts the object to UTC when a timezone
aware datetime object is passed in.

example::

    from relengapi import db
    import sqlalchemy as sa
    
    class Log(db.declarative_base('...')):
        __tablename__ = 'logs'
        id = sa.Column(sa.Integer, primary_key=True)
        dt = sa.Column(db.UTCDateTime,
                       default=datetime.datetime.utcnow,
                       nullable=False)
        msg = sa.Column(sa.String(255), nullable=False)
