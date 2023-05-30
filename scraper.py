from pybtex.database.input import bibtex
import bs4
from bs4 import BeautifulSoup
import requests
import argparse
from multiprocessing import Process, Manager
import pandas as pd

def generate_keyword_from_input(input: str):
    input = input.lower()
    quotation_format = '{'+input[0]+'}'+input[1:]
    return [quotation_format, quotation_format + 's', input, input + 's']


def check_substring_match(keyword: list, source_str: str):
    return any(substring in keyword for substring in source_str.lower().split(' '))


# dl: html description list object from sour.find('dl')
def find_url_with_field_name(field: str, dl):
    if dl.find("dt",string=field):
        temp = []
        for link in iter(dl.find("dt",string=field).findNext("dd").children):
            if isinstance(link, bs4.element.Tag):
                temp.append(link['href'])
        urls = '\n'.join(temp)
    else:
        urls = ''
    return urls


def check_keyword(text: str, keyword_list: list):
    keyword_matches = 0
    for keyword in keyword_list:
        keyword_matches += check_substring_match(keyword, text)
    return keyword_matches


def get_code_and_data_urls(content):
    code_urls = find_url_with_field_name('Code', content)
    data_urls = find_url_with_field_name('Data', content)
    return code_urls, data_urls


def do_work(in_queue, out_list, num_of_keywords, keywords_list):

    while True:
        value = in_queue.get()
        if value is None:
            break
        title = value.fields['title'] # field title
        url = value.fields['url'] # field url
        title_matches = check_keyword(title, keywords_list)
        if title_matches == num_of_keywords:
            try:
                page = requests.get(url)
            except Exception as e:
                print(e)
            soup = BeautifulSoup(page.text, 'html.parser')
            content = soup.find('dl')
            print('Title: ' + title)
            code_urls, data_urls = get_code_and_data_urls(content)
            result = [title, url, code_urls, data_urls]
            out_list.append(result)        

        else:
            try:
                page = requests.get(url)
            except Exception as e:
                print(e)
            soup = BeautifulSoup(page.text, 'html.parser')
            content = soup.find('dl')
            # check if entry has abstract 
            if soup.find("div", class_="card-body acl-abstract"):
                abstract = soup.find("div", class_="card-body acl-abstract").find('span').text
                abstract_matches = check_keyword(abstract, keywords_list)
                if abstract_matches == num_of_keywords:
                    print('Title: ' + title)
                    code_urls, data_urls = get_code_and_data_urls(content)
                    result = [title, url, code_urls, data_urls]
                    out_list.append(result)

    in_queue.task_done()

def main(keywords):
    # {C}hinese has 3546 entries, chinese has 2194 entries, 
    # two adds up to 5740, which is the number of matches for 'hinese'
    # hence, the keyword 'Chinese' should present in the two string formats
    # This is ACL anthropoloy quotation handling, check the following link for reason:
    # https://www.quora.com/Why-do-people-occasionally-put-brackets-around-the-first-letter-of-a-word
    # query_first_keyword = ['{c}hinese', 'chinese'] 

    # same math conducted on keywod 'Dataset'
    # query_second_keyword = ['{d}ataset', 'dataset','{d}atasets', 'datasets']

    num_of_keywords = len(keywords)
    keywords_list = [generate_keyword_from_input(keyword) for keyword in keywords]

    num_workers = 8
    manager = Manager()
    results = manager.list()
    work = manager.Queue(num_workers)

    # start for workers    
    pool = []
    for i in range(num_workers):
        p = Process(target=do_work, args=(work, results, num_of_keywords, keywords_list))
        p.start()
        pool.append(p)

    bib_parser = bibtex.Parser()
    # produce data
    bib_file = bib_parser.parse_file('./anthology.bib')
    bib_data = bib_file.entries.items()
    total_entries = len(bib_data)
    for idx, (key, value) in enumerate(bib_data):
        print('Processing entries ' + str(idx + 1) + ' out of ' + str(total_entries))
        work.put(value)
    results = [x for x in results]
    df = pd.DataFrame(results, columns=['Title', 'Paper_URL', 'Codebase_URLs', 'Dataset_URLs'])
    df.to_csv('_'.join(keywords) + '.csv', index=False)

    for p in pool:
        p.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
    '--keywords',
    nargs='*',
    type=str,
    help='ACL keyword of variable length')
    args = parser.parse_args()
    main(args.keywords)