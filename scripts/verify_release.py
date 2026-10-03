"""Inspect the current database and release artifacts; write no business data."""
import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookbridge.settings')
import django
django.setup()
from django.core.management.utils import get_random_secret_key
from bridge.models import Audit, Book, Inventory, Loan, Need, Profile, Proposal, ProposalLine, School


def main():
    required = ['README.md', 'requirements.txt', 'manage.py', 'serve.py', '.env.example',
                'docs/WEBUI.md', 'docs/wireframes.html', 'docs/DEPLOYMENT.md', 'docs/VERIFICATION.md',
                'bridge/migrations/0001_initial.py', 'bridge/migrations/0002_alter_proposal_options_alter_proposalline_options.py',
                'bridge/management/commands/seed_demo.py', 'bridge/management/commands/backup_database.py',
                'deploy/nginx.conf.example', 'static/bridge.css', 'static/bridge.js']
    for relative in required:
        assert (ROOT / relative).is_file(), relative
    for cls in [School, Book, Profile, Inventory, Need, Proposal, ProposalLine, Loan, Audit]:
        for obj in cls.objects.all():
            obj.full_clean()
    loans = list(Loan.objects.select_related('inventory', 'need'))
    for inv in Inventory.objects.all():
        items = [l for l in loans if l.inventory_id == inv.pk]
        assert inv.reserved == sum(l.quantity for l in items if l.status in ['pending', 'ready']), f'Inventory {inv.pk} reserved'
        assert inv.lent == sum(l.quantity for l in items if l.status in ['sent', 'borrowed', 'returning']), f'Inventory {inv.pk} lent'
        assert inv.available >= 0
    for need in Need.objects.all():
        items = [l for l in loans if l.need_id == need.pk]
        assert need.committed == sum(l.quantity for l in items if l.status in ['pending', 'ready', 'sent']), f'Need {need.pk} committed'
        assert need.received == sum(l.quantity for l in items if l.status in ['borrowed', 'returning', 'completed']), f'Need {need.pk} received'
    for loan in loans:
        assert loan.inventory.book_id == loan.need.book_id
        assert loan.inventory.school_id != loan.need.school_id
        if loan.status in ['ready', 'sent', 'borrowed', 'returning', 'completed']:
            assert loan.lender_confirmed and loan.borrower_confirmed
        assert loan.events.exists()
    backup = ROOT / 'artifacts/verified-backup.sqlite3'
    with closing(sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        backup_counts = {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ['bridge_school', 'bridge_inventory', 'bridge_need', 'bridge_loan']}
    env = dict(os.environ, BOOKBRIDGE_DEBUG='0', BOOKBRIDGE_SECRET_KEY=get_random_secret_key(),
               BOOKBRIDGE_ALLOWED_HOSTS='bookbridge.example.org', BOOKBRIDGE_CSRF_ORIGINS='https://bookbridge.example.org')
    deployment = subprocess.run([sys.executable, str(ROOT / 'manage.py'), 'check', '--deploy'], env=env, cwd=ROOT,
                                capture_output=True, text=True, encoding='utf-8')
    assert deployment.returncode == 0, deployment.stdout + deployment.stderr
    assert 'no issues' in deployment.stdout, deployment.stdout + deployment.stderr
    matrix = json.loads((ROOT / 'artifacts/responsive-coordinator.json').read_text(encoding='utf-8'))
    roles = json.loads((ROOT / 'artifacts/responsive-roles.json').read_text(encoding='utf-8'))
    assert len(matrix) == 36 and {x['width'] for x in matrix} == {375, 768, 1024, 1440}
    assert len(roles) == 72 and {x['username'] for x in roles} == {'giaovien1', 'giaovien2', 'giaovien3', 'giaovien4', 'giaovien5', 'admin'}
    public = json.loads((ROOT / 'artifacts/responsive-public.json').read_text(encoding='utf-8'))
    assert len(public) == 8 and {x['width'] for x in public} == {375, 768, 1024, 1440}
    assert all(r['scrollWidth'] <= r['clientWidth'] and not r.get('error') for r in matrix + roles + public)
    contrast = json.loads((ROOT / 'artifacts/contrast.json').read_text(encoding='utf-8'))
    assert contrast['failures'] == []
    report = {
        'required_artifacts': required, 'model_validation': 'passed', 'ledger_conservation': 'passed',
        'counts': {cls.__name__: cls.objects.count() for cls in [School, Book, Inventory, Need, Loan, Audit]},
        'loan8': {'status': Loan.objects.get(pk=8).status, 'events': list(Audit.objects.filter(loan_id=8).values_list('action', 'actor__username'))},
        'loan9': {'status': Loan.objects.get(pk=9).status},
        'math_inventory': dict(Inventory.objects.filter(school__code='DEMO-01', book__title='Toán 3', book__year=2025).values('owned', 'internal', 'reserved', 'lent').get()),
        'backup_integrity': 'ok', 'backup_counts': backup_counts,
        'production_check': deployment.stdout.strip(), 'responsive_checks': len(matrix) + len(roles) + len(public),
        'contrast_failures': contrast['failures'],
    }
    assert report['loan8']['status'] == 'completed' and report['loan9']['status'] == 'cancelled'
    assert report['math_inventory'] == {'owned': 50, 'internal': 30, 'reserved': 0, 'lent': 0}
    (ROOT / 'artifacts/release-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()
