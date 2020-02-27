#!/usr/bin/python3
# -*- coding: utf-8 -*-
# (c) 2020 Matt Martz <matt@sivel.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import base64
import fnmatch
import json
import os
import re
import sys

import q
import yaml  # pyyaml

from collections import defaultdict

from github import Github  # pygithub

PLUGINS_RE = re.compile(r'lib/ansible/(plugins|modules|module_utils)/.*$') #  FIXME, add inventory *scripts* and tests?
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

assert GITHUB_TOKEN, "GITHUB_TOKEN env var must be set to an oauth token with repo:read from https://github.com/settings/"
g = Github(GITHUB_TOKEN)
migration = g.get_repo('ansible-community/collection_migration')
ansible = g.get_repo('ansible/ansible')

nwo = {}
botmeta_collections = {}

# Read in migration scenarios

for f in migration.get_contents('scenarios/nwo'):
    if f.path != "scenarios/nwo/community.yml":
        # Initially only look at community.yml, may need others?
        continue
    data = yaml.safe_load(base64.b64decode(f.content))
    namespace, ext = os.path.splitext(f.name)
    if ext != '.yml':
        continue
    for collection, content in data.items():
        if collection[0] == '_':
            continue
        name = '%s.%s' % (namespace, collection)
        for ptype, paths in content.items():
            for relpath in paths:
                if ptype in ('modules', 'module_utils'):
                    path = 'lib/ansible/%s/%s' % (ptype, relpath)
                else:
                    path = 'lib/ansible/plugins/%s/%s' % (ptype, relpath)
                nwo[path] = name

globs = [p for p in nwo if '*' in p]

# Read in botmeta from ansible/ansible


f = ansible.get_contents(".github/BOTMETA.yml")
botmeta = yaml.safe_load(base64.b64decode(f.content))
for key, contents in botmeta['files'].items():

    # Find which Schema contains this file
    match = None
    f = key.replace('$modules', 'lib/ansible/modules')
    f = f.replace('$module_utils', 'lib/ansible/module_utils')
    f = f.replace('$plugins', 'lib/ansible/plugins')
    #if f in nwo:
    if nwo.find(f):
        # Rewrite path
        # FIXME If community.general, keep module directory structure for modules only
        plugin = f.replace('lib/ansible/modules', 'plugins/modules')
        plugin = plugin.replace('lib/ansible/module_utils', 'plugins/module_utils')
        plugin = plugin.replace('lib/ansible/plugins', 'plugins')
        plugin = plugin.replace('test/integration/targets', 'tests/integration/targets')
        plugin = plugin.replace('test/units', 'tests/units')

        if not nwo[f] in botmeta_collections:
            botmeta_collections[nwo[f]] = {}

        botmeta_collections[nwo[f]][plugin] = contents
      # Remove support
      # Remove migrated_to
      # or do we do this once over the whole data structure?

    else:
        # FIXME Maybe a directory, or regexp?
        # If we expect BOTMETA to have migrated_to for each file, this may not happen for plugins
        # Though may still happen for plugins

        print ("Can't find " + f)
    #else:
        #q.q("'Couldn't find" + f)
        #sys.exit()


# FIXME Need to copy team_ macros across

# For each entry in botmeta
#   Given module_utils/postgres.py
#   Find in schema
#     # Known collection name
      # new_bot_meta{collection}{'files'}{$new_path} = $data

print (yaml.dump(botmeta_collections))

sys.exit()


moves = {}
for f in ansible.get_contents('changelogs/fragments'):
    for commit in ansible.get_commits(path=f.path):
        files = [p.filename for p in commit.files]
        plugins = [p for p in files if PLUGINS_RE.search(p)]
        if not plugins:
            continue

        match = None
        if plugins[0] in nwo:
            match = plugins[0]
        else:
            try:
                for glob in globs:
                    for plugin in plugins:
                        if fnmatch.fnmatch(glob, plugin):
                            match = glob
                            raise StopIteration()
            except StopIteration:
                pass

        if match:
            collection = nwo[match]
            print('%s' % f.path, file=sys.stderr)
            print(
                '    %s - %s' % (collection, match),
                file=sys.stderr
            )

            clog_data = yaml.safe_load(base64.b64decode(f.content))
            moves[f.path] = {
                'collection': collection,
                'changelog': clog_data,
            }

            break

print(file=sys.stderr)
print(json.dumps(moves, sort_keys=True, indent=4))
