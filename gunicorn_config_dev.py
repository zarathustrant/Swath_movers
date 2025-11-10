"""
Gunicorn Configuration for Swath Movers Application (DEVELOPMENT)

Lightweight config for testing on port 8081
"""

import os

# Server socket - DEVELOPMENT PORT
bind = "127.0.0.1:8081"
backlog = 512

# Worker processes - minimal for development
workers = 2
worker_class = "gthread"
threads = 2
worker_connections = 100
max_requests = 500
max_requests_jitter = 50
timeout = 120
keepalive = 5

# Process naming
proc_name = "swath_movers_dev"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
umask = 0
tmp_upload_dir = None

# Logging
accesslog = "/var/log/swath-movers-dev-access.log"
errorlog = "/var/log/swath-movers-dev-error.log"
loglevel = "debug"  # Debug level for development
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process optimization
preload_app = False
worker_tmp_dir = "/dev/shm"

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Swath Movers DEV application starting on port 8081...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Swath Movers DEV server is ready. Spawning workers...")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("DEV Worker spawned (pid: %s)" % worker.pid)

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Swath Movers DEV shutting down...")
