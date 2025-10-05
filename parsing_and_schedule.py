'''Module for parsing schedules from the BSU website and for working with users schedules'''
import re
import sched
import fitz
import requests
import datetime
import hashlib
import json
import os
from bs4 import BeautifulSoup
from urllib3 import disable_warnings
import hashlib

from sql import sql_insert_to_statistics_by_id
from log import log


disable_warnings()  # BSU website is not secure


def get_current_folder_path():
    return os.path.dirname(__file__)


def minsk_time():
    delta = datetime.timedelta(hours=3, minutes=0)
    current_time = datetime.datetime.now(datetime.timezone.utc) + delta
    return current_time.strftime("%H:%M:%S %d.%m.%Y")


def get_sections_links() -> dict:
    '''From https://philology.bsu.by get the schedule sections: {section_name: link, ...}'''
    log('get_sections_links', 'start')
    root_link = 'https://philology.bsu.by'
    raspisanie_link = f'{root_link}/ru/studjentu/raspisanie'

    text = requests.get(raspisanie_link, verify=False).text
    soup = BeautifulSoup(text, "html.parser")
    links = {}
    log('get_sections_links', f'get soup frin {raspisanie_link}')
    for a_tag in soup.find_all('a', href=True):
        link = root_link + a_tag['href']
        text = a_tag.get_text(strip=True)

        if 'raspisanie/' in link:  # логично и просто
            links[text] = link

    log('get_sections_links', str(link))
    return links


def get_pdfs_from_section(link: str) -> list[dict]:
    '''Get links to pdf files with schedules: [{course_name: str, content: {'1 курс': str, ...}}, ...]'''
    log('get_pdfs_from_section', f'start {link}')
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
                pdf_links.append({'course_name': specialty, 'content': temp_links})

    log('get_pdfs_from_section', str(pdf_links))
    return pdf_links
    

def get_master_degree_links() -> dict:
    '''Для магистрантов существует расписания только на https://philology.bsu.by/ru/magistrantu/magistracy-timetable/dnevnoj-formy-obucheniya'''
    return {'Расписание занятий для студентов магистратуры': 'https://philology.bsu.by/ru/magistrantu/magistracy-timetable/dnevnoj-formy-obucheniya'}

def get_pdfs_from_master_degree(link: str) -> list[dict]:
    '''Магистранты'''
    log('get_pdfs_from_master_degree', 'start')
    
    response = requests.get(link, verify=False)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    article_body = soup.find('div', {'itemprop': 'articleBody'})
    if not article_body:
        print('Article body not found')
        return []
    
    result = []
    paragraphs = article_body.find_all('p')
    
    for p in paragraphs:
        text = p.get_text(strip=True)
        if 'Специальность' in text:
            match = re.search(r'Специальность\s*["\"]([^"\"]+)["\"]', text)
            if match:
                course_name = match.group(1)
                content = {}
                links = p.find_all('a', href=True)
                for link_tag in links:
                    href = link_tag['href']
                    link_text = link_tag.get_text(strip=True)
                    if href.endswith('.pdf'):
                        if href.startswith('http'):
                            href = href.replace('https://philology.bsu.by', '')
                        year_match = re.search(r'(\d+)\s*год', link_text)
                        if year_match:
                            year_key = f"{year_match.group(1)} год"
                            content[year_key] = href
                if content:
                    result.append({
                        'course_name': course_name,
                        'content': content
                    })
    
    log('get_pdfs_from_master_degree', str(result))
    return result

    

def parsing() -> dict:
    '''Create a json file with all links and return it
    {
        'name_hash': {  # we use the hash from the name, as the name is not suitable for inline button
            'name': str,
            'content': [
                {
                    'course_name': str,
                    'content': {
                        '1 курс': str,
                        ...}
                }]
            }
        ...
    }'''
    log('parsing', 'Start creating json file with schedule (bsu_links)')
    result = {}
    links = get_sections_links()

    for section_name, section_link in links.items():
        pdfs = get_pdfs_from_section(section_link)

        if pdfs:
            hash_name = hashlib.md5(section_name.encode('utf-8')).hexdigest()

            result[hash_name] = {
                'name': section_name,
                'content': pdfs
            }

    # магистратура
    for name, link in get_master_degree_links().items():
        pdfs = get_pdfs_from_master_degree(link)
        if pdfs:
            hash_name = hashlib.md5(name.encode('utf-8')).hexdigest()
            result[hash_name] = {
                'name': name,
                'content': pdfs
            }

    path = os.path.join(get_current_folder_path(), 'bsu_links.json')
    with open(path, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False)
    
    log('parsing', f'The schedule was updated in {minsk_time()}. Length: {len(result)}')
    return result


def get_bsu_links() -> dict:
    '''Getting text from json file with schedule'''
    path = os.path.join(get_current_folder_path(), 'bsu_links.json')

    if not os.path.exists(path) or os.path.getsize(path) == 0:
        log('get_bsu_links', f'Create json file', error=True)
        return parsing()

    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    log('get_bsu_links', f'Len: {len(data)}')
    return data


def download_pdf(link: str) -> str | bool:
    '''Download the pdf file from the link. '''
    try:
        if not link.startswith('https:/'):
            root_link = 'https://philology.bsu.by'
            link = root_link + link


        response = requests.get(link, verify=False)

        if response.status_code == 404:
            log(f'download_pdf', f'404: {link}', error=True)
            return False
        
        file_name = '_'.join(link.split('/')[-3:])  # https://philology.bsu.by/files/dnevnoe/raspisanie/4_rom-germ.pdf >>> dnevnoe_raspisanie_4_rom-germ.pdf

        with open(file_name, 'wb') as file:
            file.write(response.content)

        log('download_pdf', str(link))
        return file_name
    
    except Exception as e:
        log('download_pdf', f'{e}, {link}', error=True)
        return False


