from typing import Literal

import pandas as pd
import spacy

from datetime import datetime, timedelta
from django.utils import timezone
from langdetect import detect
from spacy import Language


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

    # Convert to dataframe for optimized vectorized parsing and filtering
    df = pd.DataFrame(entries)
    if date_key not in df.columns:
        return []

    df[date_key] = pd.to_datetime(df[date_key], errors='coerce')
    df = df.dropna(subset=[date_key])

    # Ensure that dates are timezone aware.
    tz = date_min.tzinfo
    if df[date_key].dt.tz is None:
        df[date_key] = df[date_key].dt.tz_localize(tz)
    else:
        df[date_key] = df[date_key].dt.tz_convert(tz)

    mask = (df[date_key] >= date_min) & (df[date_key] <= date_max)
    return df[mask].to_dict('records')


def make_tz_aware(date: datetime) -> datetime:  # TODO: Check if timezone should be derived from server.
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


def get_summary_counts_per_date(
        data: list[list[datetime]],
        ref: Literal['d', 'w', 'm', 'y']  = 'd',
        base: Literal['sum', 'median', 'mean'] = 'sum'
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
    all_dates = []
    person_date_indices = []

    for person_idx, person_dates in enumerate(data):
        normalized = [normalize_datetime(d, mode=ref) for d in person_dates]
        all_dates.extend(normalized)
        person_date_indices.extend([person_idx] * len(normalized))

    # Create DataFrame for vectorized operations
    df = pd.DataFrame({
        'date': all_dates,
        'person': person_date_indices
    })

    person_counts = df.groupby(['person', 'date']).size().reset_index(name='count')
    pivot = person_counts.pivot(index='date', columns='person', values='count').fillna(0)

    # Apply summary function
    if base == 'sum':
        counts = pivot.sum(axis=1).to_dict()
    elif base == 'mean':
        counts = pivot.mean(axis=1).to_dict()
    elif base == 'median':
        counts = pivot.median(axis=1).to_dict()

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
        cleaned = text.lower().strip()
        if cleaned:
            valid_texts.append(cleaned)

    long_text = ''.join(valid_texts)

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
