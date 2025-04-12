"""
This script does the following:

1. replace any partial bibliography entries of the form ["title"](url) in
   papers.md with more complete citations using info from crossref.org.
2. write papers.html from scratch based on markdown.md

To revise a citation, can edit papers.md and then rerun this script.

If you have previously collected the papers in Zotero, you can right-click on
the new ones, export as a bibliography, then use ChatGPT with this prompt to
convert them into the required format:

Can you give me the titles and URLs of some papers in the following format?
```
["title1"](url)
["title2"](url)
```

These are the papers:
```
<insert bibliography entries here, including titles and URLs>
```

One good technique is to put all the new citations at the top of the document in
abbreviated form (as above), then run the script to convert them to full
bibliography entries, then distribute them to the right rows of the right
sections.

Before running, you should run something like
conda create -n bibliography requests fuzzywuzzy markdown
conda activate bibliography
"""

import requests
import json
from fuzzywuzzy import fuzz
from markdown import markdown


# Function to retrieve paper metadata using CrossRef API
def get_citation(title, url):
    # this is slow, so give an update
    print(f'Retrieving citation for "{title}".')

    # basic citation
    citation = f'["{title}."]({url})'

    # get more metadata if possible
    api_url = f"https://api.crossref.org/works"
    params = {
        "query.bibliographic": title,
        # get several rows and pick our favorite (if we just use 1, sometimes
        # it's an older preprint instead of a journal article)
        "rows": 4,
        "mailto": "matthias@energyinnovation.org",
    }
    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data["message"]["items"]:
            # prefer the newest version with a good enough match
            items = data["message"]["items"]
            for item in items:
                item["cr_title"] = item.get("title", [""])[0]
                item["match"] = fuzz.token_set_ratio(title, item["cr_title"])
                item["issue_date"] = item.get("issued", {}).get("date-parts", [[None]])[
                    0
                ]
            paper = max(
                items,
                key=lambda p: (
                    99 if p["match"] >= 99 else p["match"],
                    [0, 0, 0] if p["issue_date"] == [None] else p["issue_date"],
                ),
            )

            cr_title = paper.get("title", [""])[0]
            match = paper["match"]
            if match < 90:
                # bail out if the title doesn't match the first paper
                print(f'   Not matched in crossref. Closest is "{cr_title}".')
                return citation
            if match < 99:
                print(f"   WARNING: weak title match:")
                print(f'        "{title}"')
                print(f'    vs. "{cr_title}"')

            authors = paper.get("author", [])
            authors = [
                f"{author.get('given', '')} {author.get('family', '')}"
                for author in authors
            ]
            for i in range(0, len(authors) - 2):
                authors[i] += ","
            if len(authors) > 1:
                authors[-1] = "and " + authors[-1]
            author_names = " ".join(authors)
            journal = paper.get("container-title", [""])[0]
            publication_year = (
                "undated"
                if paper["issue_date"] == [None]
                else str(paper["issue_date"][0])
            )
            volume = paper.get("volume", "")
            issue = paper.get("issue", "")
            page = paper.get("page", "")

            citation = f'["{title}."]({url})'

            if authors:
                citation = f"{author_names}. {citation}"

            if journal:
                citation += f" _{journal}_".replace("&amp;", "&")
                if volume:
                    citation += f" {volume}"
                    if issue:
                        citation += f", no. {issue}"

            citation += f" ({publication_year})"
            if page:
                citation += f": {page}"

            citation += "."

            # Add a bullet at the start
            citation = "- " + citation

            # if (
            #     title
            #     == "Climate Change and Its Influence on Water Systems Increases the Cost of Electricity System Decarbonization"
            # ):
            #     breakpoint()

    return citation


# read the current version of the article list
with open("papers.md") as f:
    lines = f.read().splitlines()

# Replace plain [article](url) lines with full citations
for i, line in enumerate(lines):
    line = line.strip()
    if (
        line.startswith('"[')
        and line.endswith(')"')
        or line.startswith("[")
        and line.endswith(")")
    ):
        # Extract title from the line
        title_start = line.index("[") + 1
        title_end = line.index("](")
        title = line[title_start:title_end]
        # clean up if we have one of our own short citations back
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        if title.endswith("."):
            title = title[:-1]

        # Extract URL from the line
        url_start = title_end + 2
        url_end = len(line) - (1 if line.endswith(")") else 2)
        url = line[url_start:url_end]

        # Retrieve metadata using CrossRef API
        lines[i] = get_citation(title, url)
    # else:
    #     print(f"Skipping `{line}`")

papers_markdown = "\n".join(lines)

papers_html = f"""<!DOCTYPE html>
<html>

  <head>
    <meta charset='utf-8'>
    <meta http-equiv="X-UA-Compatible" content="chrome=1">
    <meta name="description" content="Papers written with Switch power system planning model : ">

    <link rel="stylesheet" type="text/css" media="screen" href="stylesheets/stylesheet.css">

    <title>Papers Written with Switch</title>
  </head>

  <body>
    <!-- HEADER -->
    <div id="header_wrap" class="outer">
        <header class="inner">
          <h1 id="project_title">Papers Written with Switch</h1>
        </header>
    </div>

    <!-- MAIN CONTENT -->
    <div id="main_content_wrap" class="outer">
      <section id="main_content" class="inner">

<p>These can give you an idea of work that others have done—possibly in your
region—and may point you toward possible data sources, collaborators, advisors
or shared code.</p>

{markdown(papers_markdown)}
      </section>
    </div>
  </body>
</html>
"""

with open("papers.md", "w") as f:
    f.write(papers_markdown)

with open("papers.html", "w") as f:
    f.write(papers_html)

print("re-wrote papers.md and created papers.html")
