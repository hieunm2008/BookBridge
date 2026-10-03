from io import StringIO
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import tempfile
from django.core.management import call_command, CommandError
from django.test import TransactionTestCase
from bridge.models import School


class BackupTests(TransactionTestCase):
    def test_backup_is_consistent_restorable_and_does_not_overwrite(self):
        School.objects.create(code='BACKUP', name='Trường sao lưu', province='A', locality='B', contact_name='GV')
        with tempfile.TemporaryDirectory(prefix='bookbridge-backup-test-') as directory:
            destination = Path(directory) / 'backup.sqlite3'
            call_command('backup_database', str(destination), stdout=StringIO())
            with closing(sqlite3.connect(destination)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(db.execute('SELECT code FROM bridge_school').fetchall(), [('BACKUP',)])
            School.objects.create(code='AFTER', name='Thêm sau backup', province='A', locality='B', contact_name='GV')
            with self.assertRaises(CommandError):
                call_command('backup_database', str(destination), stdout=StringIO())
            restored = Path(directory) / 'restored.sqlite3'
            shutil.copyfile(destination, restored)
            with closing(sqlite3.connect(restored)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(db.execute('SELECT code FROM bridge_school').fetchall(), [('BACKUP',)])
            self.assertEqual(School.objects.count(), 2)
