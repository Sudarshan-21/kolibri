#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import sqlite3

logger = logging.getLogger(__name__)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class KolibriDB:
    """Shortcuts to common Kolibri-database queries


    Kolibri uses the Modified Preorder Tree Traversal model, from django-mptt
    https://gist.github.com/tmilos/f2f999b5839e2d42d751"""

    def __init__(self, fpath):
        self.conn = sqlite3.connect(
            f"file:{fpath.expanduser().resolve()}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        self.conn.row_factory = sqlite3.Row
        self._fpath = fpath

    @property
    def fpath(self):
        return self._fpath

    @property
    def name(self):
        return self.fpath.name

    def get_conn(self):
        return self.conn

    def get_row(self, query, *args, **kwargs):
        with self.get_conn() as conn:
            return conn.execute(query, *args, **kwargs).fetchone()

    def get_cell(self, query, *args, **kwargs):
        return self.get_row(query, *args, **kwargs)[0]

    def get_rows(self, query, *args, **kwargs):
        with self.get_conn() as conn:
            cursor = conn.execute(query, *args, **kwargs)
            rows = cursor.fetchmany()
            while rows:
                for row in rows:
                    yield row
                rows = cursor.fetchmany()

    def get_channel_metadata(self, channel_id):
        return self.get_row(
            "SELECT * FROM content_channelmetadata WHERE id=?", (channel_id,)
        )

    def get_node_children(self, node_id, left=None, right=None):
        if left is None or right is None:
            node = self.get_node(with_parents=False, with_children=False)
            left = node["left"]
            right = node["right"]

        for row in self.get_rows(
            "SELECT id, title, kind "
            "FROM content_contentnode WHERE lft > ? AND rght < ? "
            "AND parent_id=?"
            "ORDER BY level ASC",
            (left, right, node_id),
        ):
            row = dict(row)
            row.update(
                {
                    "thumbnail": self.get_thumbnail_name(row["id"]),
                }
            )
            yield row

    def get_node_children_count(self, node_id, left=None, right=None):
        if left is None or right is None:
            node = self.get_node(with_parents=False, with_children=False)
            left = node["left"]
            right = node["right"]

        return self.get_cell(
            "SELECT COUNT(*) FROM content_contentnode WHERE lft > ? AND rght < ? "
            "AND parent_id=?",
            (left, right, node_id),
        )

    def get_node_parents(self, node_id, left=None, right=None):
        if left is None or right is None:
            node = self.get_node(with_parents=False, with_children=False)
            left = node["left"]
            right = node["right"]

        for row in self.get_rows(
            "SELECT id, title FROM content_contentnode "
            "WHERE lft < ? AND rght > ? ORDER BY Lft ASC",
            (left, right),
        ):
            yield dict(row)

    def get_node_parents_count(self, node_id, left=None, right=None):
        if left is None or right is None:
            node = self.get_node(with_parents=False, with_children=False)
            left = node["left"]
            right = node["right"]

        return self.get_cell(
            "SELECT COUNT(*) FROM content_contentnode "
            "WHERE lft < ? AND rght > ? ORDER BY Lft ASC",
            (left, right),
        )

    def get_node(self, node_id, with_parents=False, with_children=False):
        node = self.get_row(
            "SELECT id, title, description, author, level, lft as left, rght as right "
            "FROM content_contentnode WHERE id=?",
            (node_id,),
        )
        if not node:
            return node
        node = dict(node)
        if with_parents:
            node.update(
                {
                    "parents": self.get_node_parents(
                        node_id, node["left"], node["right"]
                    ),
                    "parents_count": self.get_node_parents_count(
                        node_id, node["left"], node["right"]
                    ),
                }
            )

        if with_children:
            node.update(
                {
                    "children": self.get_node_children(
                        node_id, node["left"], node["right"]
                    ),
                    "children_count": self.get_node_children_count(
                        node_id, node["left"], node["right"]
                    ),
                }
            )
        return node

    def get_node_file(self, node_id, thumbnail=False):
        try:
            return next(self.get_node_files(node_id, thumbnail))
        except StopIteration:
            return None

    def get_node_files(self, node_id, thumbnail=False):
        for row in self.get_rows(
            "SELECT local_file_id as id, extension as ext, priority as prio, "
            "supplementary as supp, file_size as size, lang_id as lang, preset "
            "FROM content_file WHERE contentnode_id=? AND available=? AND thumbnail=? "
            "ORDER BY priority ASC",
            (node_id, 1, 1 if thumbnail else 0),
        ):
            yield dict(row)

    def get_node_thumbnail(self, node_id):
        return self.get_node_file(node_id, thumbnail=True)

    def get_thumbnail_name(self, node_id):
        thumbnail = self.get_node_thumbnail(node_id)
        return f"{thumbnail['id']}.{thumbnail['ext']}" if thumbnail else None