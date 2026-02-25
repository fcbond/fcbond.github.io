"""
bib2html.py  –  BibTeX → HTML bibliography for Flask-Frozen
============================================================

Parses .bib files (including an abbreviation file) and renders a
bibliography as HTML matching the style of Bond's current pubs.html.

Requirements:
    pip install bibtexparser>=2.0

Usage (standalone test):
    python bib2html.py abb.bib mtg.bib

Flask integration:
    from bib2html import load_bibliography, render_bibliography

    # Load once at startup
    entries = load_bibliography('static/abb.bib', 'static/mtg.bib')

    # Personal page – only entries where Bond is an author
    html = render_bibliography(entries, author_filter='Bond')

    # Group page – all entries where Bond is an author or co-author
    # (same call, or pass author_filter=None for truly all entries)
    html = render_bibliography(entries)

    # In your Jinja2 template: {{ bib_html | safe }}
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

import bibtexparser
from bibtexparser.middlewares import (
    MonthIntMiddleware,
    LatexDecodingMiddleware,
)


# ---------------------------------------------------------------------------
# 1.  Loading
# ---------------------------------------------------------------------------

def load_bibliography(*bib_paths: str) -> list[dict]:
    """
    Parse one or more .bib files (pass the abbreviation file first).
    Returns a list of entry dicts with lower-cased field names.
    @String entries are resolved automatically.
    """
    # Concatenate all bib files (abb file first) so @string macros resolve
    # across files in a single parse pass.
    combined = '\n'.join(
        Path(p).read_text(encoding='utf-8', errors='replace') for p in bib_paths
    )

    # The default parse stack already includes ResolveStringReferencesMiddleware
    # and RemoveEnclosingMiddleware; append the extra transforms we need.
    library = bibtexparser.parse_string(
        combined,
        append_middleware=[LatexDecodingMiddleware(), MonthIntMiddleware()],
    )

    entries = []
    for entry in library.entries:
        d = {'_type': entry.entry_type.lower(), '_key': entry.key}
        for field in entry.fields:
            d[field.key.lower()] = str(field.value) if field.value is not None else ''
        entries.append(d)

    # Resolve crossref fields: inherit missing fields from the parent entry
    entry_map = {e['_key']: e for e in entries}
    for e in entries:
        xref_key = e.get('crossref', '').strip()
        if not xref_key:
            continue
        parent = entry_map.get(xref_key)
        if not parent:
            continue
        for field, value in parent.items():
            if field.startswith('_'):
                continue
            if not e.get(field):   # only fill in what the child is missing
                e[field] = value

    return entries


# ---------------------------------------------------------------------------
# 2.  Author / name handling
# ---------------------------------------------------------------------------

def _parse_names(name_str: str) -> list[str]:
    """Split an author/editor string on ' and ' (case-insensitive)."""
    parts = re.split(r'\s+and\s+', name_str, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def _format_name(name: str) -> str:
    """
    Convert a name to 'Firstname Lastname' display form.
    Handles both 'Lastname, Firstname [von]' and 'Firstname Lastname' input.
    """
    name = name.strip()
    if ',' in name:
        parts = name.split(',', 1)
        last = parts[0].strip()
        first = parts[1].strip()
        return f'{first} {last}'
    return name


def _format_name_list(name_str: str) -> str:
    """Format a full author/editor string as 'A, B, C, and D'."""
    names = _parse_names(name_str)
    formatted = [_format_name(n) for n in names]
    if len(formatted) == 0:
        return ''
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f'{formatted[0]} and {formatted[1]}'
    return ', '.join(formatted[:-1]) + ', and ' + formatted[-1]


def _author_matches(name_str: str, filter_str: str) -> bool:
    """Return True if filter_str appears anywhere in name_str (case-insensitive)."""
    return filter_str.lower() in name_str.lower()


# ---------------------------------------------------------------------------
# 3.  Field helpers
# ---------------------------------------------------------------------------

def _get(entry: dict, *keys: str, default: str = '') -> str:
    for k in keys:
        v = entry.get(k, '').strip()
        if v:
            return v
    return default


def _pages(entry: dict) -> str:
    p = _get(entry, 'pages')
    if not p:
        return ''
    p = re.sub(r'\s*-{1,2}\s*', '–', p)
    return f'pp.&nbsp;{p}'


def _doi_link(doi: str) -> str:
    if not doi:
        return ''
    doi = doi.strip()
    if doi.startswith('http'):
        url = doi
        display = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    else:
        url = f'https://doi.org/{doi}'
        display = doi
    return f'DOI: <a href="{url}">{display}</a>'


# ---------------------------------------------------------------------------
# 4.  Venue rendering per entry type
# ---------------------------------------------------------------------------

def _venue_html(entry: dict) -> str:
    """Build the venue/source HTML for one entry."""
    etype     = entry.get('_type', '')
    url       = _get(entry, 'url')
    doi       = _get(entry, 'doi')
    booktitle = _get(entry, 'booktitle')
    journal   = _get(entry, 'journal')
    publisher = _get(entry, 'publisher')
    school    = _get(entry, 'school')
    series    = _get(entry, 'series')
    volume    = _get(entry, 'volume')
    number    = _get(entry, 'number')
    address   = _get(entry, 'address')
    isbn      = _get(entry, 'isbn')
    note      = _get(entry, 'note')
    editor    = _get(entry, 'editor')
    pages     = _pages(entry)

    venue = ''

    if etype in ('inproceedings',):
        if booktitle:
            venue = f'In <i>{booktitle}</i>'
        if address:
            venue += f', {address}'
        if pages:
            venue += f', {pages}'

    elif etype in ('article',):
        if journal:
            j = f'<i>{journal}</i>'
            if volume:
                j += f' <b>{volume}</b>'
                if number:
                    j += f'({number})'
            venue = j
        if pages:
            venue += (', ' if venue else '') + pages

    elif etype in ('book',):
        parts = []
        if series:
            parts.append(series)
        if publisher:
            parts.append(publisher)
        if address:
            parts.append(address)
        if isbn:
            parts.append(f'ISBN {isbn}')
        venue = '. '.join(parts)

    elif etype in ('incollection', 'inbook'):
        parts = []
        if editor:
            parts.append(f'In {_format_name_list(editor)} (ed.),')
        if booktitle:
            parts.append(f'<i>{booktitle}</i>')
        if publisher:
            parts.append(publisher)
        if pages:
            parts.append(pages)
        venue = ' '.join(parts)

    elif etype in ('phdthesis', 'masterthesis', 'mastersthesis'):
        label = 'PhD thesis' if 'phd' in etype else "Master's thesis"
        venue = label
        if school:
            venue += f', {school}'

    elif etype in ('techreport',):
        inst = _get(entry, 'institution')
        num  = _get(entry, 'number')
        venue = 'Technical Report'
        if num:
            venue += f' {num}'
        if inst:
            venue += f', {inst}'

    elif etype in ('proceedings',):
        parts = []
        if publisher:
            parts.append(publisher)
        if address:
            parts.append(address)
        if isbn:
            parts.append(f'ISBN {isbn}')
        venue = ', '.join(parts)

    else:  # unpublished, misc, …
        venue = note or ''

    # Append links
    links = []
    if url:
        if 'aclanthology' in url or 'aclweb.org/anthology' in url:
            links.append(f'<a href="{url}">ACL Anthology</a>')
        else:
            links.append(f'<a href="{url}">{url}</a>')
    if doi:
        links.append(_doi_link(doi))

    if links:
        sep = '. ' if venue and not venue.endswith('.') else (' ' if venue else '')
        venue = venue + sep + '; '.join(links)

    # Append note if not already incorporated
    if note and note not in venue:
        venue += f' ({note})'

    return venue.strip()


# ---------------------------------------------------------------------------
# 5.  Single-entry rendering
# ---------------------------------------------------------------------------

def _render_entry(entry: dict) -> str:
    """Render a single bib entry as a styled <div>."""
    key    = entry.get('_key', '')
    year   = _get(entry, 'year')
    title  = _get(entry, 'title')
    url    = _get(entry, 'url')
    author = _get(entry, 'author')
    editor = _get(entry, 'editor')

    # Person line: prefer author, fall back to editor
    person_raw = author or editor
    role_suffix = ' (eds)' if (not author and editor) else ''
    person_str = (_format_name_list(person_raw) + role_suffix) if person_raw else 'Unknown'

    # Title element: linked if URL present, slightly larger via CSS
    if url:
        title_el = f'<a class="bib-title" href="{url}">{title}</a>'
    else:
        title_el = f'<span class="bib-title">{title}</span>'

    id_attr = f' id="{key}"' if key else ''
    person_year = f'{person_str} ({year}).'
    venue = _venue_html(entry)
    return (
        f'<div class="bib-entry"{id_attr}>\n'
        f'  <span class="bib-meta">{person_year}</span>\n'
        f'  {title_el}.\n'
        + (f'  <span class="bib-venue">{venue}</span>\n' if venue else '')
        + f'</div>'
    )


# ---------------------------------------------------------------------------
# 6.  Full bibliography
# ---------------------------------------------------------------------------

def render_bibliography(
    entries: list[dict],
    author_filter: Optional[str] = None,
) -> str:
    """
    Render a complete bibliography as an HTML fragment.

    Parameters
    ----------
    entries       : output of load_bibliography()
    author_filter : if given (e.g. 'Bond'), only include entries where this
                    string appears in the author or editor field.

    Returns
    -------
    HTML string ready to embed in a Jinja2 template with {{ bib_html | safe }}.
    """
    if author_filter:
        visible = [
            e for e in entries
            if _author_matches(_get(e, 'author', 'editor'), author_filter)
        ]
    else:
        visible = list(entries)

    # Group by year
    by_year: dict[str, list[dict]] = defaultdict(list)
    for e in visible:
        year = _get(e, 'year', default='undated')
        by_year[year].append(e)

    years = sorted(
        by_year.keys(),
        reverse=True,
        key=lambda y: int(y) if y.isdigit() else 0,
    )

    # Navigation bar: one row per decade, most recent first
    nav_years = [y for y in years if y.isdigit()]
    from collections import defaultdict as _dd
    by_decade: dict[int, list[str]] = _dd(list)
    for y in nav_years:
        by_decade[(int(y) // 10) * 10].append(y)
    decades = sorted(by_decade.keys(), reverse=True)
    row_strs = []
    for decade in decades:
        row = by_decade[decade]   # already sorted descending within decade
        row_strs.append(' · '.join(f'<a href="#{y}">{y}</a>' for y in row))
    nav_html = (
        '<p class="bib-nav">\n  '
        + '\n  <br>\n  '.join(row_strs)
        + '\n</p>'
    )

    # Year sections
    sections = []
    for year in years:
        label = year if year != 'undated' else 'Undated'
        body = '\n\n'.join(_render_entry(e) for e in by_year[year])
        sections.append(
            f'<h3 id="{label}">{label}</h3>\n<div class="bib-section">\n\n{body}\n\n</div>'
        )

    return nav_html + '\n\n<hr>\n\n' + '\n\n\n'.join(sections)


# ---------------------------------------------------------------------------
# 7.  CLI / smoke test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python bib2html.py [abb.bib] main.bib')
        sys.exit(1)

    paths = sys.argv[1:]
    print(f'Loading: {paths}')
    all_entries = load_bibliography(*paths)
    print(f'Loaded {len(all_entries)} entries.')

    html_all  = render_bibliography(all_entries)
    html_bond = render_bibliography(all_entries, author_filter='Bond')

    Path('bib_all.html').write_text(html_all,  encoding='utf-8')
    Path('bib_bond.html').write_text(html_bond, encoding='utf-8')
    print(f'Written bib_all.html and bib_bond.html.')
    print(f'  All entries  : {html_all.count("<dt>"):4d} items')
    print(f'  Bond entries : {html_bond.count("<dt>"):4d} items')
