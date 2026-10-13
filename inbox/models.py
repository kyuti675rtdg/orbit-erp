"""Inbox is a view-layer module over req.Request: no tables of its own.

Pending approvals, personal submissions and decision history are all
derived from requests and their activity events, so the inbox always
reflects the live workflow state.
"""
