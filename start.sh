#!/bin/bash
# Start the Orbit ERP demo server.
cd "$(dirname "$0")"
exec .venv/bin/python manage.py runserver 127.0.0.1:8901
