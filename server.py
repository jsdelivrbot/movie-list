from flask import Flask, render_template, make_response, redirect
from flask.ext.restful import Api, Resource, reqparse, abort

import json
import string
import random
from datetime import datetime

# Define our priority levels.
# These are the values that the "priority" property can take on a help request.
RATINGS = ('G', 'PG', 'PG-13', 'R')

# Limit licence option to yes/no.
LICENCES = ('Licenced', 'Unlicenced')

# Load data from disk.
# This simply loads the data from our "database," which is just a JSON file.
with open('data.jsonld') as data:
    data = json.load(data)


# Generate a unique ID for a new help request.
# By default this will consist of six lowercase numbers and letters.
def generate_id(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


# Respond with 404 Not Found if no help request with the specified ID exists.
def error_if_movie_not_found(movie_id):
    if movie_id not in data['movielist']:
        message = "No movie with ID: {}".format(movie_id)
        abort(404, message=message)


# Filter and sort a list of movies.
def filter_and_sort_movielist(query='', sort_by='title'):

    # Returns True if the query string appears in the help request's
    # title or description.
    def matches_query(item):
        (movie_id, movie) = item
        text = movie['title'] + movie['licence']
        return query.lower() in text

    # Returns the help request's value for the sort property (which by
    # default is the "time" property).
    def get_sort_value(item):
        (movie_id, movie) = item
        return movie[sort_by]

    filtered_movielist = filter(matches_query, data['movielist'].items())

    return sorted(filtered_movielist, key=get_sort_value, reverse=True)


# Given the data for a movie, generate an HTML representation
# of that help request.
def render_movie_as_html(movie):
    return render_template(
        'movie.html',
        movie=movie,
        licences=reversed(list(enumerate(LICENCES))))


# Given the data for a list of movies, generate an HTML representation
# of that list.
def render_movie_list_as_html(movielist):
    return render_template(
        'movielist.html',
        movielist=movielist,
        licences=LICENCES)

def render_showing_as_html(movie):
    return render_template(
        'showing.html',
        movie=movie)


# Raises an error if the string x is empty (has zero length).
def nonempty_string(x):
    s = str(x)
    if len(x) == 0:
        raise ValueError('string is empty')
    return s


# Specify the data necessary to create a new help request.
# "title", "rating", and "licence" are all required values.
new_movie_parser = reqparse.RequestParser()
for arg in ['title', 'rating', 'licence', 'description', 'duration']:
    new_movie_parser.add_argument(
        arg, type=nonempty_string, required=True,
        help="'{}' is a required value".format(arg))


# Specify the data necessary to update an existing help request.
# Only the licence and showtimes can be updated.
update_movie_parser = reqparse.RequestParser()
update_movie_parser.add_argument(
    'licence', type=str, default='')
update_movie_parser.add_argument(
    'title', type=str, default='')


# Specify the parameters for filtering and sorting help requests.
# See `filter_and_sort_movielist` above.
query_parser = reqparse.RequestParser()
query_parser.add_argument(
    'query', type=str, default='')
query_parser.add_argument(
    'sort_by', type=str, choices=('title', 'licence'), default='title')


# Define our help request resource.
class Movie(Resource):

    # If a help request with the specified ID does not exist,
    # respond with a 404, otherwise respond with an HTML representation.
    def get(self, movie_id):
        error_if_movie_not_found(movie_id)
        return make_response(
            render_movie_as_html(
                data['movielist'][movie_id]), 200)

    # If a help request with the specified ID does not exist,
    # respond with a 404, otherwise update the help request and respond
    # with the updated HTML representation.
    def patch(self, movie_id):
        error_if_movie_not_found(movie_id)
        movie = data['movielist'][movie_id]
        update = update_movie_parser.parse_args()
        movie['licence'] = update['licence']
        if len(update['licence'].strip()) > 0:
            movie.setdefault('licence')(update['licence'])
        return make_response(
            render_movie_as_html(movie), 200)


# Define a resource for getting a JSON representation of a movie.
class MovieAsJSON(Resource):

    # If a help request with the specified ID does not exist,
    # respond with a 404, otherwise respond with a JSON representation.
    def get(self, movie_id):
        error_if_movie_not_found(movie_id)
        movie = data['movielist'][movie_id]
        movie['@context'] = data['@context']
        return movie


# Define our help request list resource.
class MovieList(Resource):

    # Respond with an HTML representation of the help request list, after
    # applying any filtering and sorting parameters.
    def get(self):
        query = query_parser.parse_args()
        return make_response(
            render_movie_list_as_html(
                filter_and_sort_movielist(**query)), 200)

    # Add a new help request to the list, and respond with an HTML
    # representation of the updated list.
    def post(self):
        movie = new_movie_parser.parse_args()
        movie_id = generate_id()
        movie['@id'] = 'request/' + movie_id
        movie['@type'] = 'movielist:Movie'
        data['movielist'][movie_id] = movie
        return make_response(
            render_movie_list_as_html(
                filter_and_sort_movielist()), 201)


# Define a resource for getting a JSON representation of the help request list.
class MovieListAsJSON(Resource):
    def get(self):
        return data

class Showing(Resource):
    def get(self):

        return make_response(render_showing_as_html(data ['movielist']), 200)

# Assign URL paths to our resources.
app = Flask(__name__)
api = Api(app)
api.add_resource(MovieList, '/movielist.html')
api.add_resource(MovieListAsJSON, '/movielist.json')
api.add_resource(Movie, '/movie/<string:movie_id>')
api.add_resource(MovieAsJSON, '/movie/<string:movie_id>.json')
api.add_resource(Showing, '/showings.html')


# Redirect from the index to the list of help requests.
@app.route('/')
def index():
    return redirect(api.url_for(MovieList), code=303)


# This is needed to load JSON from Javascript running in the browser.
@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
  return response

# Start the server.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=True)
