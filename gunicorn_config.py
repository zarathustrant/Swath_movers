"""
Gunicorn Configuration for Swath Movers Application

Optimized for:
- 8 CPU cores
- 15GB RAM
- High concurrent user load
- GIS/mapping operations
"""

import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = 5  # Optimal for 8 cores with 15GB RAM
worker_class = "gthread"  # Threaded worker for better concurrency
threads = 4  # 4 threads per worker = 20 total workers
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests (prevent memory leaks)
max_requests_jitter = 50  # Add randomness to prevent all workers restarting simultaneously
timeout = 120  # 2 minutes timeout for heavy GIS operations
keepalive = 5  # Keep-alive connections

# Process naming
proc_name = "swath_movers"

# Server mechanics
daemon = False  # Don't daemonize (systemd handles this)
pidfile = None
user = None  # Run as the user who starts the process
group = None
umask = 0
tmp_upload_dir = None

# Logging
accesslog = "/home/aerys/Documents/ANTAN3D/logs/gunicorn-access.log"
errorlog = "/home/aerys/Documents/ANTAN3D/logs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process optimization
preload_app = True  # Load application code before forking workers
worker_tmp_dir = "/dev/shm"  # Use shared memory for worker heartbeat

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Swath Movers application starting...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Swath Movers application...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Swath Movers server is ready. Spawning workers...")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)" % worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker initialized successfully")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info("Worker exited (pid: %s)" % worker.pid)

def child_exit(server, worker):
    """Called just after a worker has been reaped."""
    pass

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Swath Movers shutting down...")
