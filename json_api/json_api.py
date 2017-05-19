# JSON API classes

from user_accounts import *
from article_helpers import *
from search import *

# BEGIN: search API endpoints

# API endpoint to handle search queries; returns 10 results at a time
class SearchEndpointHandler(BaseHandler):
    def pull_api(self, response):
        database_dict = {}
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        option = self.get_query_argument("req", "t")
        results = formatted_search(q, start, option)
        output_list = []
        for article in results:
            try:
                article_dict = {}
                article_dict["id"] = article.pmid
                article_dict["title"] = article.title
                article_dict["authors"] = article.authors
                output_list.append(article_dict)
            except:
                pass
        response["articles"] = output_list
        if len(results) == 0:
            response["start_index"] = -1
            # returns -1 if there are no results;
            # UI can always calculate (start, end) with (start_index + 1, start_index + 1 + len(articles))
            # TODO: consider returning the start/end indices for the range of articles returned instead
        else:
            response["start_index"] = start
        return response


# API endpoint to fetch coordinates from all articles that match a query; returns 200 sets of coordinates at a time
class CoordinatesEndpointHandler(BaseHandler):
    def pull_api(self, response):
        database_dict = {}
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        option = self.get_query_argument("req", "t")
        results = formatted_search(q, start, option, True)
        output_list = []
        for article in results:
            try:
                article_dict = {}
                experiments = json.loads(article.experiments)
                for c in experiments:  # get the coordinates from the experiments
                    output_list.extend(c["locations"])
            except:
                pass
        response["coordinates"] = output_list
        return response


# API endpoint that returns five random articles; used on the front page of Brainspell
class RandomEndpointHandler(BaseHandler):
    def pull_api(self, response):
        database_dict = {}
        results = random_search()
        output_list = []
        for article in results:
            try:
                article_dict = {}
                article_dict["id"] = article.pmid
                article_dict["title"] = article.title
                article_dict["authors"] = article.authors
                output_list.append(article_dict)
            except:
                pass
        response["articles"] = output_list
        return response

# BEGIN: article API endpoints

# API endpoint to get the contents of an article (called by the view-article page)
class ArticleEndpointHandler(BaseHandler):
    def pull_api(self, response):
        pmid = self.get_query_argument("pmid")
        try:
            article = next(get_article(pmid))
            response["timestamp"] = article.timestamp
            response["abstract"] = article.abstract
            response["authors"] = article.authors
            response["doi"] = article.doi
            response["experiments"] = article.experiments
            response["metadata"] = article.metadata
            response["neurosynthid"] = article.neurosynthid
            response["pmid"] = article.pmid
            response["reference"] = article.reference
            response["title"] = article.title
            response["id"] = article.uniqueid
        except:
            response["success"] = 0
        return response

# API endpoint corresponding to BulkAddHandler
class BulkAddEndpointHandler(BaseHandler):
    def post(self): # no wrapper method for POST push APIs yet
        response = {}
        file_body = self.request.files['articlesFile'][0]['body'].decode('utf-8')
        contents = json.loads(file_body)
        if type(contents) == list:
            clean_articles = clean_bulk_add(contents)
            add_bulk(clean_articles)
            response["success"] = 1
        else:
            # data is malformed
            response["success"] = 0
        self.write(json.dumps(response))

# fetch PubMed and Neurosynth data using a user specified PMID, and add the article to our database
class AddArticleEndpointHandler(BaseHandler):
    def push_api(self, response):
        pmid = self.get_query_argument("pmid", "")
        x = getArticleData(pmid) # TODO: name this variable correctly
        request = Articles.insert(abstract=x["abstract"], doi=x["DOI"], authors=x["authors"],
                                  experiments=x["coordinates"], title=x["title"])
        request.execute()
        return response

# edit the authors of an article
class ArticleAuthorEndpointHandler(BaseHandler):
    def push_api(self, response):
        pmid = self.get_query_argument("pmid", "")
        authors = self.get_query_argument("authors", "")
        update_authors(pmid, authors)
        return response

# endpoint for a user to vote on an article tag
class ToggleUserVoteEndpointHandler(BaseHandler):
    def push_api(self, response):
        email = get_email_from_api_key(self.get_query_argument("key", ""))
        topic = self.get_query_argument("topic", "")
        pmid = self.get_query_argument("pmid", "")
        direction = self.get_query_argument("direction", "")
        # exp = int(self.get_query_argument("experiment", ""))
        toggle_vote(pmid, topic, email, direction)
        return response

# BEGIN: table API endpoints

# flag a table as inaccurate
class FlagTableEndpointHandler(BaseHandler):
    def push_api(self, response):
        pmid = self.get_query_argument("pmid", "")
        exp = int(self.get_query_argument("experiment", ""))
        flag_table(pmid, exp)
        return response

# delete row from experiment table
class DeleteRowEndpointHandler(BaseHandler):
    def push_api(self, response):
        pmid = self.get_query_argument("pmid", "")
        exp = self.get_query_argument("experiment", "")
        row = self.get_query_argument("row", "")
        delete_row(pmid, exp, row)
        return response

# split experiment table
class SplitTableEndpointHandler(BaseHandler):
    def push_api(self, response):
        pmid = self.get_query_argument("pmid", "")
        exp = self.get_query_argument("experiment", "")
        row = self.get_query_argument("row", "")
        split_table(pmid, exp, row)
        return response

# add one row of coordinates to an experiment table
class AddCoordinateEndpointHandler(BaseHandler):
    def push_api(self, response):
        pmid = self.get_query_argument("pmid", "")
        exp = self.get_query_argument("experiment", "")
        coords = self.get_query_argument("coordinates", "").replace(" ", "")
        add_coordinate(pmid, exp, coords)
        return response

# BEGIN: non-Github collections API endpoints

# delete a saved article
class DeleteArticleEndpointHandler(BaseHandler):
    def get(self):
        if self.is_logged_in(): # TODO: should take a username/key, rather than checking cookies
            value = self.get_query_argument("article")
            User_metadata.delete().where(User_metadata.user_id == self.get_current_email(),
                                         User_metadata.metadata_id == value).execute()
            self.write(json.dumps({"success": 1}))
        else:
            self.write(json.dumps({"success": 0}))


# access a user's saved articles
class SavedArticlesEndpointHandler(BaseHandler):
    def post(self):
        email = self.get_argument("email").encode("utf-8")
        password = self.get_argument("password").encode("utf-8")
        if user_login(email, password):
            articles = get_saved_articles(email)
            response = {}
            output_list = []
            for a in articles:
                pmid = a.article_pmid
                info = next(get_article(pmid))
                articleDict = {}
                articleDict["id"] = a.metadata_id
                articleDict["pmid"] = pmid
                articleDict["title"] = info.title
                articleDict["collection"] = a.collection
                output_list.append(articleDict)
            response["articles"] = output_list
            self.write(json.dumps(response))
        else:
            self.write(json.dumps({"success": 0}))

