import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import logging.config
from dotenv import load_dotenv
import csv
from urllib.parse import urlparse

logging.config.fileConfig('logging.conf')
log = logging.getLogger('crawling')
HOST_MAPPER = {'melon': 'www.melon.com', 'vibe': 'vibe.naver.com'}

load_dotenv()

options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-extensions")

driver = webdriver.Chrome(options=options)
songs = []

def get_host(uri: str) -> str:
    parsed_url = urlparse(uri)
    return parsed_url.hostname

def extract_songs(uri:str):
    host = get_host(uri)

    if host == HOST_MAPPER['melon']:
        rows_xpath = '/html/body/div/div[2]/div/div/div[2]/div/div[1]/form/div/table/tbody/tr'
        WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.XPATH, rows_xpath)))

        rows = driver.find_elements(By.XPATH, rows_xpath)
        for row in rows:
            try:
                title = row.find_element(By.XPATH, './td[3]/div/div/a[2]').text
                artist = row.find_element(By.XPATH, './td[4]/div/div/a').text
                songs.append((title, artist))
            except:
                continue
    else:
        raise Exception(f"{host} is not supported platform.")

def get_songs(uri:str):
    log.debug(f"Received [{uri}]")
    host = get_host(uri)
    log.info(f"Let's make [{host}] csv file.")

    driver.get(uri)
    time.sleep(2)
    songs.clear()

    if host == HOST_MAPPER['melon']:
        extract_songs(uri)
        home_xpath = '/html/body/div/div[2]/div/div/div[2]/div/div[2]/div'
        WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.XPATH, home_xpath)))

        home = driver.find_element(By.XPATH, home_xpath)
        last_page = home.find_element(By.XPATH, './span').text[-1]
        
        for i in range(int(last_page)):
            try:
                home = driver.find_element(By.XPATH, home_xpath)
                next_button = home.find_element(By.XPATH, f'./span/a[{i+1}]')
                log.info(f'{next_button.text} 번째 페이지 이동')
                next_button.click()
                time.sleep(2)
                extract_songs(uri)
            except:
                break

    elif host == HOST_MAPPER['vibe']:
        ad_close_button_xpath = '/html/body/div[3]/div/div/div/div/a[2]'
        WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.XPATH, ad_close_button_xpath)))
        ad_close_button = driver.find_element(By.XPATH, ad_close_button_xpath)
        ad_close_button.click()
        time.sleep(0.5)

        home = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[3]/main/div[2]')
        total_qty = home.find_element(By.XPATH, './div[1]/div[2]/div/span/span').text
        more_button = home.find_element(By.XPATH, './div[3]/a/span')
        for _ in range(int(total_qty) // 100):
            driver.execute_script("arguments[0].click();", more_button)
            time.sleep(2)

        rows = driver.find_elements(By.XPATH, '/html/body/div[1]/div/div[3]/main/div[2]/div[2]/div/table/tbody/tr')
    
        for row in rows:
            try:
                title = row.find_element(By.XPATH, './td[3]/div[1]/span/a/span').text
                artist = row.find_element(By.XPATH, './td[3]/div[2]/span[1]/span/a/span').text
                songs.append((title, artist))
            except:
                continue
    else:
        raise Exception(f"{host} is not supported platform.")

def save_csv(file_path: str):
    sorted_songs = sorted(songs, key=lambda x: x[0])
    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["곡명", "아티스트"])
        writer.writerows(sorted_songs)

if __name__ == "__main__":
    old_playlist_uri = os.getenv("old_playlist_uri")
    new_playlist_uri = os.getenv("new_playlist_uri")

    try:
        get_songs(old_playlist_uri)
        save_csv("old_playlist.csv")
        get_songs(new_playlist_uri)
        save_csv("new_playlist.csv")
    except Exception as e:
        log.error(f"Error occurred: {e}")
        raise e
    finally:
        if driver:
            driver.quit()