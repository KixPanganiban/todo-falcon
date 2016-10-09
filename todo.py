import json
import logging
import os

import falcon
from falcon_cors import CORS
from tinydb import TinyDB, Query

# Replace this with localhost:8000 if running locally
BASE_URL = 'http://todo-backend-falcon.herokuapp.com/todo'


def JSONSerialize(req, resp, resource):
    """Falcon hook to convert response body to JSON
    """
    if isinstance(resp.body, str):
        return resp.body
    resp.body = json.dumps(resp.body)


class TodoResource(object):
    """Handles both collection and single-todo requests.
    """

    def __init__(self):
        """Initialize a TinyDB connection.
        """
        self._db = TinyDB('todos.json')

    def _make_todo(self, todo):
        """Return todo's data as well as id->eid and url.
        """
        return dict(
            id=todo.eid,
            url='{base_url}/{id}'.format(base_url=BASE_URL, id=todo.eid),
            **todo
        )

    @falcon.after(JSONSerialize)
    def on_get(self, req, resp, id=None):
        """Handle GET
        """
        if id is not None:
            todo = self._db.get(eid=int(id))
            if todo is None:
                raise falcon.HTTPNotFound()
            resp.body = self._make_todo(todo)
        else:
            todos = self._db.all()
            resp.body = []
            for todo in todos:
                resp.body.append(self._make_todo(todo))
        resp.status = falcon.HTTP_200

    @falcon.after(JSONSerialize)
    def on_post(self, req, resp, id=None):
        """Handle POST
        """
        if id is not None:
            raise falcon.HTTPMethodNotAllowed(
                ('PATCH',)
            )
        body = json.loads(req.stream.read())
        if not body or 'title' not in body:
            raise falcon.HTTPBadRequest(
                'Missing title',
                'POST request body must include title'
            )
        eid = self._db.insert({
            'title': body['title'],
            'completed': body.get('completed', False),
            'order': body.get('order', 10)
        })
        resp.body = self._make_todo(self._db.get(eid=eid))

    @falcon.after(JSONSerialize)
    def on_patch(self, req, resp, id=None):
        """Handle PATCH
        """
        if id is None:
            raise falcon.HTTPMethodNotAllowed(
                ('GET', 'POST')
            )
        todo = self._db.get(eid=int(id))
        if todo is None:
            raise falcon.HTTPNotFound()

        body = json.loads(req.stream.read())
        if not body:
            raise falcon.HTTPBadRequest(
                'Missing parameters',
                'Parameters must include `title` or `completed`'
            )
        title = body.get('title', self._db.get(eid=int(id))['title'])
        completed = body.get('completed',
                             self._db.get(eid=int(id))['completed'])
        order = body.get('order', self._db.get(eid=int(id))['order'])
        eid = self._db.update({
            'title': title,
            'completed': completed,
            'order': order
        }, eids=[int(id)])
        resp.body = self._make_todo(self._db.get(eid=eid[0]))

    @falcon.after(JSONSerialize)
    def on_delete(self, req, resp, id=None):
        """Handle DELETE
        """
        if id is not None:
            todo = self._db.get(eid=int(id))
            if todo is None:
                raise falcon.HTTPNotFound()

            self._db.remove(eids=[int(id)])
            resp.body = '{}'
        else:
            eids = map(lambda e: e.eid, self._db.all())
            self._db.remove(eids=eids)
            resp.body = '[]'

# Initialize the WSGI app
cors = CORS(allow_all_origins=True, allow_all_headers=True,
            allow_all_methods=True)
app = falcon.API(middleware=[cors.middleware])

# Load the routes
todo = TodoResource()
app.add_route('/todo/', todo)
app.add_route('/todo/{id}', todo)
