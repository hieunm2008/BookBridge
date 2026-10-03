from pathlib import Path
from contextlib import closing
import sqlite3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Tạo bản sao nhất quán bằng SQLite backup API, không ghi đè file hiện có.'

    def add_arguments(self, parser):
        parser.add_argument('destination', help='Đường dẫn file sao lưu mới')

    def handle(self, *args, **options):
        source = Path(settings.DATABASES['default']['NAME']).resolve()
        destination = Path(options['destination']).resolve()
        if destination.exists() or source == destination:
            raise CommandError('Đích đã tồn tại hoặc trùng database nguồn. Chọn file mới.')
        if not source.is_file():
            raise CommandError('Không tìm thấy database nguồn.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents accidental overwrites even when two backups race.
        with destination.open('xb'):
            pass
        # sqlite3's transaction context manager does not close file handles.
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dest:
                src.backup(dest)
                if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise CommandError('Kiểm tra tính toàn vẹn của bản sao thất bại.')
        self.stdout.write(self.style.SUCCESS(f'Đã sao lưu và kiểm tra tính toàn vẹn: {destination}'))
