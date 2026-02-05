"""Route declaration."""
from flask import current_app as app
from flask import render_template


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

