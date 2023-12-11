import requests
from bs4 import BeautifulSoup

__all__ = ("crawl_version_num_and_file_url",)


def crawl_version_num_and_file_url() -> tuple[str, str]:
    resp = requests.get("https://www.sfb.gov.tw/ch/home.jsp?id=1016&parentpath=0,6,52")
    soup = BeautifulSoup(resp.text, "lxml")
    tables = soup.find_all("table", {"class": "table01 table02"})
    trs = tables[0].find_all("tr")
    tds = trs[1].find_all("td")
    version = tds[3].text.strip()
    file_url = tds[4].find_all("a")[1].get("href")
    return version, file_url
