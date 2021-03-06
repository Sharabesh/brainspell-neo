# brainspell-neo

[![Build Status](https://travis-ci.org/OpenNeuroLab/brainspell-neo.svg?branch=master)](https://travis-ci.org/OpenNeuroLab/brainspell-neo)

Working on a new version on Brainspell.

Clients can make requests to the JSON API directly, or access Brainspell through the web interface. A running Heroku instance is available at https://brainspell.herokuapp.com/. 

To view a list of all JSON API endpoints, take a look at https://brainspell.herokuapp.com/json/list-endpoints. If you're unsure about the parameters for an endpoint, add `/help` to the end of the URL (e.g., the documentation for https://brainspell.herokuapp.com/json/split-table is available at https://brainspell.herokuapp.com/json/split-table/help). Alternatively, you can try our API via [Swagger](https://swaggerhub.com/apis/neelsomani/brainspell/1.0.0).

## Running Brainspell

To run Brainspell locally:  
1) Clone the Git repo with `git clone git@github.com:OpenNeuroLab/brainspell-neo.git`.
2) Install Postgres (if not already installed). If you have Homebrew installed, you can use `brew install postgres`.
3) Make sure that you're using Python 3.5.
4) Enter the repo with `cd brainspell-neo/`, and install the Python dependencies with `pip install -r requirements.txt`.

Now you can run Brainspell with `python3 brainspell/brainspell.py`. Brainspell should be running at `http://localhost:5000`.

Having difficulty getting Brainspell running? Install [Conda](https://conda.io/docs/get-started.html), and create an environment for Python 3.5.

## Running Brainspell with Docker

First, make sure that you have [Docker](https://docs.docker.com/engine/installation/) installed. Then:  
1) Navigate into the Brainspell directory. (`cd brainspell-neo/`)
2) Build the Docker image with `docker build -t brainspell .`
3) Create the Docker container and run with `docker run --name brainspell -ti -p 5000:5000 brainspell`

Brainspell should be running at `http://localhost:5000/`. The next time that you want to run the Docker container, simply execute `docker start -a brainspell`, and stop the Docker container with `docker stop brainspell`.

## Code Organization

`brainspell/brainspell.py` runs the Tornado main event loop.  
Handlers go in one of three files:
1. `json_api.py`, which contains JSON API endpoints that do not make GitHub API requests,
2. `user_interface.py`, which contains all handlers that render Tornado HTML templates, or
3. `github_collections.py`, which contains all API endpoints and handlers that communicate with GitHub.

Our naming convention is to use `[*]EndpointHandler` for API endpoint handlers, and `[*]Handler` for web interface handlers. 
 
`brainspell/article_helpers.py` contains helper functions for adding articles to the database.  
`brainspell/base_handler.py` is our abstract handler, which provides various helper functions. All handlers should subclass `BaseHandler`.  
`brainspell/deploy.py` is a module for deploying to a remote server using Git.  
`brainspell/models.py` is for our ORM, PeeWee, which lets us treat our database like a Python object.   
`brainspell/search_helpers.py` contains helper functions for searching articles in the database.   
`brainspell/test_tornado.py` is our suite of continuous integration tests.  
`brainspell/user_account_helpers.py` contains helper functions for accessing and mutating user information.  
`brainspell/websockets.py` contains a WebSocket that allows developers to connect to the API using the WebSockets protocol.   
`brainspell/static/` contains the HTML, CSS, images, fonts, and Javascript code for the website.

Our official Postgres database is hosted on AWS, but we have a static database available on Heroku. The full database is available in the `database_dumps` folder.

---

Former website for Brainspell: http://www.brainspell.org
