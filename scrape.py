import asyncio
import aiohttp
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

INDEX_URL = 'https://spa5.scrape.center/api/book/?limit=18&offset={offset}'
DETAIL_URL = 'https://spa5.scrape.center/api/book/{id}'
PAGE_SIZE = 1
PAGE_NUMBER = 10 # 调整为实际页数
CONCURRENCY = 10  # 并发量，可以根据网络和服务器负载调整

semaphore = asyncio.Semaphore(CONCURRENCY)

async def scrape_api(session, url):
    async with semaphore:
        try:
            logging.info('Scraping %s', url)
            async with session.get(url) as response:
                return await response.json()
        except aiohttp.ClientError:
            logging.error('Failed to scrape %s', url, exc_info=True)

async def fetch_list_pages(session):
    tasks = []
    for offset in range(0, PAGE_NUMBER * PAGE_SIZE, PAGE_SIZE):
        url = INDEX_URL.format(offset=offset)
        task = asyncio.create_task(scrape_api(session, url))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    return results

async def fetch_detail_page(session, book_id):
    url = DETAIL_URL.format(id=book_id)
    return await scrape_api(session, url)

async def process_chunk(chunk):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_detail_page(session, book_id) for book_id in chunk]
        return await asyncio.gather(*tasks)

async def main():
    async with aiohttp.ClientSession() as session:
        list_pages = await fetch_list_pages(session)
        book_ids = []
        for page in list_pages:
            if page and 'results' in page:
                for book in page['results']:
                    book_ids.append(book['id'])

    chunk_size = 100
    book_id_chunks = [book_ids[i:i + chunk_size] for i in range(0, len(book_ids), chunk_size)]

    detail_pages = []
    for chunk in book_id_chunks:
        detail_pages.extend(await process_chunk(chunk))

    # 提取和保存所需的字段
    data = []
    for book in detail_pages:
        if book:
            authors = ', '.join(book.get('authors', []))
            tags = ', '.join(book.get('tags', []))
            tags = tags.replace('\\n', '').replace(' ', '')
            authors = authors.replace('\\n','').replace(' ','')
            item = {
                '书名':book.get('name',''),
                '简介': book.get('introduction', ''),
                '定价': book.get('price', ''),
                '标签':tags,
                '作者': authors,
                '出版时间': book.get('published_at', ''),
                '出版社': book.get('publisher', ''),
                '页数': book.get('page_number', ''),
                'ISBN': book.get('isbn', '')
            }
            data.append(item)

    # 保存数据
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    import time
    start_time = time.time()
    asyncio.run(main())
    end_time = time.time()
    print(str(end_time - start_time) + ' seconds')