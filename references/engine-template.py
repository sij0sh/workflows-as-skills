#!/usr/bin/env python3
"""Mechanics example, not mandatory phases: verify a file's word count.
Replace task checks/transitions, not a generic workflow specification. No loop.
Python 3.11+, POSIX. Single JSON state; ticketed results; fail-closed resume.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import uuid


def require(ok, message):
    if not ok:
        raise ValueError(message)


def safe(path):
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink refused')
    return path


def snapshot(root, source):
    path = safe(Path(os.path.abspath(root / source)))
    require(path.is_relative_to(root) and path.is_file(), 'source must be project-local')
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw.decode('utf-8').split())


def write(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load(raw):
    def pairs(entries):
        value = {}
        for key, item in entries:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--source', type=Path, help='start only; local text file')
    parser.add_argument('--done', help='current ticket; JSON {"words": integer} on stdin')
    args = parser.parse_args()
    root = args.root.resolve()
    path = safe(root / '.agents/exampleflow.json')
    if not path.exists() and args.source is None:
        require(args.done is None, 'no active state')
        print('Start with --source FILE')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with safe(path.with_suffix('.lock')).open('a') as lock:
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                require(time.monotonic() < deadline, 'lock timeout')
                time.sleep(.05)
        require(not (args.source and args.done), 'start and done are exclusive')
        if not path.exists():
            source = Path(os.path.abspath(root / args.source))
            digest, _ = snapshot(root, source)
            state = dict(version=1, root=str(root), ticket=uuid.uuid4().hex,
                         phase='measure', source=str(source), digest=digest)
            write(path, state)
        else:
            require(args.source is None, 'state already exists; resume without --source')
            state = load(path.read_bytes())
        require(isinstance(state, dict) and set(state) ==
                {'version', 'root', 'ticket', 'phase', 'source', 'digest'}, 'invalid state')
        require(type(state['version']) is int and state['version'] == 1 and
                state['root'] == str(root) and state['phase'] in ('measure', 'complete') and
                all(isinstance(state[k], str) for k in ('ticket', 'source', 'digest')),
                'unsupported/corrupt state')
        require(re.fullmatch(r'[0-9a-f]{32}', state['ticket']) and
                re.fullmatch(r'[0-9a-f]{64}', state['digest']), 'invalid ticket/digest')
        if args.done:
            require(args.done == state['ticket'], 'stale ticket')
            if state['phase'] != 'complete':
                raw = sys.stdin.buffer.read(4097)
                require(len(raw) <= 4096, 'result too large')
                result = load(raw)
                digest, words = snapshot(root, state['source'])
                require(digest == state['digest'], 'source changed; do not certify stale input')
                require(isinstance(result, dict) and set(result) == {'words'} and
                        type(result['words']) is int and result['words'] == words, 'wrong count')
                state['phase'] = 'complete'
                write(path, state)
        print(json.dumps(state))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
        sys.exit(f'ERROR: {error}')
