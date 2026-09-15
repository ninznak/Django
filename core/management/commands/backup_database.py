"""Back up precisely the database Django uses, without shell parsing of .env."""
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from contextlib import closing

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def write_backup(config, destination):
    engine = config['ENGINE']
    if engine.endswith('sqlite3'):
        source = Path(config['NAME']).resolve()
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
    elif engine.endswith('postgresql'):
        env = os.environ.copy()
        for key, value in [('PGPASSWORD', config.get('PASSWORD')), ('PGHOST', config.get('HOST')),
                           ('PGPORT', config.get('PORT')), ('PGUSER', config.get('USER'))]:
            # Do not inherit unrelated connection credentials from the shell.
            env.pop(key, None)
            if value:
                env[key] = str(value)
        subprocess.run(['pg_dump', '--no-password', '--format=custom',
                        '--dbname', str(config['NAME']), '--file', str(destination)],
                       env=env, check=True, capture_output=True)
    else:
        raise CommandError('Unsupported database backend.')


class Command(BaseCommand):
    help = 'Consistent backup of settings.DATABASES[default], with private file permissions.'

    def add_arguments(self, parser):
        parser.add_argument('--directory', required=True)
        parser.add_argument('--keep', type=int, default=30)

    def handle(self, **options):
        if options['keep'] < 1:
            raise CommandError('--keep must be positive.')
        directory = Path(options['directory']).resolve()
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        config = settings.DATABASES['default']
        suffix = '.sqlite3' if config['ENGINE'].endswith('sqlite3') else '.dump'
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        output = directory / f'db-{stamp}{suffix}'
        fd, temporary = tempfile.mkstemp(prefix='.backup-', dir=directory)
        os.close(fd)
        try:
            write_backup(config, temporary)
            os.replace(temporary, output)
        except Exception as exc:
            Path(temporary).unlink(missing_ok=True)
            # Never echo connection strings/passwords or subprocess stderr.
            raise CommandError(f'Backup failed ({type(exc).__name__}); deployment must stop.') from None
        for old in sorted(directory.glob(f'db-*{suffix}'), key=lambda p: p.stat().st_mtime, reverse=True)[options['keep']:]:
            old.unlink()
        self.stdout.write(str(output))
