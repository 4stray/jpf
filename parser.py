from typing import (
    AnyStr,
    List,
    Sequence,
    Union,
    Optional,
)

from bs4 import BeautifulSoup
from bs4.element import Tag
from requests import get, Response

SOURCE_DOMAIN = 'https://www.work.ua'
SOURCE_URL = SOURCE_DOMAIN + '/ru/jobs-kharkiv-it/'


class Item(object):
    def __init__(self, source: Response):
        self.source = source
        self.soup = BeautifulSoup(self.source.text, 'html.parser')


class Job(Item):
    def __init__(self, source: Response):
        super(Job, self).__init__(source)
        print(self.soup.find('h1', id='h1-name'))


class Page(Item):
    def __init__(self, source: Response):
        super(Page, self).__init__(source)
        self.jobs: List[Item] = []
        self._jobs_container: Optional[Tag] = None
        self.collect_jobs()

    def jobs_container(self) -> Tag:
        if not self._jobs_container:
            self._jobs_container = self.soup.find(id='pjax-job-list')
        return self._jobs_container

    def job_cards(self) -> Sequence[Tag]:
        return self.jobs_container().find_all('div', class_=['card', 'job-link'])

    def paginator(self) -> Tag:
        return self.jobs_container().find('ul', class_='pagination')

    def collect_jobs(self) -> None:
        for card in self.job_cards():
            if 'job-link' not in card['class']:
                continue
            job_source_url = SOURCE_DOMAIN + card.find('h2').find('a')['href']
            job_source = get(job_source_url)
            job = Job(job_source)
            self.jobs.append(job)


class Pager(object):
    def __init__(self, pages: List[Page] = None):
        self.pages = pages or []
        self._pages_number = None

    @property
    def pages_number(self) -> int:
        if not self._pages_number:
            zero_paginator = self.pages[0].paginator()
            links = zero_paginator.find_all('a')
            self._pages_number = int(links[-2].text) if links else 1
        return self._pages_number

    def add(self, page: Union[Page, Response, AnyStr]) -> None:
        if isinstance(page, str):
            page = get(page)
        if isinstance(page, Response):
            page = Page(page)
        self.pages.append(page)

    def add_from_url(self, source_url):
        page_source = get(source_url)
        page = Page(page_source)
        self.add(page)


class Parser(object):
    def __init__(self, url):
        self.source_url = url
        self.pager = Pager()
        self.collect_pages()

    def collect_pages(self) -> None:
        self.pager.add_from_url(self.source_url)
        if self.pager.pages_number == 1:
            return
        for pn in range(2, self.pager.pages_number + 1):
            page_source = get(self.source_url, {'page': pn})
            self.pager.add(Page(page_source))


parser = Parser(SOURCE_URL)
# print(parser.pager.links())
