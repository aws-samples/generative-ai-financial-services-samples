import re
from itertools import product
from operator import itemgetter
from nltk.corpus import stopwords
from string import punctuation
from itertools import chain


# Function to get a set of English stop words
def stop_words():
    return set(stopwords.words("english"))


# Function to remove duplicates from a list while preserving order
def dedup(xs):
    seen = set()
    seen_add = seen.add
    return [x for x in xs if not (x in seen or seen_add(x))]


# Function to extract the first number from text, or return a default value
def text_get_number(text, default):
    res = re.findall(r"\d+", text)
    return res[0] if res else default


# Function to extract the first float number from text, or return a default value
def text_get_float(text, default):
    res = re.findall(r"\d+(?:\.\d+)?", text)
    return res[0] if res else default


# Function to tokenize text based on specific delimiters and removing some words
def tokenize(text):
    tokens = re.split(r" and | at | the | of |[\,\;\(\)]", text)
    tokens = [re.sub(r"\bthe", "", x) for x in tokens]
    tokens = [x.strip() for x in tokens]
    tokens = [x for x in tokens if x]
    return dedup(tokens)


# Function to tokenize text into words, removing stop words and punctuation
def text_tokenizer(text):
    tokens = text.split()
    tokens = [t for t in tokens if len(t) > 1]
    tokens = [t for t in tokens if t.lower() not in stop_words()]
    tokens = [x.strip(punctuation) for x in tokens]
    tokens = [x.strip() for x in tokens]
    tokens = [x for x in tokens if x]
    return dedup(tokens)


# Function to find the most compact span of text containing all tokens in order
def spans_of_tokens_ordered(text, tokens):
    """
    Get most compact span of text
    containing tokens preserving the order of tokens
    Returns a list of offsets [i,j]
    """

    # Exclude not present tokens
    text_lo = text.lower()
    tokens = [t for t in tokens if t.lower() in text_lo]
    if not tokens:
        return []

    # Backtracking
    def bfs(text, tokens, path, solutions):
        tabs = len(tokens)

        if not tokens:
            solutions += (path,)
        elif not text:
            pass
        else:
            t = tokens[0]
            after = path[-1][0] if path else 0
            indices = [
                (m.start(), m.end()) for m in re.finditer(t, text, flags=re.IGNORECASE)
            ]
            indices = [(i, j) for i, j in indices if i >= after]

            for i, j in indices:
                bfs(text, tokens[1:], path + [(i, j)], solutions)

    # Collect all solutions
    solutions = []
    bfs(text, tokens, [], solutions)

    # Most compact solution
    solutions = [x for x in solutions if x]
    solution = min(solutions, key=lambda xs: xs[-1][1] - xs[0][0], default=[])
    return solution


# Function to find the most compact span containing all tokens, without order
def spans_of_tokens_compact(text, tokens):
    """
    Find most compact span containing all the tokens.
    Returns a list of offsets [i,j]
    """
    # Exclude not present tokens
    text_lo = text.lower()
    tokens = [t for t in tokens if t.lower() in text_lo]
    if not tokens:
        return []

    occurrences = [
        [(m.start(), m.end()) for m in re.finditer(t, text, flags=re.IGNORECASE)]
        for t in tokens
    ]

    solutions = product(*occurrences)
    solutions = [s for s in solutions if len(s) == len(tokens)]
    if not solutions:
        return []

    ranges = [
        (min(s, key=itemgetter(0)), max(s, key=itemgetter(0)), i)
        for i, s in enumerate(solutions)
    ]

    # Most compact range
    compact = min(ranges, key=lambda xs: xs[1][1] - xs[0][0])
    i = compact[2]
    return sorted(solutions[i], key=itemgetter(0))


# Function to find all spans containing the tokens
def spans_of_tokens_all(text, tokens):
    """
    Find all the spans containing the tokens.
    Returns a list of offsets [i,j]
    """
    # Exclude not present tokens
    text_lo = text.lower()
    tokens = [t for t in tokens if t.lower() in text_lo]
    if not tokens:
        return []

    occurrences = [
        [(m.start(), m.end()) for m in re.finditer(t, text, flags=re.IGNORECASE)]
        for t in tokens
    ]
    return chain.from_iterable(occurrences)
