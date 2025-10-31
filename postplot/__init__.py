"""
Post Plot Acquisition Map Module
Flask Blueprint for tracking source shot acquisition
"""

from flask import Blueprint

# Create blueprint
postplot_bp = Blueprint(
    'postplot',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/postplot/static'
)

# Import routes (this registers them with the blueprint)
from postplot import routes
