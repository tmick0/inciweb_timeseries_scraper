__all__ = ['get_all_data']

import requests
from bs4 import BeautifulSoup, NavigableString, Comment
import re
from urllib import parse
import nltk
import datefinder
from word2number import w2n
import locale


# acquire nltk data
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('averaged_perceptron_tagger')

# set up locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# constants
URL_ROOT_ARTICLE_PAGE = "https://inciweb.nwcg.gov"
URL_TEMPLATE_NEWS_PAGE = "https://inciweb.nwcg.gov/incident/news/{:d}/{:d}/"
REGEX_USEFUL_ARTICLE = re.compile(".+ Daily Update [0-9]{1,2}/[0-9]{1,2}/[0-9]{1,2}")

def get_one_page_links(incident, offset):
    url = URL_TEMPLATE_NEWS_PAGE.format(incident, offset)
    data = requests.get(url)
    soup = BeautifulSoup(data.content, "html.parser")
    name = soup.find("h1").text
    links = soup.find_all("a", class_="feed-headline")
    nav = soup.find("nav", class_="nav-pagination").find("p")
    first, last, total = map(lambda e: int(e.text), nav.find_all("strong"))
    next_page = None
    if last < total:
        next_page = last

    return name, [(l['href'], l.text) for l in links], next_page


def get_all_links(incident):
    offset = 0
    results = []
    while offset is not None:
        name, partial, offset = get_one_page_links(incident, offset)
        results.extend(partial)
    return name, results


def condense(elem):
    result = []

    if isinstance(elem, NavigableString) and not isinstance(elem, Comment):
        cleaned = re.sub(r'[^\x00-\x7F]+',' ', elem.text) # strip non-ascii
        result.append(cleaned)
    else:
        for e in elem:
            result += condense(e)

    return result


def process_one_link(rel_url):
    abs_url = parse.urljoin(URL_ROOT_ARTICLE_PAGE, rel_url)
    data = requests.get(abs_url)
    soup = BeautifulSoup(data.content, "html.parser")
    title_text = condense(soup.find("div", class_="ibox-title"))
    body_text = condense(soup.find("div", id="IncidentContent"))

    all_text = ' . '.join(title_text + body_text)
    return apply_nlp(all_text)


def get_best_value(text, value_tag, label_values):
    val = None
    dist = 0

    concordance_list = []
    for l in label_values:
        concordance_list += text.concordance_list(l)

    for s in concordance_list:
        tags = nltk.pos_tag(nltk.tokenize.word_tokenize(s.line))

        label_candidates = []
        value_candidates = []
        
        for i, (token, tag) in enumerate(tags):
            if tag == value_tag:
                value_candidates.append((token, i))
            elif token.lower() in label_values:
                label_candidates.append((token, i))

        for l, i in label_candidates:
            for v, j in value_candidates:
                d = abs(i - j)
                if val is None or d <= dist:
                    val = v
                    dist = d
        
    return val


def apply_nlp(raw_text):
    stemmer = nltk.stem.WordNetLemmatizer()
    
    words = nltk.tokenize.word_tokenize(raw_text)
    tokens = [stemmer.lemmatize(w) for w in words]
    text = nltk.text.Text(tokens)

    date = next(datefinder.find_dates(raw_text))
    size = get_best_value(text, 'CD', ['acre', 'acres'])
    size = process_number(size)
    containment = get_best_value(text, "CD", ['contained', 'containment'])
    containment = process_number(containment)
    
    return date, size, containment


def process_number(text, default=None):
    if text is None:
        return default

    try:
        return locale.atoi(text)
    except ValueError:
        try:
            return w2n.word_to_num(text)
        except ValueError:
            return None


def process_all_links(links):
    data = []
    for rel_url, title in links:
        date, size, containment = process_one_link(rel_url)
        if size is None or containment is None:
            continue
        data.append((date, size, containment))
    return data


def get_all_data(incident):
    name, links = get_all_links(incident)
    return name, process_all_links(links)
