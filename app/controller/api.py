#!/usr/bin/env python
#
# Copyright 2016 Feei. All Rights Reserved
#
# Author:   Feei <wufeifei@wufeifei.com>
# Homepage: https://github.com/wufeifei/cobra
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the file 'doc/COPYING' for copying permission
#
import time

from flask import request, jsonify
import ConfigParser
from app import web
from app import CobraTaskInfo
from app import CobraProjects
from app import db
from pickup import GitTools

# default api url
API_URL = '/api'

"""
https://github.com/wufeifei/cobra/wiki/API
"""


@web.route(API_URL + '/add', methods=['POST'])
def add_task():
    """ Add a new task api.
    post json to http://url/api/add_new_task
    example:
        {
            "key": "34b9a295d037d47eec3952e9dcdb6b2b",              // must, client key
            "target": "https://gitlab.com/username/project",        // must, gitlab address
            "branch": "master",                                     // must, the project branch
            "old_version": "old version here",                      // optional, if you choice diff scan mode, you should provide old version hash.
            "new_version": "new version here",                      // optional, if you choice diff scan mode, you should provide new version hash.
        }
    :return:
        The return value also in json format, usually is:
        {"code": 1001, "msg": "error reason or success."}
        code: 1004: Unknown error, if you see this error code, most time is cobra's database error.
        code: 1003: You support the parameters is not json.
        code: 1002: Some parameters is empty. More information in "msg".
        code: 1001: Success, no error.
    """
    result = {}
    data = request.json
    if not data or data == "":
        return jsonify(code=1003, msg=u'Only support json, please post json data.')

    # Params
    key = data.get('key')
    target = data.get('target')
    branch = data.get('branch')
    new_version = data.get('new_version')
    old_version = data.get('old_version')

    # Verify
    if not key or key == "":
        return jsonify(code=1002, msg=u'key can not be empty.')
    if not target or target == "":
        return jsonify(code=1002, msg=u'url can not be empty.')
    if not branch or branch == "":
        return jsonify(code=1002, msg=u'branch can not be empty.')

    # Parse
    current_time = time.strftime('%Y-%m-%d %X', time.localtime())
    config = ConfigParser.ConfigParser()
    config.read('config')
    username = config.get('git', 'username')
    password = config.get('git', 'password')

    gg = GitTools.Git(target, branch=branch, username=username, password=password)
    repo_author = gg.repo_author
    repo_name = gg.repo_name

    if new_version == "" or old_version == "":
        scan_way = 1
    else:
        scan_way = 2

    # Git Clone Error
    if gg.clone() is False:
        return jsonify(code=4001)

    # insert into task info table.
    task = CobraTaskInfo(target, branch, scan_way, new_version, old_version, None, None, None, 1, 0,
                         current_time, current_time)

    p = CobraProjects.query.filter_by(repository=target).first()
    project = None
    if not p:
        # insert into project table.
        project = CobraProjects(target, repo_name, repo_author, None, None, current_time, current_time)

    try:
        db.session.add(task)
        if not p:
            db.session.add(project)
        db.session.commit()
        return jsonify(code=1001, msg=u'task add success.')
    except:
        return jsonify(code=1004, msg=u'Unknown error, try again later?')


@web.route(API_URL + '/status', methods=['POST'])
def status_task():
    scan_id = request.json.get('scan_id')
    c = CobraTaskInfo.query.filter_by(id=scan_id)
    if not c:
        return jsonify(status=4004)
    status = {
        0: 'init',
        1: 'scanning',
        2: 'done',
        3: 'error'
    }
    status_text = status[c.status]
    result = {
        'status': status_text,
        'report': 'http://cobra.wufeifei.com/report/' + scan_id
    }
    return jsonify(status=1001, result=result)