def pdf_to_png(pdf_path: str, n: int = 2) -> list[str]:
    '''Convert pdf file to png. Return the list of paths to png files'''
    file_name = pdf_path[:-4]
    doc = fitz.open(pdf_path)
    photos = []
    count = len(doc)
        
    for i in range(count):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(n, n)) # type: ignore
        temp_file_name = f"{file_name}_{i}.png"
        pix.save(temp_file_name)
        photos.append(temp_file_name)

    doc.close()

    log('pdf_to_png', f'{pdf_path}')
    return photos


def hash_pdf(path: str) -> str | bool:
    '''Hashing a pdf file. This is used to check if the pdf has been modified'''
    hash_sha256 = hashlib.sha256()

    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(), b""):
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()



def check_schedule_file():
    """Checks if a schedule file exists. If not, creates an empty one."""
    file_path = os.path.join(get_current_folder_path(), 'bsu_schedule_links.json')
    if not os.path.isfile(file_path):
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump({}, json_file, ensure_ascii=False)


def get_schedule_links() -> dict:
    """Get text from bsu_schedule_links.json"""
    check_schedule_file()
    file_path = os.path.join(get_current_folder_path(), 'bsu_schedule_links.json')
    with open(file_path, 'r', encoding='utf-8') as json_file:
        return json.load(json_file)


def add_or_update_schedule_link(link: str, user_id: int) -> bool:
    """Add or update a schedule link with the user ID in the schedule file."""
    file_path = os.path.join(get_current_folder_path(), 'bsu_schedule_links.json')

    schedule_links = get_schedule_links()

    if link in schedule_links:  # если ссылка уже есть
        if user_id not in schedule_links[link]['id']:
            log('add_or_update_schedule_link', f'New id {user_id} for {link}')
            schedule_links[link]['id'].append(user_id)

    else:

        pdf_path = download_pdf(link)
        if pdf_path:
            hash_value = hash_pdf(pdf_path)
            schedule_links[link] = {'hash': hash_value, 'id': [user_id]}
            log('add_or_update_schedule_link', f'New link: {link}. User ID: {user_id}. Hash: {hash_value}')
        else:
            log('add_or_update_schedule_link', f'Error downloading PDF. Link: {link}, ID: {user_id}', error=True)
            return False

    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(schedule_links, json_file, ensure_ascii=False)

    return True


def remove_user_id_from_schedule(link: str, user_id: int) -> None:
    """Remove a user ID from a specific schedule link."""
    file_path = os.path.join(get_current_folder_path(), 'bsu_schedule_links.json')
    
    schedule_links = get_schedule_links()

    if link not in schedule_links:
        log('remove_user_id_from_schedule', f'{link} not found in schedule links. ID: {user_id}', error=True)
        return

    if user_id not in schedule_links[link]['id']:
        log('remove_user_id_from_schedule', f'User ID {user_id} not found for link {link}.')
        return

    schedule_links[link]['id'].remove(user_id)

    if not schedule_links[link]['id']:  # if there is no more user_id for this link
        del schedule_links[link]
        log('remove_user_id_from_schedule', f'No more user IDs for link {link}. Link removed.')
    else:
        log('remove_user_id_from_schedule', f'User ID {user_id} removed from link {link}.')

    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(schedule_links, json_file, ensure_ascii=False)


def remove_user_id_from_all_schedules(user_id: int) -> None:
    """Remove user ID from all schedule links (if user wants to unsubscribe from all schedules)."""
    file_path = os.path.join(get_current_folder_path(), 'bsu_schedule_links.json')

    schedule_links = get_schedule_links()

    updated_links = {}

    for link, data in schedule_links.items():
        if user_id in data['id']:
            data['id'].remove(user_id)
            if data['id']:  # Only keep the link if there are remaining user IDs
                updated_links[link] = data
            else:
                log('remove_user_id_from_all_schedules', f'No more user IDs for link {link}. Link removed.')
        else:
            updated_links[link] = data

    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(updated_links, json_file, ensure_ascii=False)

    log('remove_user_id_from_all_schedules', f'User ID {user_id} removed from all schedule links.')


def gets_link_ids_from_schedule_link(link: str) -> list:
    """Get all user IDs from a specific schedule link."""
    schedule_links = get_schedule_links()

    if link in schedule_links.keys():
        ids = schedule_links[link]['id']
        log('gets_link_ids_from_schedule_link', f'{link}: {ids}')
        return ids
      
    else:
        log('gets_link_ids_from_schedule_link', f'{link} not found in schedule links', error=True)
        return []


def check_schedule_link_hash() -> list:
    """Check if the hash of the PDF files has changed and update the schedule links if necessary."""
    log('check_schedule_link_hash', 'Start checking schedule links')
    file_path = os.path.join(get_current_folder_path(), 'bsu_schedule_links.json')
    
    schedule_links = get_schedule_links()
    updated_links = schedule_links.copy()
    links_to_update = []

    for link, data in schedule_links.items():
        pdf_path = download_pdf(link)
        if pdf_path:
            pdf_hash = hash_pdf(pdf_path)
            if pdf_hash != data['hash']:
                links_to_update.append(link)
                updated_links[link]['hash'] = pdf_hash
            os.remove(pdf_path)
        else:
            log('check_schedule_link_hash', f'Failed to download: {link}', error=True)

    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(updated_links, json_file, ensure_ascii=False)

    log('check_schedule_link_hash', f'Links to update: {links_to_update}')

    return links_to_update


# parsing()
check_schedule_file()