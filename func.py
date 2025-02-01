import fitz
import requests
import datetime
import hashlib
import json
import os
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from urllib3 import disable_warnings
import hashlib
from tavily import TavilyClient
from dotenv import load_dotenv

from sql import sql_statistics_by_id

if __name__ == '__main__' or '.' not in __name__:
    from log import log
else:
    from .log import log


load_dotenv()
disable_warnings()  # Сайт БГУ не безопасен

tavily_client = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))


def parsing_links():
    root_link = 'https://philology.bsu.by'
    raspisanie_link = f'{root_link}/ru/studjentu/raspisanie'

    text = requests.get(raspisanie_link, verify=False).text
    soup = BeautifulSoup(text, "html.parser")

    links = {}

    for a_tag in soup.find_all('a', href=True):
        link = root_link + a_tag['href']
        text = a_tag.get_text(strip=True)

        if 'raspisanie/' in link:  # логично и просто
            links[text] = link

    log('parsing_links', str(link))
    return links


def translate_to_bel(text: str) -> str:
    try:
        return GoogleTranslator(source='ru', target='be').translate(text)
    except Exception as e:
        return text
    

def parsing_pdf(link):

    text = requests.get(link, verify=False).text
    soup = BeautifulSoup(text, 'html.parser')

    pdf_links = []

    for p_tag in soup.find_all('p'):  # проходимся по специальностям

        strong_tag = p_tag.find('strong')
        if strong_tag:

            specialty = strong_tag.get_text(strip=True).split('(')[0]

            temp_links = {}
            for a_tag in p_tag.find_all('a', href=True):  # по курсам
                pdf_link = a_tag['href']
                text = a_tag.get_text(strip=True)
                temp_links[text] = pdf_link

            if temp_links:
                pdf_links.append({'ru_name': specialty, 'bel_name': translate_to_bel(specialty), 'content': temp_links})

    log('parsing_pdf', str(link))
    return pdf_links
    

def parsing():
    result = {}

    links = parsing_links()

    for name, link in links.items():
        pdfs = parsing_pdf(link)

        if pdfs:
            hash_name = hashlib.md5(name.encode('utf-8')).hexdigest()

            result[hash_name] = {
                'ru_name': name,
                'bel_name': translate_to_bel(name),
                'content': pdfs
            }

    path = 'data.json'
    with open(path, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False)
    
    log('parsing', f'Расписание было обновленно в {current_time()}. Длина: {len(result)}')

    return result


'''
{
    "d500510e6b9dc0689177a9a1a94b5d67": {
        "ru_name": "Расписание занятий студентов дневного отделения (І семестр) 2024-2025",
        "bel_name": "Расклад заняткаў студэнтаў дзённага аддзялення (І семестр) 2024-2025",
        "content": [
            {
                "ru_name": "Специальность \"Белорусская филология\" ",
                "bel_name": "Спецыяльнасць \"Беларуская філалогія\"",
                "content": {
                    "1 курс": "/files/dnevnoe/raspisanie/1_bel.pdf",
                    ...
                }
            },
            ...
        ],
        ...
    },
    ...
}
'''


def get_data(json_name: str = 'data.json') -> dict:
    path = os.path.join(os.path.dirname(__file__), json_name)

    if not(os.path.exists(path)) or os.path.getsize(path) == 0:
        log('get_data', 'Создаем json файл')
        parsing()

    with open(path, 'r', encoding='utf-8') as file:
        log('get_data')
        data = json.load(file)

    return data


def download_pdf(link: str) -> str | bool:
    
    try:
        if not link.startswith('https:/'):
            root_link = 'https://philology.bsu.by/'
            link = root_link + link


        response = requests.get(link, verify=False)

        if response.status_code == 404:
            log(f'download_pdf', f'404: {link}')
            return False
        
        file_name = '_'.join(link.split('/')[-3:])  # https://philology.bsu.by/files/dnevnoe/raspisanie/4_rom-germ.pdf >>> dnevnoe_raspisanie_4_rom-germ.pdf

        with open(file_name, 'wb') as file:
            file.write(response.content)

        log('download_pdf', str(link))
        return file_name
    
    except Exception as e:
        log('download_pdf', f'{e}, {link}', error=True)
        return False


def pdf_to_png(pdf_path: str) -> list[str]:
    file_name = pdf_path[:-4]
    doc = fitz.open(pdf_path)
    photos = []
    count = len(doc)
    n = 2  # качество страниц
        
    for i in range(count):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(n, n))
        temp_file_name = f"{file_name}_{i}.png"
        pix.save(temp_file_name)
        photos.append(temp_file_name)

    doc.close()

    return photos


