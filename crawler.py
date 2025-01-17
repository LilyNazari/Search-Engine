########################################################IMPORTS############################################################
import requests
from bs4 import BeautifulSoup
from whoosh.index import create_in
from whoosh.fields import *
from whoosh import index
from whoosh.qparser import QueryParser
from whoosh import query
from flask import Flask, request, render_template
import re
import os
#######################################################CRAWLER#########################################################
app = Flask(__name__)
prefix = "https://vm009.rz.uos.de/crawl/"
start_url = prefix + "index.html"
agenda = [start_url]
visited = set()
if not os.path.exists("indexdir"):
    os.makedirs("indexdir")
schema = Schema(title=TEXT(stored=True), content=TEXT(stored=True), summary=TEXT(stored=True), url=ID(stored=True))
ix = create_in("indexdir", schema)
writer = ix.writer()
while agenda:
    url = agenda.pop()
    if url in visited:
        continue
    visited.add(url)
    try:
        r = requests.get(url)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "html.parser")
            title = soup.title.string if soup.title else "No title"
            content = soup.get_text()
            summary = content[:200] + "..." if len(content) > 200 else content
            writer.add_document(title=title, content=content, summary=summary, url=url)
            for link in soup.find_all("a", href=True):
                full_url = prefix + link["href"]
                if full_url not in visited and full_url not in agenda:
                    agenda.append(full_url)
    except:
        pass
writer.commit()
ix = index.open_dir("indexdir")
###################################################DATA RETRIEVAL#########################################################

@app.route("/", methods=["GET"])
@app.route("/search", methods=["GET"])
def search():
    query_terms = request.args.get("q")  # the input query from the user
    if not query_terms:
        return render_template("start.html", results=[])    # empty results in case no query is provided otherwise spliting the query into words and operators
    query_terms = query_terms.strip().lower()
    operator = "and"
    if "and" in query_terms:
        operator = "and"
    elif "or" in query_terms:
        operator = "or"
    words = query_terms.split()
    if operator == "and":
        combined_query = query.And([QueryParser("content", ix.schema).parse(word) for word in words])
    else:
        combined_query = query.Or([QueryParser("content", ix.schema).parse(word) for word in words])
    with ix.searcher() as searcher:
        results = searcher.search(combined_query)
        def highlight_text(text, words): #using regular expression to find and wrap query terms for highlighting
            highlighted = text
            for w in words:
                highlighted = re.sub(rf"({re.escape(w)})", r'<span class="highlight">\1</span>', highlighted, flags=re.IGNORECASE)
            return highlighted
        results_list = []
        for r_ in results:
            t = r_["title"]
            u = r_["url"]
            s = highlight_text(r_["summary"], words)
            results_list.append({"title": t, "url": u, "summary": s})  # add the result to the results list with highlighted summary
    return render_template("results.html", results=results_list, query=query_terms) # render the results in the results.html template

if __name__ == "__main__":
    app.run(debug=True)