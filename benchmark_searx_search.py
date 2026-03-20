import timeit
from bs4 import BeautifulSoup

def generate_mock_html(num_results=1000):
    html_parts = ["<html><body>"]
    for i in range(num_results):
        html_parts.append(f"""
        <article class="result">
            <a class="url_header" href="http://example.com/{i}">Link {i}</a>
            <h3>Title {i}</h3>
            <p class="content">Description for result {i} goes here and is a bit longer to simulate real text.</p>
        </article>
        """)
    html_parts.append("</body></html>")
    return "".join(html_parts)

html_content = generate_mock_html(500)

def original_parsing():
    results = []
    soup = BeautifulSoup(html_content, 'html.parser')
    for article in soup.find_all('article', class_='result'):
        url_header = article.find('a', class_='url_header')
        if url_header:
            url = url_header.get('href', '')
            title = article.find('h3').text.strip() if article.find('h3') else "No Title"
            description = article.find('p', class_='content').text.strip() if article.find('p', class_='content') else "No Description"
            results.append(f"Title:{title}\\nSnippet:{description}\\nLink:{url}")
    return results

def optimized_parsing():
    results = []
    soup = BeautifulSoup(html_content, 'html.parser')
    for article in soup.find_all('article', class_='result'):
        url_header = article.find('a', class_='url_header')
        if url_header:
            url = url_header.get('href', '')
            h3_node = article.find('h3')
            p_node = article.find('p', class_='content')
            title = h3_node.text.strip() if h3_node else "No Title"
            description = p_node.text.strip() if p_node else "No Description"
            results.append(f"Title:{title}\\nSnippet:{description}\\nLink:{url}")
    return results

if __name__ == "__main__":
    original_time = timeit.timeit(original_parsing, number=10)
    print(f"Original Parsing Time (10 runs, 500 results each): {original_time:.4f} seconds")

    optimized_time = timeit.timeit(optimized_parsing, number=10)
    print(f"Optimized Parsing Time (10 runs, 500 results each): {optimized_time:.4f} seconds")
    print(f"Improvement: {original_time - optimized_time:.4f} seconds ({(original_time - optimized_time) / original_time * 100:.2f}%)")
