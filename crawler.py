
########################################################IMPORTS############################################################
import requests
from bs4 import BeautifulSoup
from whoosh.index import create_in
from whoosh.fields import *
from whoosh import index
from whoosh.qparser import QueryParser
from whoosh import query
from flask import Flask, request, render_template

app = Flask(__name__)
#######################################################CRAWLER#########################################################

prefix = 'https://vm009.rz.uos.de/crawl/'
start_url = prefix + 'index.html'
agenda = [start_url]
visited = set()

schema = Schema(title=TEXT(stored=True), content=TEXT(stored=True), url=ID(stored=True))
ix = create_in("indexdir", schema)       
writer = ix.writer()



while agenda:
    url = agenda.pop()
    if url in visited:
        continue
    visited.add(url)
    print("Get:", url)
    try:
        r = requests.get(url)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            title = soup.title.string if soup.title else "No title"
            content = soup.get_text()
            writer.add_document(title=title, content=content)
            for link in soup.find_all('a', href= True):
                full_url = prefix+link['href']
                if full_url not in visited and full_url not in agenda:
                    agenda.append(full_url)
    except Exception as e:
        print(f"Failed to get {url}: {e}")

writer.commit()
print("Crawling and indexing completed!")
###################################################DATA RETRIEVAL#########################################################
ix = index.open_dir("indexdir")


@app.route("/")
def start():
    return render_template('start.html')


@app.route("/search")
def search():
    query_terms = request.args.get('q')  # The input query from the user
    if not query_terms:
        return render_template('results.html', results=[])  # If no query is provided, return empty results

    # Split the query into words and operator (assuming user enters AND/OR in uppercase)
    query_terms = query_terms.strip().lower()
    
    if "and" in query_terms:
        operator = "and"
    elif "or" in query_terms:
        operator = "or"
    else:
        operator = "and"  # Default to AND if no operator is specified

    words = query_terms.split()
    
    # Create a combined query using "AND" or "OR" depending on user input
    if operator == "and":
        combined_query = query.And([QueryParser("content", ix.schema).parse(word) for word in words])
    elif operator == "or":
        combined_query = query.Or([QueryParser("content", ix.schema).parse(word) for word in words])

    # Search the index with the combined query
    with ix.searcher() as searcher:
        results = searcher.search(combined_query)
        results_list = [{"title": result['title'], "url": result['url']} for result in results]

    # Render the results in the results.html template
    return render_template('results.html', results=results_list)


if __name__ == "__main__":
    app.run(debug=True)  


#NEXT:
#FUNCTIONAL DEBUGGING
#HANDLE THE SERVER
#After each search there's no place for the next search, is that okay?

#GPT SUGGESTION: IS IT RELEVANT OR TOO COMPLEX?
#You are appending links to the agenda list with this logic: full_url = prefix + link['href']
#However, this could be problematic because the href attribute might contain relative URLs (e.g., /about.html), 
#in which case you need to resolve these relative URLs to form complete URLs.
#You can use urljoin from the urllib.parse library to handle relative URLs properly.

#LATER:
#Modify the frontend (start.html) to display search results, including title and content snippets.and check the course for ideas.
#Improve the content extraction by providing summaries of the pages in schema

