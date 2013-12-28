#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib.request
import lxml.html
from lxml import etree
import re
from collections import defaultdict

OUTPUT_XML = 'PeriodicTable/src/main/res/raw/elements.xml'

URL_PREFIX = 'http://en.wikipedia.org'

def table_to_list(table):
    return list(iter_2d_dict(table_to_2d_dict(table)))

def table_to_2d_dict(table):
    result = defaultdict(lambda : defaultdict(str))
    rows = table.xpath('./tr')
    d_row = 0
    for row_i, row in enumerate(rows):
        if d_row != 0:
            d_row -= 1
            continue
        row_height = 0
        rowspan_i = 0
        for col_i, col in enumerate(row.xpath('./td')):
        	row_height = max(row_height, int(col.get('rowspan', 1)))
        for col_i, col in enumerate(row.xpath('./td')):
            colspan = int(col.get('colspan', 1))
            rowspan = int(col.get('rowspan', 1))
            col_data = col.text_content()
            while row_i in result and col_i in result[row_i]:
                col_i += 1
            if row_height > rowspan:
                height_i = 1
                row_j = 0
                while height_i < row_height:
                    cur_col = rows[row_i + row_j + 1].xpath('./td')[rowspan_i]
                    col_data += '\n' + cur_col.text_content()
                    height_i += int(cur_col.get('rowspan', 1))
                    row_j += 1
                rowspan_i += 1
                d_row = max(d_row, row_j)
            for j in range(col_i, col_i + colspan):
                result[row_i][j] = col_data if j == col_i else ''
    return result

def iter_2d_dict(dct):
    for i, row in sorted(dct.items()):
        cols = []
        for j, col in sorted(row.items()):
        	# Patch historic name
            if len(row.items()) > 10:
            	if j == 1:
            		continue
            cols.append(col)
        yield cols

def add_to_element(root, name, value):
    subelement = etree.SubElement(root, name)
    subelement.text = value

def fetch(url, root):
    content = lxml.html.fromstring(urllib.request.urlopen(url).read())

    # Properties

    nsm = content.xpath('//table[@class="infobox bordered"]/tr[th[contains(., "Name, ")]]/td/text()')[0].replace(",", "").split()

    saw = re.sub(r'\([0-9]?\)', '', content.xpath('//table[@class="infobox bordered"]/tr[th[a[contains(., "Standard atomic weight")]]]/td/text()')[0]).replace('(', '[').replace(')', ']')
    try:
        saw = format(float(saw), '.3f').rstrip('0').rstrip('.')
    except ValueError:
        pass

    cat = content.xpath('//table[@class="infobox bordered"]/tr[th[a[contains(., "Element category")]]]/td/a/text()')[0]

    pb = content.xpath('//table[@class="infobox bordered"]/tr[th[a[contains(., "Group")]]]/td/a/text()')
    grp = re.sub(r'[^0-9]', '', content.xpath('//table[@class="infobox bordered"]/tr[th[a[contains(., "Group")]]]/td/span/a/text()')[0].replace('n/a', '0'))

    # Isotopes

    content = lxml.html.fromstring(urllib.request.urlopen(URL_PREFIX + content.xpath('//table[@class="infobox bordered"]/tr/td/a[contains(., "Isotopes of ")]/@href')[0]).read())

    isotopes = table_to_list(content.xpath('//table[@class="wikitable"][@style="font-size:95%; white-space:nowrap"]')[0])

    # Add all the things to the tree

    element = etree.SubElement(root, 'element')
    element.attrib['number'] = nsm[2]

    add_to_element(element, 'symbol', nsm[1])
    add_to_element(element, 'name', nsm[0].capitalize())
    add_to_element(element, 'weight', saw)
    add_to_element(element, 'category', cat)
    add_to_element(element, 'group', grp)
    add_to_element(element, 'period', pb[0])
    add_to_element(element, 'block', pb[1])
    add_to_element(element, 'wiki', url)

    isotopes_tag = etree.SubElement(element, 'isotopes')

    for isotope in isotopes:
        isotope_tag = etree.SubElement(isotopes_tag, 'isotope')
        isotope_tag.attrib['symbol'] = re.sub('\[.+?\]\s*', '', isotope[0].replace(nsm[1].capitalize(), ''))
        add_to_element(isotope_tag, 'half-life', re.sub(r'\([^)]*\)', '', re.sub(r'\[.+?\]\s*', '', isotope[4].replace('Observationally ', '')).replace('#', '').lower()).replace('×10', '×10^'))
        add_to_element(isotope_tag, 'decay-modes', re.sub(r'\[.+?\]\s*', '', isotope[5].replace('#', '')).replace('×10', '×10^'))
        add_to_element(isotope_tag, 'daughter-isotopes', re.sub(r'\[.+?\]\s*', '', isotope[6]))
        add_to_element(isotope_tag, 'spin', isotope[7].replace('#', '').replace('(', '').replace(')', ''))
        add_to_element(isotope_tag, 'abundance', re.sub(r'\([^)]*\)', '', re.sub(r'\[.+?\]\s*', '', isotope[8].lower())).replace('×10', '×10^') if len(isotope) > 8 else '')

    print(list([nsm[0].capitalize(), nsm[1], nsm[2], saw, cat, grp, pb[0], pb[1]]))

if __name__ == '__main__':
    pages = lxml.html.fromstring(urllib.request.urlopen(URL_PREFIX + '/wiki/Periodic_table').read()).xpath('//table/tr/td/div[@title]/div/a/@href')

    root = etree.Element('elements')

    for page in pages:
        fetch(URL_PREFIX + page, root)

    with open(OUTPUT_XML, 'w+') as out_file:
        out_file.write(etree.tostring(root, encoding='utf-8', pretty_print=True, xml_declaration=True).decode('utf-8'));
