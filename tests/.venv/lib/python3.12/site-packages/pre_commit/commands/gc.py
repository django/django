from __future__ import annotations

import os.path
from typing import Any

import pre_commit.constants as C
from pre_commit import output
from pre_commit.clientlib import InvalidConfigError
from pre_commit.clientlib import InvalidManifestError
from pre_commit.clientlib import load_config
from pre_commit.clientlib import load_manifest
from pre_commit.clientlib import LOCAL
from pre_commit.clientlib import META
from pre_commit.store import Store
from pre_commit.util import rmtree


def _mark_used_repos(
        store: Store,
        all_repos: dict[tuple[str, str], str],
        unused_repos: set[tuple[str, str]],
        repo: dict[str, Any],
) -> None:
    if repo['repo'] == META:
        return
    elif repo['repo'] == LOCAL:
        for hook in repo['hooks']:
            deps = hook.get('additional_dependencies')
            unused_repos.discard((
                store.db_repo_name(repo['repo'], deps),
                C.LOCAL_REPO_VERSION,
            ))
    else:
        key = (repo['repo'], repo['rev'])
        path = all_repos.get(key)
        # can't inspect manifest if it isn't cloned
        if path is None:
            return

        try:
            manifest = load_manifest(os.path.join(path, C.MANIFEST_FILE))
        except InvalidManifestError:
            return
        else:
            unused_repos.discard(key)
            by_id = {hook['id']: hook for hook in manifest}

        for hook in repo['hooks']:
            if hook['id'] not in by_id:
                continue

            deps = hook.get(
                'additional_dependencies',
                by_id[hook['id']]['additional_dependencies'],
            )
            unused_repos.discard((
                store.db_repo_name(repo['repo'], deps), repo['rev'],
            ))


def _gc(store: Store) -> int:
    with store.exclusive_lock(), store.connect() as db:
        store._create_configs_table(db)

        repos = db.execute('SELECT repo, ref, path FROM repos').fetchall()
        all_repos = {(repo, ref): path for repo, ref, path in repos}
        unused_repos = set(all_repos)

        configs_rows = db.execute('SELECT path FROM configs').fetchall()
        configs = [path for path, in configs_rows]

        dead_configs = []
        for config_path in configs:
            try:
                config = load_config(config_path)
            except InvalidConfigError:
                dead_configs.append(config_path)
                continue
            else:
                for repo in config['repos']:
                    _mark_used_repos(store, all_repos, unused_repos, repo)

        paths = [(path,) for path in dead_configs]
        db.executemany('DELETE FROM configs WHERE path = ?', paths)

        db.executemany(
            'DELETE FROM repos WHERE repo = ? and ref = ?',
            sorted(unused_repos),
        )
        for k in unused_repos:
            rmtree(all_repos[k])

        return len(unused_repos)


def gc(store: Store) -> int:
    output.write_line(f'{_gc(store)} repo(s) removed.')
    return 0
