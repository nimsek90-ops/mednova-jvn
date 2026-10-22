"""Protect the private Django schema; does not create roles or change passwords."""
import re
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Preview/apply private-schema privileges and backend-only RLS for PostgreSQL.'

    def add_arguments(self, parser):
        parser.add_argument('--runtime-role', required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('Requires PostgreSQL; no MySQL changes performed.')
        role = options['runtime_role']
        if not re.fullmatch(r'[a-z_][a-z0-9_]*', role):
            raise CommandError('Use a simple lowercase runtime role identifier.')
        q = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_schema()')
            schema = cursor.fetchone()[0]
            if schema in ('public','auth','storage','extensions') or schema != 'mednova':
                raise CommandError('This command protects only the private mednova schema.')
            cursor.execute('SELECT rolbypassrls,rolsuper FROM pg_roles WHERE rolname=%s',[role])
            found = cursor.fetchone()
            if not found or any(found):
                raise CommandError('Runtime role must exist and have neither superuser nor BYPASSRLS.')
            cursor.execute('SELECT tablename FROM pg_tables WHERE schemaname=%s ORDER BY tablename',[schema])
            tables = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated','service_role')")
            blocked = [r[0] for r in cursor.fetchall()]
        statements = [f'REVOKE ALL ON SCHEMA {q(schema)} FROM PUBLIC',
                      f'GRANT USAGE ON SCHEMA {q(schema)} TO {q(role)}']
        for principal in blocked:
            statements.extend([f'REVOKE ALL ON SCHEMA {q(schema)} FROM {q(principal)}',
                f'REVOKE ALL ON ALL TABLES IN SCHEMA {q(schema)} FROM {q(principal)}',
                f'REVOKE ALL ON ALL SEQUENCES IN SCHEMA {q(schema)} FROM {q(principal)}'])
        for table in tables:
            qualified = f'{q(schema)}.{q(table)}'
            statements.extend([f'REVOKE ALL ON {qualified} FROM PUBLIC',
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON {qualified} TO {q(role)}',
                f'ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY',
                f'ALTER TABLE {qualified} FORCE ROW LEVEL SECURITY',
                f'DROP POLICY IF EXISTS mednova_backend ON {qualified}',
                f'CREATE POLICY mednova_backend ON {qualified} TO {q(role)} USING (true) WITH CHECK (true)'])
        statements.append(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {q(schema)} TO {q(role)}')
        if not options['apply']:
            self.stdout.write('-- Preview only. Apply as the trusted schema owner after review.\n'+';\n'.join(statements)+';')
            return
        with transaction.atomic(), connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        self.stdout.write(f'Private schema protected: {len(tables)} tables. Backend-only RLS; no browser database grants.')
