from typing import Literal

import pandas as pd
import spacy

from datetime import datetime, timedelta
from dateutil.parser import parse
from django.utils import timezone
from langdetect import detect
from spacy import Language
from statistics import mean, median


def get_entries_in_date_range(
        entries: list[dict],
        date_min: datetime,
        date_max: datetime = datetime.now(),
        date_key: str = 'time'
) -> list:
    """
    Filter a series to only keep entries recorded in the given date range.
    date_key is used to look up the date field in the entries.

    Args:
        entries (list[dict]): List of entries to be filtered.
        date_min (datetime): Entries with min this date are kept in the list.
        date_max (datetime): Entries with max this date are kept in the list.
        date_key (str): The identifier used to look up the date field
            in the entries.

    Returns:
        list[dict]: The list of entries with dates in the date range.
    """
    date_min = make_tz_aware(date_min)
    date_max = make_tz_aware(date_max)

    result = []
    for entry in entries:
        if date_key not in entry:
            continue

        # Check whether date in entry is offset-aware
        entry_date = parse(entry[date_key])
        if date_min <= make_tz_aware(entry_date) <= date_max:
            result.append(entry)
    return result


def make_tz_aware(date: datetime) -> datetime:
    """
    Check if a date is timezone-aware. If not, add timezone.utc as default.

    Args:
        date (datetime): Date to be checked.

    Returns:
        datetime: Timezone aware date.
    """
    if (date.tzinfo is not None and
            date.tzinfo.utcoffset(date) is not None):
        return date
    else:
        return date.replace(tzinfo=timezone.utc)


def normalize_datetime(
        date: datetime,
        mode: Literal['d', 'w', 'm', 'y'] = 'd'
) -> datetime:
    """
    Normalizes a datetime object to a specific day, week, month, or year.

    Args:
        date (datetime): Date to be normalized.
        mode (Literal['d', 'w', 'm', 'y']): The normalization mode.
            'd' (daily): returns date.
            'w' (weekly): returns date of first day of the week to which date
                belongs.
            'm' (monthly): returns the 15th of the month of date.
            'y' (yearly): returns the 1st of July of the year of date.
            Note: Time is in each case set to 00:00.

    Returns:
        datetime: The normalized date.
    """
    date = date.date()

    if mode == 'd':
        return datetime.combine(date, datetime.min.time())

    elif mode == 'w':
        week_start = date - timedelta(days=date.weekday())
        return datetime.combine(week_start, datetime.min.time())

    elif mode == 'm':
        return datetime.combine(date.replace(day=15), datetime.min.time())

    elif mode == 'y':
        return datetime.combine(date.replace(day=1, month=7), datetime.min.time())

    else:
        print('Invalid mode.')
        return datetime.combine(date, datetime.min.time())


def summarize_list(
        li: list[int | float],
        n: int = 1,
        mode: Literal['sum', 'median', 'mean'] ='sum'
) -> int | float:
    """
    Summarizes a list of numbers as either sum, median, or mean.

    Args:
        li (list): List of numbers to be summarized.
        n (int): The number of reference cases.
        mode (Literal['sum', 'median', 'mean']): The summarization mode.
            'sum' - Returns the sum over all list elements.
            'median' - Returns the median of the list elements.
            'mean' - Returns the mean of the list elements.

    Returns:
        float | int: The computed statistic.
    """
    while len(li) < n:
        li.append(0)

    if mode == 'sum':
        return sum(li)
    elif mode == 'median':
        return median(li)
    elif mode == 'mean':
        return mean(li)
    else:
        print('Invalid mode.')
        return 0


def get_summary_counts_per_date(
        data: list[list[datetime]],
        ref: str = 'd',
        base: str = 'sum'
) -> dict:
    """
    Summarizes date occurrences across dates and persons.

    Args:
        data (list[list[datetime]]): A list of lists where the inner lists hold the data
            related to one person ([[{P1, e1}, {p1, e2}], [{P2, e1}, {P2, e2}]]).
        ref (str): Defines the reference of the date counts:
            'd' - counts per day (default)
            'w' - counts per week (attributed to the date of the first day of
                the week)
            'm' - counts per month (attributed to the 15th of the month)
            'y' - counts per year (attributed to the 1st of July of the year)
        base (str): Defines how the counts will be summarized:
            'sum' - Sum over all persons
            'mean' - Mean over all persons
            'median' - Median over all persons

    Returns:
        dict: Dictionary containing summary counts per date ({'date': count})
    """
    n_cases = len(data)
    dates_combined = []
    for p in data:
        dates_combined += p

    date_list = [normalize_datetime(d, mode=ref) for d in dates_combined]

    # Prepare count dictionary.
    counts = {d: [] for d in set(date_list)}

    # Add counts per person.
    for p in data:
        normalized_dates = [normalize_datetime(d, mode=ref) for d in p]
        individual_date_list = pd.Series(normalized_dates).value_counts()
        for index, value in individual_date_list.items():
            counts[index].append(value)

    # iterate over counts and sum/median/average (whatever)
    for key, value in counts.items():
        counts[key] = summarize_list(value, n=n_cases, mode=base)

    return counts


nlp_de = spacy.load('de_core_news_sm', disable=["parser", "ner"])
nlp_en = spacy.load('en_core_web_sm', disable=["parser", "ner"])

def normalize_texts(texts) -> list[str]:
    """
    This function organizes the normalization of a list of texts by first
    applying a basic set of  preprocessing (lowercasing, stripping white
    spaces), detecting whether a text is English or German
    and then batch processing the English and German texts with
    the appropriate nlp model.

    Args:
        texts (list[str]): A list of text strings.

    Returns:
        list[str]: A list containing the normalized string(s).
    """
    valid_texts = []
    for text in texts:
        text = text.lower().strip()
        if text:
            valid_texts.append(text.lower().strip())

    long_text = ''
    for text in valid_texts:
        long_text += text

    try:
        if detect(long_text) == 'de':
            nlp = nlp_de
        else:
            nlp = nlp_en
    except:
        nlp = nlp_en  # Default

    results = []

    if valid_texts:
        results += normalize_batch(valid_texts, nlp)
    return results


def normalize_batch(
        texts: list[str],
        nlp: Language,
        batch_size: int = 1000
) -> list[str]:
    """
    Normalizes texts with a given nlp model in batches by applying
    the following steps:

    - Removing stop words
    - Noise removal (punctuation etc.)
    - Lemmatization

    Args:
        texts (list[str]): A list of text strings to be normalized.
        nlp (Language): A spacy nlp object.
        batch_size (int): The batch size.

    Returns:
        list: A list containing the normalized texts.
    """
    results = []
    for doc in nlp.pipe(texts, batch_size=batch_size):
        normalized = [token.lemma_.lower() for token in doc
                      if not token.is_stop and not token.is_punct
                      and len(token.lemma_) >= 2]
        results += normalized

    return results
