"""Schema metadata without Django's MySQL SELECT * LIMIT 1 sampler."""
from django.db import connection


def metadata_constraints(cursor, table):
    if connection.vendor != 'mysql':
        # PostgreSQL uses pg_catalog; SQLite uses PRAGMA/sqlite_master only.
        return connection.introspection.get_constraints(cursor, table)
    database = connection.settings_dict['NAME']
    result = {}
    cursor.execute('''
        SELECT tc.CONSTRAINT_NAME,tc.CONSTRAINT_TYPE,k.COLUMN_NAME,
               k.REFERENCED_TABLE_NAME,k.REFERENCED_COLUMN_NAME
        FROM information_schema.TABLE_CONSTRAINTS tc
        LEFT JOIN information_schema.KEY_COLUMN_USAGE k
          ON tc.CONSTRAINT_SCHEMA=k.CONSTRAINT_SCHEMA
         AND tc.TABLE_NAME=k.TABLE_NAME AND tc.CONSTRAINT_NAME=k.CONSTRAINT_NAME
        WHERE tc.CONSTRAINT_SCHEMA=%s AND tc.TABLE_NAME=%s
        ORDER BY tc.CONSTRAINT_NAME,k.ORDINAL_POSITION
    ''', [database, table])
    for name, kind, column, parent, parent_column in cursor.fetchall():
        item = result.setdefault(name, {'columns': [], 'primary_key': kind=='PRIMARY KEY',
            'unique': kind in ('PRIMARY KEY','UNIQUE'), 'index': False,
            'check': kind=='CHECK', 'foreign_key': None})
        if column and column not in item['columns']:
            item['columns'].append(column)
        if parent:
            item['foreign_key'] = (parent, parent_column)
    cursor.execute('''
        SELECT INDEX_NAME,NON_UNIQUE,COLUMN_NAME,COLLATION,INDEX_TYPE,EXPRESSION
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
        ORDER BY INDEX_NAME,SEQ_IN_INDEX
    ''', [database, table])
    indexes = {}
    for name, non_unique, column, order, kind, expression in cursor.fetchall():
        index = indexes.setdefault(name, {'columns': [], 'orders': [], 'index_type': kind})
        index['columns'].append(column or expression or '(expression)')
        index['orders'].append('DESC' if order=='D' else 'ASC')
        item = result.setdefault(name, {'columns': [], 'primary_key': name=='PRIMARY',
            'unique': not non_unique, 'index': True, 'check': False, 'foreign_key': None})
        item.update(index=True, unique=not non_unique, type='idx')
    for name, index in indexes.items():
        result[name].update(index)
    return result
