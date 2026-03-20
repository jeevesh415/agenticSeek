import timeit
from bs4 import BeautifulSoup

def original_parse(html_content):
    results = []
    soup = BeautifulSoup(html_content, 'html.parser')
    for article in soup.find_all('article', class_='result'):
        url_header = article.find('a', class_='url_header')
        if url_header:
            url = url_header['href']
            title = article.find('h3').text.strip() if article.find('h3') else "No Title"
            description = article.find('p', class_='content').text.strip() if article.find('p', class_='content') else "No Description"
            results.append(f"Title:{title}\nSnippet:{description}\nLink:{url}")
    return results

def optimized_parse(html_content):
    results = []
    soup = BeautifulSoup(html_content, 'html.parser')
    for article in soup.find_all('article', class_='result'):
        url_header = article.find('a', class_='url_header')
        if url_header:
            url = url_header['href']

            h3 = article.find('h3')
            title = h3.text.strip() if h3 else "No Title"

            p_content = article.find('p', class_='content')
            description = p_content.text.strip() if p_content else "No Description"

            results.append(f"Title:{title}\nSnippet:{description}\nLink:{url}")
    return results

# generate mock html
html_template = """
<article class="result">
    <a class="url_header" href="http://example.com/{i}">Link {i}</a>
    <h3>Title {i}</h3>
    <p class="content">Description {i}</p>
</article>
"""
mock_html = "<html><body>" + "".join([html_template.format(i=i) for i in range(100)]) + "</body></html>"

assert original_parse(mock_html) == optimized_parse(mock_html)

t_orig = timeit.timeit(lambda: original_parse(mock_html), number=1000)
t_opt = timeit.timeit(lambda: optimized_parse(mock_html), number=1000)

print(f"Original: {t_orig:.4f} seconds")
print(f"Optimized: {t_opt:.4f} seconds")
print(f"Improvement: {(t_orig - t_opt) / t_orig * 100:.2f}%")
