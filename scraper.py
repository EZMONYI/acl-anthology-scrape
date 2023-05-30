from pybtex.database.input import bibtex
import bs4
from bs4 import BeautifulSoup
import requests
import argparse
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

def main(keywords):
    # {C}hinese has 3546 entries, chinese has 2194 entries, 
    # two adds up to 5740, which is the number of matches for 'hinese'
    # hence, the keyword 'Chinese' should present in the two string formats
    # This is ACL anthropoloy quotation handling, check the following link for reason:
    # https://www.quora.com/Why-do-people-occasionally-put-brackets-around-the-first-letter-of-a-word
    # query_first_keyword = ['{c}hinese', 'chinese'] 

    # same math conducted on keywod 'Dataset'
    # query_second_keyword = ['{d}ataset', 'dataset','{d}atasets', 'datasets']
    number_of_keywords = len(keywords)
    keyword_list = [generate_keyword_from_input(keyword) for keyword in keywords]

    parser = bibtex.Parser()
    bib_data = parser.parse_file('./anthology.bib')
    result = []


    total_entries = len(bib_data.entries.items())
    for idx, (key, value) in enumerate(bib_data.entries.items()): # iterate over each entry in bib file
        print('Processing entries ' + str(idx + 1) + ' out of ' + str(total_entries))
        title = value.fields['title'] # field title
        keyword_matches = 0
        for keyword in keyword_list:
            keyword_matches += check_substring_match(keyword, title)
        if keyword_matches == number_of_keywords:
            print('Title: ' + title)
            url = value.fields['url'] # field url
            page = requests.get(url)
            soup = BeautifulSoup(page.text, 'html.parser')
            content = soup.find('dl')
            code_urls = find_url_with_field_name('Code', content)
            data_urls = find_url_with_field_name('Data', content)
            result.append([title, url, code_urls, data_urls])

    df = pd.DataFrame(result, columns=['Title', 'Paper_URL', 'Codebase_URLs', 'Dataset_URLs'])
    df.to_csv('_'.join(keywords) + '.csv', index=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
    '--keywords',
    nargs='*',
    type=str,
    help='ACL keyword of variable length')
    args = parser.parse_args()
    main(args.keywords)