def current_hour():
    delta = datetime.timedelta(hours=3, minutes=0)
    current_time = datetime.datetime.now(datetime.timezone.utc) + delta
    return current_time.hour


def current_time():
    delta = datetime.timedelta(hours=3, minutes=0)
    current_time = datetime.datetime.now(datetime.timezone.utc) + delta
    return current_time.strftime("%H:%M:%S %d.%m.%Y")


def hash_pdf(path: str) -> str | bool:

    hash_sha256 = hashlib.sha256()

    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(), b""):
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()


def cheak_schedule_file():
    file_path = 'schedule_links.json'
    if not os.path.isfile(file_path):
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump({}, json_file, ensure_ascii=False)


def add_schedule_link_or_id(link: str, id: int) -> bool:
    file_path = 'schedule_links.json'
    cheak_schedule_file()
    with open(file_path, 'r', encoding='utf-8') as json_file:
        schedule_links = json.load(json_file)

    result = schedule_links.copy()

    if link in schedule_links.keys():
        if id not in schedule_links[link]['id']:
            log('add_schedule_link_or_id', f'New id: {id}, {link}')
            result[link] = {
                'hash': schedule_links[link]['hash'],
                'id': schedule_links[link]['id'] + [id]
            }
    else:
        log('add_schedule_link_or_id', f'new link: {link}, {id}')
        path = download_pdf(link)
        if path:
          
          hash_value = hash_pdf(path)

          result[link] = {
              'hash': hash_value,
              'id': [id]
          }


        else:
          log('add_schedule_link_or_id path error', f'link={link}, path={path}', error=True)
          return False

    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False)

    return True


def remove_id_by_shedule(link: str, id: int):
    file_path = 'schedule_links.json'
    cheak_schedule_file()
    with open(file_path, 'r', encoding='utf-8') as json_file:
        schedule_links = json.load(json_file)
    result = schedule_links.copy()

    with open(file_path, 'r', encoding='utf-8') as json_file:
        schedule_links = json.load(json_file)


    if link not in schedule_links.keys():
        log('remove_id_by_shedule', f'{link} not in {schedule_links.keys()}. {id}')
        return

    if id not in schedule_links[link]['id']:
        log('remove_id_by_shedule', f'{id} not in {schedule_links[link]["id"]}. {link}')
        return

    del result[link]

    if len(schedule_links[link]['id']) > 1:
        log('remove_id_by_shedule', f'remove {id} for {link}')
        id_list = schedule_links[link]['id']
        del id_list[id_list.index(id)]

        result[link] = {
            'hash': schedule_links[link]['hash'],
            'id': id_list
        }
    else:
        log('remove_id_by_shedule', f'1 id({id}) for {link}. delete link')


    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False)


def remove_id_form_all_shedule(id: int) -> None:
    file_path = 'schedule_links.json'
    cheak_schedule_file()
    with open(file_path, 'r', encoding='utf-8') as json_file:
        schedule_links = json.load(json_file)

    result = schedule_links.copy()

    for link in schedule_links.keys():
        if id in schedule_links[link]['id']:
            if len(schedule_links[link]['id']) > 1:
                id_list = schedule_links[link]['id']
                del id_list[id_list.index(id)]
                result[link] = {
                    'hash': schedule_links[link]['hash'],
                    'id': id_list
                }
            else:
                del result[link]

    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False)


def get_shedule_id(link: str) -> list:
    file_path = 'schedule_links.json'
    cheak_schedule_file()
    with open(file_path, 'r', encoding='utf-8') as json_file:
        schedule_links = json.load(json_file)

    if link in schedule_links.keys():
        return schedule_links[link]['id']
      
    else:
      return []


def cheak_link_hash() -> list:
    file_path = 'schedule_links.json'
    cheak_schedule_file()
    with open(file_path, 'r', encoding='utf-8') as json_file:
        schedule_links = json.load(json_file)
    
    result = schedule_links.copy()

    link_to_update = []

    for link in schedule_links.keys():
        path = download_pdf(link)
        if path:
            pdf_hash = hash_pdf(path)
            if pdf_hash != schedule_links[link]['hash']:
                link_to_update.append(link)
                result[link] = {'id': schedule_links[link]['id'], 'hash': pdf_hash}

        else:
          log('cheak_link_hash', f'{link}: не получилось скачать', error=True)

    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False)   

    log('cheak_link_hash', str(link_to_update)) 

    return link_to_update



def parsing_text_for_url(url: str) -> str:
    try:
        result = [r['raw_content'] for r in tavily_client.extract(urls=url)['results']][0]
        log('parsing_text_for_url', result)
    except Exception as e:
        log('parsing_text_for_url', f'url={url}, error={e}', error=True)
        return f'Error: {e}'
    
