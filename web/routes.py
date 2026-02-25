"""Route declaration."""
import os
from flask import current_app as app
from flask import render_template
from .bib2html import load_bibliography, render_bibliography

# Load and render bibliography once at startup
_BIB_DIR = os.path.join(os.path.dirname(__file__), 'static', 'bib')
_BIB_ENTRIES = load_bibliography(
    os.path.join(_BIB_DIR, 'abb.bib'),
    os.path.join(_BIB_DIR, 'mtg.bib'),
)
_BIB_HTML = render_bibliography(_BIB_ENTRIES, author_filter='Bond')


# nav = [
#     {"name": "Home", 'page' : 'home'},
#     {"name": "Short CV", 'page':'cv'},
#     {"name": "Publications", 'page':'pubs'},
#     {"name": "Recipes", 'page':'recipes'},
#     ]
nav = {
    'home': {"name":"Home",
             'desc':"Francis Bond's Humble home page"},
    'cv': {"name":"CV",
           'desc':"All too much about Francis Bond"},
    'pubs': {"name": "Publications",
             'desc':''},
    'recipes': {"name": "Recipes",
                'desc':'Some food I like to cook'},
    'erdos': {"name": "Erdős Number",
              'desc':'How many papers to get me to Paul Erdős'}
}




@app.route("/pubs.html")
def pubs():
    """Publications page (generated from BibTeX)."""
    return render_template(
        'pubs.html',
        page='pubs',
        nav=nav,
        title=nav['pubs']['name'],
        description=nav['pubs']['desc'],
        bib_html=_BIB_HTML,
    )

@app.route("/<page>.html")
def show(page):
    """Show a page"""
    return render_template(
        f"{page}.html",
        page=page,
        nav=nav,
        title=nav[page]['name'],
        description=nav[page]['desc'],
    )

@app.route("/")
def home():
    """show the home page"""
    return show('home')

