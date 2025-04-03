#!/usr/env/bin python

import argparse
import json
import os
import pprint
import sys

import requests

DEPENDENT_REPOS = [
    # girder 3
    'girder/girder/branches/master',
    'girder/girder_worker/branches/master',
    'girder/girder_worker_utils/branches/master',
    'girder/large_image/branches/master',
    'girder/slicer_cli_web/branches/master',
    'DigitalSlideArchive/HistomicsUI/branches/master',
    'DigitalSlideArchive/import-tracker/branches/main',
    'DigitalSlideArchive/girder_assetstore/branches/main',

    # girder 5
    'girder/girder/branches/v4-integration',
    'girder/large_image/branches/girder-5',
    'DigitalSlideArchive/HistomicsUI/branches/girder-5',
    'DigitalSlideArchive/girder_assetstore/branches/girder-5',

    # both
    'girder/large_image_wheels/branches/gh-pages',
]


def get_recent_commits():
    results = {}
    for repo in DEPENDENT_REPOS:
        print(f'Checking {repo}')
        headers = {}
        if 'GITHUB_TOKEN' in os.environ:
            headers['Authorization'] = f'token {os.environ["GITHUB_TOKEN"]}'
        response = requests.get(f'https://api.github.com/repos/{repo}', headers=headers)
        response.raise_for_status()
        results[repo] = response.json()['commit']['sha']
    return results


def get_previous_commits(source):
    results = {}
    try:
        if source and source.startswith('https'):
            headers = {}
            if 'GITHUB_TOKEN' in os.environ:
                headers['Authorization'] = f'token {os.environ["GITHUB_TOKEN"]}'
            response = requests.get(source, headers=headers)
            response.raise_for_status()
            results = response.json()
        else:
            results = json.load(open(source))
    except Exception:
        pass
    return results


def trigger_pipeline():
    print('Updates found, triggering build pipeline...')
    url = 'https://circleci.com/api/v2/project/github/DigitalSlideArchive/digital_slide_archive/pipeline'  # noqa
    headers = {
        'Circle-Token': os.environ['CIRCLECI_TOKEN'],
        'Content-Type': 'application/json'
    }
    data = {'branch': 'master'}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check if updates have occurred in a set of public github '
        'repositories.')
    parser.add_argument(
        '--out', help='Destination to write a json file with current commit '
        'hashes.')
    parser.add_argument(
        '--last', help='Previous file or url containing json commits used to '
        'check if updates have occurred.  This is considered a url if it '
        'starts with https.  Any GITHUB_TOKEN will be added as authorization.')
    parser.add_argument(
        '--trigger', action='store_true', help='Trigger a workflow if the '
        'recent commits do not match the last commits or the last commits are '
        'unavailable')

    opts = parser.parse_args()
    commits = get_recent_commits()
    pprint.pprint(commits)
    if opts.out:
        json.dump(commits, open(opts.out, 'w'), indent=2)
    if opts.last:
        previous = get_previous_commits(opts.last)
        if previous == commits:
            print('No change')
        else:
            print('Changes')
    if opts.last and opts.trigger and previous != commits:
        trigger_pipeline()
    if opts.last and previous != commits:
        sys.exit(1)
