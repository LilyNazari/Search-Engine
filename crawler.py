
########################################################IMPORTS############################################################
import requests
from bs4 import BeautifulSoup
from whoosh.index import create_in
from whoosh.fields import *
from whoosh import index
from whoosh.qparser import QueryParser
from whoosh import query
from flask import Flask, request, render_template
from urllib.parse import urljoin
import re
import os

#######################################################CRAWLER#########################################################
app = Flask(__name__)
prefix = 'https://vm009.rz.uos.de/crawl/'
start_url = prefix + 'index.html'
agenda = [(start_url, 0)]
visited = set()
max_depth = 2

index_dir = "indexdir"
if not os.path.exists(index_dir):
    os.mkdir(index_dir)

schema = Schema(title=TEXT(stored=True), content=TEXT(stored=True), summary=TEXT(stored=True), url=ID(stored=True))
ix = create_in("indexdir", schema)       
writer = ix.writer()
ix = index.open_dir("indexdir")



while agenda:
    url, depth = agenda.pop(0)
    if url in visited or depth > max_depth:
        continue
    visited.add(url)
    print("Processing:", url)
    try:
        r = requests.get(url)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')

            title = soup.title.string if soup.title else "No title"
            content = soup.get_text()
            content = " ".join(content.split()[:1000])
            summary = content[:200] + "..." if len(content) > 200 else content 
            
            writer.add_document(title=title, content=content, summary=summary, url=url)
            
            if depth < max_depth:
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(prefix, href)  # Convert relative URLs to absolute
                    if (
                        full_url.startswith(prefix)  # Ensure links belong to the target domain
                        and full_url not in visited  # Avoid revisiting
                        and not full_url.endswith(('.jpg', '.png', '.pdf'))  # Filter out unwanted files
                    ):
                        agenda.append((full_url, depth + 1))
    except Exception as e:
        print(f"Failed to get {url}: {e}")

writer.commit()
print("Crawling and indexing completed!")
###################################################DATA RETRIEVAL#########################################################


@app.route("/", methods=["GET"])
@app.route("/search")
def search():
    query_terms = request.args.get('q')  # The input query from the user
    if not query_terms:
        return render_template('start.html', results=[])  # Empty results in case no query is provided
    else:
        # Spliting the query into words and operator
        query_terms = query_terms.strip().lower()
        
        if "and" in query_terms:
            operator = "and"
        elif "or" in query_terms:
            operator = "or"
        else:
            operator = "and"  # AND is the default if no operator is specified

        words = query_terms.split()
        
        
        if operator == "and":
            combined_query = query.And([QueryParser("content", ix.schema).parse(word) for word in words])
        elif operator == "or":
            combined_query = query.Or([QueryParser("content", ix.schema).parse(word) for word in words])
        
        
        with ix.searcher() as searcher:
            results = searcher.search(combined_query)
            #results_list = [{"title": result['title'], "url": result['url'], "summary": result['summary']} for result in results]
            def highlight_text(summary, words):  #Using regular expression to find and wrap query terms for highlighting
                highlighted_summary = summary
                for word in words:
                    highlighted_summary = re.sub(rf'({re.escape(word)})', r'<span class="highlight">\1</span>', highlighted_summary, flags=re.IGNORECASE)
                return highlighted_summary
            
            results_list = []
            for result in results:
                title = result['title']
                url = result['url']
                summary = result['summary']
                highlighted_summary = highlight_text(summary, words)
                
                # Add the result to the results list with highlighted summary
                results_list.append({"title": title, "url": url, "summary": highlighted_summary})

    
    
    # Render the results in the results.html template
    return render_template('results.html', results=results_list)


if __name__ == "__main__":
    app.run(debug=True)  


#NEXT:
#HANDLE THE SERVER & wiki