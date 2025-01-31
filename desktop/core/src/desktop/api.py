#!/usr/bin/env python
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
import logging
import json
import time

from collections import defaultdict

from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from desktop.lib.i18n import force_unicode
from desktop.models import Document, DocumentTag


LOG = logging.getLogger(__name__)


def _get_docs(user):
  history_tag = DocumentTag.objects.get_history_tag(user)
  trash_tag = DocumentTag.objects.get_trash_tag(user)
  docs = itertools.chain(
      Document.objects.get_docs(user).exclude(tags__in=[trash_tag]).filter(tags__in=[history_tag]).select_related('DocumentTag', 'User', 'DocumentPermission').order_by('-last_modified')[:500],
      Document.objects.get_docs(user).exclude(tags__in=[history_tag]).select_related('DocumentTag', 'User', 'DocumentPermission').order_by('-last_modified')[:100]
  )
  return list(docs)


def massaged_tags_for_json(docs, user):
  """
    var TAGS_DEFAULTS = {
    'history': {'name': 'History', 'id': 1, 'docs': [1], 'type': 'history'},
    'trash': {'name': 'Trash', 'id': 3, 'docs': [2]},
    'mine': [{'name': 'default', 'id': 2, 'docs': [3]}, {'name': 'web', 'id': 3, 'docs': [3]}],
    'notmine': [{'name': 'example', 'id': 20, 'docs': [10]}, {'name': 'ex2', 'id': 30, 'docs': [10, 11]}]
  };
  """
  ts = {
    'trash': {},
    'history': {},
    'mine': [],
    'notmine': [],
  }
  sharers = defaultdict(list)

  trash_tag = DocumentTag.objects.get_trash_tag(user)
  history_tag = DocumentTag.objects.get_history_tag(user)

  tag_doc_mapping = defaultdict(set) # List of documents available in each tag
  for doc in docs:
    for tag in doc.tags.all():
      tag_doc_mapping[tag].add(doc)

  ts['trash'] = massaged_tags(trash_tag, tag_doc_mapping)
  ts['history'] = massaged_tags(history_tag, tag_doc_mapping)
  tags = list(set(tag_doc_mapping.keys() + [tag for tag in DocumentTag.objects.get_tags(user=user)])) # List of all personal and shared tags

  for tag in tags:
    massaged_tag = massaged_tags(tag, tag_doc_mapping)
    if tag == trash_tag:
      ts['trash'] = massaged_tag
    elif tag == history_tag:
      ts['history'] = massaged_tag
    elif tag.owner == user:
      ts['mine'].append(massaged_tag)
    else:
      sharers[tag.owner].append(massaged_tag)

  ts['notmine'] = [{'name': sharer.username, 'projects': projects} for sharer, projects in sharers.iteritems()]
  # Remove from my tags the trashed and history ones
  mine_filter = set(ts['trash']['docs'] + ts['history']['docs'])
  for tag in ts['mine']:
    tag['docs'] = [doc_id for doc_id in tag['docs'] if doc_id not in mine_filter]

  return ts

def massaged_tags(tag, tag_doc_mapping):
  return {
    'id': tag.id,
    'name': tag.tag,
    'owner': tag.owner.username,
    'docs': [doc.id for doc in tag_doc_mapping[tag]] # Could get with one request groupy
  }

def massaged_documents_for_json(documents, user):
  """
  var DOCUMENTS_DEFAULTS = {
    '1': {
      'id': 1,
      'name': 'my query history', 'description': '', 'url': '/beeswax/execute/design/83', 'icon': '/beeswax/static/art/icon_beeswax_24.png',
      'lastModified': '03/11/14 16:06:49', 'owner': 'admin', 'lastModifiedInMillis': 1394579209.0, 'isMine': true
    },
    '2': {
      'id': 2,
      'name': 'my query 2 trashed', 'description': '', 'url': '/beeswax/execute/design/83', 'icon': '/beeswax/static/art/icon_beeswax_24.png',
      'lastModified': '03/11/14 16:06:49', 'owner': 'admin', 'lastModifiedInMillis': 1394579209.0, 'isMine': true
     },
     '3': {
       'id': 3,
       'name': 'my query 3 tagged twice', 'description': '', 'url': '/beeswax/execute/design/83', 'icon': '/beeswax/static/art/icon_beeswax_24.png',
     'lastModified': '03/11/14 16:06:49', 'owner': 'admin', 'lastModifiedInMillis': 1394579209.0, 'isMine': true
     },
    '10': {
      'id': 10,
      'name': 'my query 3 shared', 'description': '', 'url': '/beeswax/execute/design/83', 'icon': '/beeswax/static/art/icon_beeswax_24.png',
      'lastModified': '03/11/14 16:06:49', 'owner': 'admin', 'lastModifiedInMillis': 1394579209.0, 'isMine': true
     },
    '11': {
      'id': 11,
      'name': 'my query 4 shared', 'description': '', 'url': '/beeswax/execute/design/83', 'icon': '/beeswax/static/art/icon_beeswax_24.png',
      'lastModified': '03/11/14 16:06:49', 'owner': 'admin', 'lastModifiedInMillis': 1394579209.0, 'isMine': true
     }
  };
  """
  docs = {}

  for document in documents:
    try:
      url = document.content_object.get_absolute_url()
    except:
      # If app of document is disabled
      url = ''
    read_perms = document.list_permissions(perm='read')
    write_perms = document.list_permissions(perm='write')
    docs[document.id] = {
      'id': document.id,
      'contentType': document.content_type.name,
      'icon': document.icon,
      'name': document.name,
      'url': url,
      'description': document.description,
      'tags': [{'id': tag.id, 'name': tag.tag} for tag in document.tags.all()],
      'perms': {
        'read': {
          'users': [{'id': perm_user.id, 'username': perm_user.username} for perm_user in read_perms.users.all()],
          'groups': [{'id': perm_group.id, 'name': perm_group.name} for perm_group in read_perms.groups.all()]
        },
        'write': {
          'users': [{'id': perm_user.id, 'username': perm_user.username} for perm_user in write_perms.users.all()],
          'groups': [{'id': perm_group.id, 'name': perm_group.name} for perm_group in write_perms.groups.all()]
        }
      },
      'owner': document.owner.username,
      'isMine': document.owner == user,
      'lastModified': document.last_modified.strftime("%x %X"),
      'lastModifiedInMillis': time.mktime(document.last_modified.timetuple())
   }

  return docs


