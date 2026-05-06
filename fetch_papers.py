"""
fetch_papers.py

First step in the ingestion pipeline. 
Pulls recent papers from chosen arXiv categories and prints their details. 

Run with: python fetch_papers.py

"""

import arxiv


# -- Configuration --
# arXiv categories to fetch from and codes 
# cond-mat.soft = Condensed Matter > Soft Condensed Matter
# cond-mat.stat-mech = Condensed Matter > Statistical Mechanics
# cond-mat.mtrl-sci = Condensed Matter > Materials Science
# physics.bio-ph = Physics > Biological Physics
# cs.LG = Computer Science > Machine Learning
# q.fin.ST = Quantitative Finance > Statistical Finance
# physics.soc-ph = Physics > Society and Social Sciences
# physics.data-an = Physics > Data Analysis, Statistics and Probability
# physics.comp-ph = Physics > Computational Physics
# physics.chem-ph = Physics > Chemical Physics
# physics.complex-ph = Physics > Complex Systems
# physics.flu-dyn = Physics > Fluid Dynamics
# biology.bio-ph = Quantitative Biology > Biophysics

CATEGORIES = "cond-mat.soft"
MAX_RESULTS = 20

# -- Build the query --
# arxiv.Search() describes what we want to fetch. 
search = arxiv.Search(
    query=f"cat:{CATEGORIES}", # cat: is arXiv's syntax for category filter
    max_results=MAX_RESULTS,
    sort_by=arxiv.SortCriterion.SubmittedDate, # newest first
    sort_order=arxiv.SortOrder.Descending
)

# -- Create a client and fetch --
# arxiv.Client() is the object that makes the HTTP requests to arXiv
client = arxiv.Client()

print(f"Fetching up to {MAX_RESULTS} papers from arXiv category '{CATEGORIES}'...\n")
print("-" * 80)

# -- Loop through results --
# client.results(search) is a generator that fetches papers one by one
#  as we iterate
print("Starting fetch...")          # add this line

for i, paper in enumerate(client.results(search), start=1):
    
    # paper.author is a list of Author objects, we can join their names
    # we take the first 3 authors for brevity and 
    # add "et al." if there are more
    print(f"Got paper {i}")  
    author_name = [a.name for a in paper.authors[:3]]
    author_str = ", ".join(author_name)
    if len(paper.authors) > 3:
        author_name.append(" et al.")
    # paper.entry_id looks like "http://arxiv.org/abs/2401.12345v1"
    # splitting on "/" and taking the last part gives us "2401.12345v1"
    arxiv_id = paper.entry_id.split("/")[-1]

    print(f"\n{i}. {paper.title}")
    print(f"   ID:        {arxiv_id}")
    print(f"   Published: {paper.published.date()}")
    print(f"   Authors:   {author_str}")
    print(f"   Abstract:  {paper.summary[:200]}...")  # first 200 characters

