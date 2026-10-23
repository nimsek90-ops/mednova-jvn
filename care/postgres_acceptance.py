"""Explicit PostgreSQL transaction tests; never silently run on SQLite."""
from django.db import connection
from . import mysql_acceptance
from . import tests as fixtures


class PostgreSQLBookingAcceptance(mysql_acceptance.MySQLBookingAcceptance):
    def setUp(self):
        if connection.vendor != 'postgresql':
            self.fail('This acceptance suite requires an isolated PostgreSQL test database.')
        fixtures.Workflows.setUpTestData()
