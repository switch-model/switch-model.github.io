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
    params = {"query.bibliographic": title, "rows": 1, "mailto": "mfripp@edf.org"}
    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data["message"]["items"]:
            paper = data["message"]["items"][0]
            cr_title = paper.get("title", [""])[0]
            match = fuzz.token_set_ratio(title, cr_title)
            if match < 90:
                # bail out if the title doesn't match the first paper
                print(f'   Not matched in crossref. Closest is "{cr_title}".')
                return citation
            if match < 99:
                print(f'   WARNING: weak title match to "{cr_title}".')

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
            date_parts = paper.get("issued", {}).get("date-parts", [[]])[0]
            publication_year = str(date_parts[0]) if date_parts else "undated"
            # publication_date = "-".join(str(part).zfill(2) for part in date_parts)
            # if not publication_date:
            #     publication_date = "undated"
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
                citation += f": {page}."
            else:
                citation += "."

    return citation


# read the current version of the article list
with open("papers.md") as f:
    lines = f.read().splitlines()

# Replace plain [article](url) lines with full citations
for i, line in enumerate(lines):
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
