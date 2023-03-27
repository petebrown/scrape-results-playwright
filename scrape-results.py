from bs4 import BeautifulSoup
import pandas as pd
from playwright.sync_api import sync_playwright
import concurrent.futures
import time

def get_soup(url):
    with sync_playwright() as pw:
        chrome = pw.chromium.launch(headless=True)
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/69.0.3497.100 Safari/537.36")
        page = chrome.new_page(user_agent = ua)
        page.goto(url, wait_until="domcontentloaded")
        doc = page.content()
        doc = BeautifulSoup(doc, "lxml")
        chrome.close() 
    return doc

def get_season_list():
    url = "https://www.11v11.com/teams/tranmere-rovers/tab/matches/"
    doc = get_soup(url)
    
    seasons = doc.select("ul#season li a")

    season_list = []

    for season in seasons:
        s = {
            "season_text": season.text,
            "season_url": season["href"]
            }
        season_list.append(s)
    
    return season_list

def get_match_list(doc):
    matches = doc.select_one('.seasonTitle').find_next_sibling('table').select("tbody tr")
    return matches

def get_season_soup(url):
    doc = get_soup(url)
    match_list = get_match_list(doc)
    return match_list

def get_specific_row(rows, col_title):
    for row in rows:
        columns = row.select('td')
        column_title = columns[0].text.strip()
        if column_title == col_title:
            value = columns[1].text.strip()
            break
        else:
            value = ""
    return value

def get_match_specifics(url):
    doc = get_soup(url)

    try:
        match_notes = doc.select_one('div.match div.comments.match').get_text().strip().replace("\n", "|")
    except:
        match_notes = ""

    rows = doc.select_one('.basicData').select('tr')
    
    score_2 = get_specific_row(rows, "Score")
    competition_2 = get_specific_row(rows, "Competition")
    stadium = get_specific_row(rows, "Venue")
    attendance = get_specific_row(rows, "Attendance").replace(",", "")
    
    match_specifics = {
        "stadium": stadium,
        "attendance": attendance,
        "competition_2": competition_2,
        "score_2": score_2,
        "match_notes": match_notes,
    }
    
    return match_specifics
    
def get_match_info(match):
    game_info = match.select('td')
        
    date = game_info[0].get_text().strip()

    teams = game_info[1].text.strip()
    team_names = teams.split(' v ')
    home_team = team_names[0]
    away_team = team_names[1]

    game_url = game_info[1].select_one('a')['href']
    game_url = f"https://www.11v11.com{game_url}"

    outcome = game_info[2].text

    score = game_info[3].get_text().strip()

    competition = game_info[4].text.strip()

    game_record = {
        "game_date": date,
        "home_team": home_team,
        "away_team": away_team,
        "game_url": game_url,
        "outcome": outcome,
        "score": score,
        "competition": competition
    }

    game_details = get_match_specifics(game_url)

    game_record.update(game_details)
    print(game_record)

    return game_record

def extract_season_urls(season_list):
    season_list = [s["season_url"] for s in season_list]
    return season_list

def async_scraping(scrape_function, urls):
    MAX_THREADS = 8
    threads = min(MAX_THREADS, len(urls))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = executor.map(scrape_function, urls)

    return results

url = "https://www.11v11.com/teams/tranmere-rovers/tab/matches/"

seasons = get_season_list()

season_urls = extract_season_urls(seasons)

tic = time.perf_counter()

all_seasons = async_scraping(get_season_soup, season_urls)
all_seasons = list(all_seasons)

all_matches = [match for season in all_seasons for match in season]

match_records = async_scraping(get_match_info, all_matches[:20])
match_records = list(match_records)
df = pd.DataFrame(match_records)
df.to_csv("records.csv", index = False)

toc = time.perf_counter()
print(f"Completed in {toc - tic:0.4f} seconds")