def massage_doc_for_json(doc, user):
  read_perms = doc.list_permissions(perm='read')
  write_perms = doc.list_permissions(perm='write')
  return {
      'id': doc.id,
      'contentType': doc.content_type.name,
      'icon': doc.icon,
      'name': doc.name,
      'url': doc.content_object.get_absolute_url(),
      'description': doc.description,
      'tags': [{'id': tag.id, 'name': tag.tag} for tag in doc.tags.all()],
      'perms': {
        'read': {
          'users': [{'id': perm_user.id, 'username': perm_user.username} for perm_user in read_perms.users.all()],
          'groups': [{'id': perm_group.id, 'name': perm_group.name} for perm_group in read_perms.groups.all()]
        },
        'write': {
          'users': [{'id': perm_user.id, 'username': perm_user.username} for perm_user in write_perms.users.all()],
          'groups': [{'id': perm_group.id, 'name': perm_group.name} for perm_group in write_perms.groups.all()]
        }
      },
      'owner': doc.owner.username,
      'isMine': doc.owner.username == user.username,
      'lastModified': doc.last_modified.strftime("%x %X"),
      'lastModifiedInMillis': time.mktime(doc.last_modified.timetuple())
    }


def add_tag(request):
  response = {'status': -1, 'message': ''}

  if request.method == 'POST':
    try:
      tag = DocumentTag.objects.create_tag(request.user, request.POST['name'])
      response['name'] = request.POST['name']
      response['id'] = tag.id
      response['docs'] = []
      response['owner'] = request.user.username
      response['status'] = 0
    except Exception, e:
      response['message'] = force_unicode(e)
  else:
    response['message'] = _('POST request only')

  return HttpResponse(json.dumps(response), mimetype="application/json")


def tag(request):
  response = {'status': -1, 'message': ''}

  if request.method == 'POST':
    request_json = json.loads(request.POST['data'])
    try:
      tag = DocumentTag.objects.tag(request.user, request_json['doc_id'], request_json.get('tag'), request_json.get('tag_id'))
      response['tag_id'] = tag.id
      response['status'] = 0
    except Exception, e:
      response['message'] = force_unicode(e)
  else:
    response['message'] = _('POST request only')

  return HttpResponse(json.dumps(response), mimetype="application/json")


def update_tags(request):
  response = {'status': -1, 'message': ''}

  if request.method == 'POST':
    request_json = json.loads(request.POST['data'])
    try:
      doc = DocumentTag.objects.update_tags(request.user, request_json['doc_id'], request_json['tag_ids'])
      response['doc'] = massage_doc_for_json(doc, request.user)
      response['status'] = 0
    except Exception, e:
      response['message'] = force_unicode(e)
  else:
    response['message'] = _('POST request only')

  return HttpResponse(json.dumps(response), mimetype="application/json")


def remove_tag(request):
  response = {'status': -1, 'message': _('Error')}

  if request.method == 'POST':
    try:
      DocumentTag.objects.delete_tag(request.POST['tag_id'], request.user)
      response['message'] = _('Project removed!')
      response['status'] = 0
    except Exception, e:
      response['message'] = force_unicode(e)
  else:
    response['message'] = _('POST request only')

  return HttpResponse(json.dumps(response), mimetype="application/json")


def update_permissions(request):
  response = {'status': -1, 'message': _('Error')}

  if request.method == 'POST':
    data = json.loads(request.POST['data'])
    doc_id = request.POST['doc_id']
    try:
      doc = Document.objects.get_doc(doc_id, request.user)
      doc.sync_permissions(data)
      response['message'] = _('Permissions updated!')
      response['status'] = 0
      response['doc'] = massage_doc_for_json(doc, request.user)
    except Exception, e:
      LOG.exception(e.message)
      response['message'] = force_unicode(e)
  else:
    response['message'] = _('POST request only')

  return HttpResponse(json.dumps(response), mimetype="application/json")
