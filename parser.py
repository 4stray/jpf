from typing import (
    AnyStr,
    List,
    Sequence,
    Iterable,
    Union,
    Optional,
)

from bs4 import BeautifulSoup
from bs4.element import Tag

from aiohttp import ClientResponse, ClientSession

import asyncio
import time
import csv
import re


from serializer import JobSerializer

SOURCE_DOMAIN = 'https://www.work.ua'
SOURCE_URL = SOURCE_DOMAIN + '/ru/jobs-kharkiv-it/'


async def perform_tasks_non_suspiciously(tasks, batch, delay):
    result = []
    for i in range(len(tasks) // batch):
        batch_slice = slice(i * 10, (i + 1) * 10)
        await asyncio.sleep(delay)
        batch_result = await asyncio.gather(*tasks[batch_slice], return_exceptions=True)
        if batch_result:
            result.extend(batch_result)
    return result if result else None


class Item(object):
    def __init__(self, source: AnyStr):
        self.source = source
        self.soup: Optional[BeautifulSoup] = None
        self.resp: Optional[ClientResponse] = None

    async def make_soup(self):
        async with ClientSession() as session:
            async with session.get(self.source) as resp:
                soup_content = await resp.text()
                self.resp, self.soup = resp, BeautifulSoup(soup_content, "html.parser")
                self.initial_soup_parse()

    def initial_soup_parse(self):
        pass


class Job(Item):
    serializer = JobSerializer()

    def __init__(self, source: AnyStr):
        super(Job, self).__init__(source)
        self.degree_required = False
        self.for_disabled = False
        self.for_students = False
        self.full_time = False
        self.half_time = False
        self.experience = None
        self.max_salary = None
        self.min_salary = None
        self.company = None
        self.title = None
        self.description = None

    def name_header(self):
        return self.soup.find('h1', id='h1-name')

    def initial_soup_parse(self):
        name_header = self.name_header()
        self.title = name_header.text
        for paragraph in name_header.find_next_siblings('p'):
            if paragraph.find(title='Зарплата') is not None:
                salary = re.split(r'\s{2,}', re.sub(r'[^A-Za-z0-9]', ' ', paragraph.get_text()).strip())
                salary = (sal.replace(' ', '') for sal in salary)
                salary = [int(sal) for sal in salary if sal.isnumeric()]
                if len(salary) > 1:
                    self.min_salary = min(salary)
                    self.max_salary = max(salary)
                elif salary:
                    self.min_salary = self.max_salary = salary[0]
            elif paragraph.find(title='Данные о компании') is not None:
                anchor = paragraph.find('a')
                self.company = anchor.text if anchor else paragraph.text
            elif paragraph.find(title='Условия и требования') is not None:
                content = re.split(r'[.,]', re.sub(r'\s+', ' ', paragraph.get_text()))
                content = (cond.strip() for cond in content)
                self.parse_work_conditions((cond.lower() for cond in content))
        # print(self)

    def parse_work_conditions(self, content: Iterable[AnyStr]):
        for cond in content:
            if 'опыт' in cond:
                self.experience = re.findall(r'\d+', cond)[0]
            elif 'неполная' in cond:
                self.half_time = True
            elif 'полная' in cond:
                self.full_time = True
            elif 'студента' in cond:
                self.for_students = True
            elif 'с инвалидностью' in cond:
                self.for_disabled = True

    @property
    def salary(self):
        if self.min_salary != self.max_salary:
            return f'{self.min_salary} - {self.max_salary}'
        else:
            return self.min_salary

    def json(self):
        return self.serializer.dump(self)

    def __str__(self):
        return f'"{self.title}" in "{self.company}" for {self.salary} with conditions:\n' \
               f'\tUniversity Degree is required : {self.degree_required};' \
               f'\tApproach for disabled: {self.for_disabled};' \
               f'\tApproach for students: {self.for_students};' \
               f'\tExperience: {self.experience} years' \
               f'\tFull Time: {self.full_time};' \
               f'\tHalf Time: {self.half_time};'


class Page(Item):
    def __init__(self, source: AnyStr):
        super(Page, self).__init__(source)
        self.jobs: List[Job] = []
        self._jobs_container: Optional[Tag] = None

    def jobs_container(self) -> Tag:
        if not self._jobs_container:
            self._jobs_container = self.soup.find(id='pjax-job-list')
        return self._jobs_container

    def paginator(self) -> Tag:
        return self.jobs_container().find('ul', class_='pagination')

    def job_cards(self) -> Sequence[Tag]:
        container = self.jobs_container()
        return container.find_all('div', class_=['card', 'job-link']) if container else []

    def job_links(self) -> Sequence[AnyStr]:
        return [
            SOURCE_DOMAIN + card.find('h2').find('a')['href']
            for card in self.job_cards() if 'job-link' in card['class']
        ]

    async def retrieve_jobs(self) -> None:
        self.jobs = [Job(link) for link in self.job_links()]
        await asyncio.gather(*(job.make_soup() for job in self.jobs), return_exceptions=True)


class Pager(object):
    def __init__(self, first_page_url: AnyStr):
        self.pages: List[Page] = [Page(first_page_url)]
        self.first_page_url = first_page_url
        self._number_of_pages = None

    @property
    def number_of_pages(self) -> int:
        if not self._number_of_pages and self.pages:
            zero_paginator = self.pages[0].paginator()
            links = zero_paginator.find_all('a')
            self._number_of_pages = int(links[-2].text) if links else 1
        return self._number_of_pages

    async def retrieve_pages(self):
        await self.pages[0].make_soup()
        if self.number_of_pages < 2:
            return
        pages = [Page(f'{self.first_page_url}?page={page_number}') for page_number in range(2, self.number_of_pages + 1)]
        for i in range(self.number_of_pages // 10 + 1):
            await asyncio.sleep(0.05)
            await asyncio.gather(*(page.make_soup() for page in pages[i * 10:(i + 1) * 10]), return_exceptions=True)
        self.pages.extend(pages)

    def add_page(self, page: Union[Page, AnyStr]) -> None:
        self.pages.append(page)

    def all_jobs(self):
        for page in self.pages:
            yield from page.jobs


class Parser(object):
    def __init__(self, source: AnyStr, loop: Optional[asyncio.BaseEventLoop] = None):
        self.source = source
        self.pager = Pager(self.source)
        self.loop = loop or asyncio.get_event_loop()

    def gather(self):
        self.loop.run_until_complete(self.pager.retrieve_pages())
        for page in self.pager.pages:
            time.sleep(1)
            self.loop.run_until_complete(page.retrieve_jobs())

    def export(self, fname):
        jobs = [job.json() for job in self.pager.all_jobs()]
        with open(fname, 'w') as target:
            writer = csv.DictWriter(target, fieldnames=jobs[0].keys())
            writer.writeheader()
            for job in jobs:
                writer.writerow(job)


parser = Parser(SOURCE_URL)
parser.gather()
parser.export(fname='export.csv')

# print(parser.pager.links())
