"""Cross-platform setup, launcher, tests and diagnostics. Standard library only."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / '.venv'
PYTHON = VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
SUPPORTED = {(3, 12), (3, 13)}


def execute(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], cwd=ROOT, **kwargs)


def check_python():
    if sys.version_info[:2] not in SUPPORTED:
        raise RuntimeError('Use Python 3.12 or 3.13. Install it from python.org, then run setup again.')


def environment():
    check_python()
    if not PYTHON.exists():
        print('Creating a project-local .venv...', flush=True)
        execute([sys.executable, '-m', 'venv', VENV], check=True)
    version = execute([PYTHON, '-c', 'import sys; print(str(sys.version_info.major)+"."+str(sys.version_info.minor))'], capture_output=True, text=True, check=True).stdout.strip()
    if version not in {'3.12', '3.13'}:
        raise RuntimeError('This .venv uses an unsupported Python version. Rename it and run setup with Python 3.12 or 3.13.')


def ready():
    if not PYTHON.exists():
        return False
    code = 'from importlib.metadata import version; import pathlib; req=pathlib.Path("requirements-dev.txt").read_text(); base=pathlib.Path("requirements.txt").read_text(); pairs=[x.strip().split("==") for x in (base+"\\n"+req).splitlines() if "==" in x and not x.lstrip().startswith("#")]; assert all(version(n)==v for n,v in pairs)'
    return execute([PYTHON, '-c', code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def setup():
    environment()
    if ready():
        print('The project environment is already ready.', flush=True)
        return
    print('Installing pinned dependencies. Internet is needed for this first setup.', flush=True)
    execute([PYTHON, '-m', 'pip', 'install', '-r', 'requirements-dev.txt'], check=True)
    if not ready():
        raise RuntimeError('Dependency validation failed. Run DIAGNOSE_FYNTRA.cmd for details.')
    print('Setup complete. The fictional demo needs no credentials.', flush=True)


def diagnose():
    # Deliberately avoid reading financial files, tokens, or credential values.
    expected = {}
    for name in ('requirements.txt', 'requirements-dev.txt'):
        for line in (ROOT / name).read_text(encoding='utf-8-sig').splitlines():
            if '==' in line and not line.lstrip().startswith('#'):
                package, version = line.strip().split('==', 1)
                expected[package] = version
    checks = []
    checks.append(('Python 3.12 or 3.13', sys.version_info[:2] in SUPPORTED, platform.python_version()))
    for package, wanted in expected.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            actual = 'not installed'
        checks.append((package, actual == wanted, f'{actual}; expected {wanted}'))
    for name in ('app.py', 'database.py', 'analytics.py', 'assets/mark.svg', '.streamlit/config.toml'):
        checks.append((name, (ROOT / name).is_file(), 'required source file'))
    try:
        compile((ROOT / 'app.py').read_text(encoding='utf-8-sig'), 'app.py', 'exec')
        checks.append(('Entrypoint syntax', True, 'valid'))
    except (SyntaxError, OSError) as exc:
        checks.append(('Entrypoint syntax', False, type(exc).__name__))
    try:
        import sqlite3
        with sqlite3.connect(':memory:') as connection:
            connection.execute('CREATE TABLE check_database(value INTEGER)')
            connection.execute('INSERT INTO check_database VALUES (?)', (125,))
            assert connection.execute('SELECT value FROM check_database').fetchone()[0] == 125
        checks.append(('SQLite', True, sqlite3.sqlite_version))
    except Exception as exc:
        checks.append(('SQLite', False, type(exc).__name__))
    lines = ['FYNTRA local diagnostic report', f'OS: {platform.system()} {platform.release()}', f'Python: {platform.python_version()}', '']
    lines.extend(f'{"PASS" if ok else "FAIL"} | {name} | {detail}' for name, ok, detail in checks)
    lines += ['', 'Private cloud configuration file: '+('present (contents not read)' if (ROOT / '.streamlit/secrets.toml').exists() else 'absent (demo works without it)'),
              'No financial records, environment values, passwords or tokens are included.',
              'For missing dependencies: python tools/manage.py setup',
              'For behavior tests: python tools/manage.py test']
    report = '\n'.join(lines)+'\n'
    logs = ROOT / 'logs'
    logs.mkdir(exist_ok=True)
    (logs / 'diagnostics.txt').write_text(report, encoding='utf-8')
    print(report)
    print('Saved: logs/diagnostics.txt')
    return 0 if all(ok for _, ok, _ in checks) else 1


def main():
    parser = argparse.ArgumentParser(description='Set up, run, test or diagnose FYNTRA.')
    parser.add_argument('action', nargs='?', default='run', choices=['setup', 'run', 'test', 'doctor'])
    parser.add_argument('--port', type=int, default=8501)
    parser.add_argument('--no-browser', action='store_true', help='Do not open a browser automatically.')
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.action == 'doctor':
        if PYTHON.exists() and Path(sys.executable).resolve() != PYTHON.resolve():
            return execute([PYTHON, __file__, 'doctor']).returncode
        return diagnose()
    setup()
    if args.action == 'setup':
        return 0
    if args.action == 'test':
        env = os.environ.copy()
        env['FYNTRA_TESTING'] = '1'
        return execute([PYTHON, '-m', 'pytest', '-q'], env=env).returncode
    if not 1024 <= args.port <= 65535:
        raise RuntimeError('Choose a port between 1024 and 65535.')
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', args.port))
        except OSError as exc:
            raise RuntimeError(f'Port {args.port} is busy or unavailable. Try: python tools/manage.py run --port {args.port+1}') from exc
    print(f'Open http://localhost:{args.port} in your browser. Press Ctrl+C here to stop.', flush=True)
    return execute([PYTHON, '-m', 'streamlit', 'run', 'app.py', '--server.address', '127.0.0.1', '--server.port', str(args.port), '--server.headless', 'true' if args.no_browser else 'false']).returncode


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nFYNTRA stopped.')
        raise SystemExit(0)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f'\nFYNTRA: {error}\nSee START_HERE.md or run DIAGNOSE_FYNTRA.cmd.', file=sys.stderr)
        raise SystemExit(1)
