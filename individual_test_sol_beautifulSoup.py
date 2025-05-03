import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import csv

# DB setup
conn = sqlite3.connect('ind_test_solutions.db')
cur = conn.cursor()
cur.execute(''' 
CREATE TABLE IF NOT EXISTS individual_tests (
  sr INTEGER PRIMARY KEY AUTOINCREMENT,
  link TEXT UNIQUE,
  title TEXT,
  description TEXT,
  languages TEXT,
  time TEXT,
  test TEXT,
  remote TEXT,
  download TEXT,
  adaptive_irt TEXT
)
''')
conn.commit()

# 🔧 scrape_individual_test now accepts adaptive_irt from listing page
def scrape_individual_test(url, adaptive_irt):
    print(f"Fetching: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    title = soup.find('h1').get_text(strip=True)

    description = ''
    if h4 := soup.find('h4', string='Description'):
        if p := h4.find_next('p'):
            description = p.get_text(strip=True)

    languages = ''
    if h4 := soup.find('h4', string='Languages'):
        if p := h4.find_next('p'):
            languages = p.get_text(strip=True)

    time = ''
    if h4 := soup.find('h4', string='Assessment length'):
        if p := h4.find_next('p'):
            txt = p.get_text(strip=True)
            m = re.search(r'(\d+)', txt)
            time = m.group(1) if m else txt

    test = ''
    remote = ''
    for p in soup.select('p.product-catalogue__small-text'):
        txt = p.get_text(strip=True)
        if txt.startswith('Test Type:'):
            keys = [span.get_text(strip=True) for span in p.select('span.product-catalogue__key')]
            test = ', '.join(keys)
        elif txt.startswith('Remote Testing:'):
            if p.select_one('span.catalogue__circle.-yes'):
                remote = 'Yes'
            elif p.select_one('span.catalogue__circle.-no'):
                remote = 'No'
            else:
                remote = 'Unknown'

    download = ''
    if h4 := soup.find('h4', string='Downloads'):
        if a := h4.find_next('a', href=True):
            download = a['href'].strip()

    # 🔧 adaptive_irt is passed from listing page, no need to fetch here

    cur.execute(''' 
        INSERT OR IGNORE INTO individual_tests (link, title, description, languages, time, test, remote, download, adaptive_irt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (url, title, description, languages, time, test, remote, download, adaptive_irt))
    conn.commit()
    print(f"✔ Saved: {title}")

# 🔧 Now returns list of (link, adaptive_irt) tuples
def fetch_individual_test_links(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    results = []
    table = soup.find('th', class_='custom__table-heading__title', string='Individual Test Solutions')
    if table:
        wrapper = table.find_parent('table')
        for row in wrapper.find_all('tr')[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) >= 3:
                link_tag = cols[0].find('a', href=True)
                adaptive_col = cols[2]
                adaptive_span = adaptive_col.find('span', class_='catalogue__circle')

                if not link_tag:
                    continue
                href = link_tag['href']
                full_link = 'https://www.shl.com' + href.strip()

                if adaptive_span and '-yes' in adaptive_span['class']:
                    adaptive_irt = 'Yes'
                elif adaptive_span and '-no' in adaptive_span['class']:
                    adaptive_irt = 'No'
                else:
                    adaptive_irt = 'Unknown'

                results.append((full_link, adaptive_irt))
    return results

def save_to_csv():
    cur.execute('SELECT * FROM individual_tests')
    rows = cur.fetchall()
    with open('individual_test_solutions.csv', 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([desc[0] for desc in cur.description])  # Write header
        writer.writerows(rows)
    print("✅ Data saved to individual_test_solutions.csv")

if __name__ == "__main__":
    base_url = "https://www.shl.com/solutions/products/product-catalog/?start={}&type=1"
    step = 12
    max_empty_pages = 3
    empty_count = 0
    seen_links = set()
    total_commits = 0

    for i in range(0, 373, step):
        url = base_url.format(i)
        print(f"\n🔎 Scanning page {url}")
        links_with_adaptive = fetch_individual_test_links(url)
        new_links = [(link, adp) for (link, adp) in links_with_adaptive if link not in seen_links]

        if not new_links:
            empty_count += 1
            if empty_count >= max_empty_pages:
                print("🛑 No more new links. Stopping.")
                break
        else:
            empty_count = 0

        for link, adaptive_irt in new_links:
            seen_links.add(link)
            scrape_individual_test(link, adaptive_irt)
            total_commits += 1

        print(f"🔢 Summary for this page:")
        print(f" - Found {len(new_links)} unique links")
        print(f" - Committed {total_commits} products to the database so far.")

    save_to_csv()
    conn.close()
    print("\n✅ All done!")
