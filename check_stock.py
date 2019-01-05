import csv
import xmltodict as xml
import urllib.request
import json
from termcolor import colored

in_file = './in.csv'

store_ids = [215, 211]
country_code = 'us'
language_code = 'en'

availability_base_url = 'https://www.ikea.com/' + country_code + '/' + language_code +'/iows/catalog/availability/'
product_base_url = 'https://www.ikea.com/' + country_code + '/' + language_code + '/catalog/products/' 
product_url_suffix = '?version=v1&type=xml&dataset=normal,prices,parentCategories,allImages,attributes'

product_info = []
product_availability = []

'''
Reads the input CSV file

Returns: An array of dictionaries [{'id': '01234567', 'qty': 1, 'notes':'blah'}]
'''
def load_input_CSV():
    out = []
    with open(in_file) as csvFile:
        reader = csv.reader(csvFile, delimiter=',')

        for count, row in enumerate(reader):
            if count > 0:
                # Process the rows to a dict
                if row[1] == '':
                    qty = 1;
                else:
                    qty = int(row[1])
                this_item = {
                    "id": row[0].replace(".",""),
                    "qty": qty,
                    "notes": row[2]
                }

                out.append(this_item)

    return out


'''
Gets the product color, description, size, and price

Inputs:
    item_id string: The item id

Returns: A dict with the product info 
    e.g. {'item_id':'01234567', 'price':229.0, 'color':'white', 'description':'EXAMPLE product', 'size':'1x1 "'}
'''
def get_product_info(item_id):
    global product_info

    # If we already got info for this product, return it
    for prod in product_info:
        if prod['item_id'] == item_id:
            return prod

    url = product_base_url + item_id + product_url_suffix
    data = urllib.request.urlopen(url).read()
    data = xml.parse(data)
    # pretty_print(data)

    try:
        item = data['ir:ikea-rest']['products']['product']['items']['item']
    
        item_info = {}
        item_info['item_id'] = item_id

        # pricing
        item_info['price'] = float(item['prices']['normal']['priceNormal']['@unformatted'])

        # description
        item_info['color'] = item['attributesItems']['attributeItem'][0]['value']
        item_info['description'] = item['name'] + ' ' + item['facts']

        # size
        item_info['size'] = item['attributesItems']['attributeItem'][1]['value']

        print('Product', item_info['item_id'], item_info['description'])

        # Save for later
        product_info.append(item_info)

        return item_info
    except KeyError as e:
        try:
            error = data['ir:ikea-rest']['products']['error']
            errorcode = error['@code']
            errormsg = error['message']
            print(colored('Error: ' + errormsg + ', Code: ' + errorcode + ', Item: ' + item_id, 'red'))
        except:
            print(colored('Error: ' + e + ' for product: ' + item_id, 'red'))

        print(colored('Quitting.', 'red'))
        quit()

    
'''
For a specified product ID, gets stock info at the requested stores

Input:
    item_id string: The item ID

Returns: a list of dictionaries containing item availability
'''
def get_product_availability(item_id):
    global product_availability

    # If we already got info for this product, return it
    for prod in product_availability:
        if prod[0]['item_id'] == item_id:
            return prod

    url = availability_base_url + item_id
    data = urllib.request.urlopen(url).read()
    data = xml.parse(data)
    availability = data['ir:ikea-rest']['availability']['localStore']
    # pretty_print(availability)

    out = []

    for id in store_ids:
        for store in availability:
            if int(store['@buCode']) == id:
                store_dict = {}
                stock = store['stock']

                # basic availability info
                store_dict['store_id'] = id
                store_dict['item_id'] = item_id
                store_dict['available'] = int(stock['availableStock'])
                if store_dict['available'] == 0:
                    store_dict['restockDate'] = stock['restockDate']
                store_dict['probability'] = stock['inStockProbabilityCode']
                store_dict['isMultiProduct'] = str_to_bool(stock['isMultiProduct'])

                # item location(s)
                loc = stock['findItList']['findIt']
                locations = []
                if store_dict['isMultiProduct']:
                    for item in loc:
                        item_dict = get_item_location(item)
                        locations.append(item_dict)
                else:
                    item_dict = get_item_location(loc)
                    locations.append(item_dict)

                store_dict['locations'] = locations

                # forecast
                store_dict['forecast'] = stock['forecasts']['forcast']

                out.append(store_dict)

                # print the status to the terminal
                confcolor = color_confidence(store_dict['probability'])
                print('At store:', store_dict['store_id'], 'Qty:', colored(store_dict['available'], confcolor), 'In-Stock Confidence:', colored(store_dict['probability'], confcolor))
                if store_dict['available'] == 0:
                    print('Restock date:', store_dict['restockDate'])
                    print('Forecast:')
                    for f in store_dict['forecast']:
                        confcolor = color_confidence(f['inStockProbabilityCode'])
                        print(f['validDate'], 'Qty:', colored(f['availableStock'], confcolor), 'Confidence:', colored(f['inStockProbabilityCode'])) 

    # Save for later
    product_availability.append(out)

    return out


'''
Assigns Green/Yellow/Red colors to in-stock probability values

Input: The in-stock probability

Returns: A color for use by the colored library
'''
def color_confidence(probability):
    if probability == 'HIGH':
        return 'green'
    elif probability == 'MEDIUM':
        return 'yellow'
    else:
        return 'red'


'''
Gets an item's location within the store

Inputs: 
    item dict: The dictionary containing the item

Returns: A dict with the item location
'''
def get_item_location(item):
    item_dict = {}
    item_dict['partNumber'] = item['partNumber']
    item_dict['qty'] = int(item['quantity'])

    if item['type'] == 'BOX_SHELF':
        aisle = item['box']
        bin = item['shelf']
        item_dict['location'] = 'Warehouse ' + aisle + '-' + bin
    elif item['type'] == 'CONTACT_STAFF':
        item_dict['location'] = 'Contact Staff'
    elif item['type'] == 'SPECIALITY_SHOP':
        item_dict['location'] = item['specialityShop'] + ' Dept.'
    else:
        item_dict['location'] = item['type']
    
    return item_dict


'''
Converts a 'true' or 'false' string to boolean

Input:
    s: The string to convert

Returns: the boolean value
'''
def str_to_bool(s):
    if s == 'true':
         return True
    elif s == 'false':
         return False
    else:
         raise ValueError


'''
Pretty prints dictionaries

Input:
    data dict: The dictionary to pretty print
'''
def pretty_print(data):
    print(json.dumps(data, indent=1))


'''
Loads and parses all products

Returns [dict]: A list of products
'''
def load_parse_all_products():
    products = []
    items = load_input_CSV()
    for item in items:
        # Get product info
        product = {}
        product['id'] = item['id']
        product['qty_needed'] = item['qty']
        product['notes'] = item['notes']
        product['info'] = get_product_info(item['id'])
        product['availability'] = get_product_availability(item['id'])
        
        products.append(product)

    return products


'''
Computes the total price of the list

Inputs:
    products [dict]: The list of products

Returns float: The total price
'''
def calc_total_price(products):
    total_price = 0.0

    for prod in products:
        total_price = total_price + prod['info']['price'] * prod['qty_needed']

    return total_price


'''
Determines the in-stock probability for the entire list by store

Returns:
    The stock confidence for each store
'''
def get_stock_confidence(products):
    confidence = []
    for store in store_ids:
        store_dict = {}
        store_dict['id'] = store
        store_dict['confidence'] = 'HIGH'
        confidence.append(store_dict)

    for prod in products:
        for store in prod['availability']:
            store_id = store['store_id']
            probability = store['probability']

            if probability == 'LOW':
                for store in confidence:
                    if store['id'] == store_id:
                        store['confidence'] = 'LOW'
            elif confidence == 'MEDIUM':
                for store in confidence:
                    if store['id'] == store_id and store['confidence'] != 'LOW':
                        store['confidence'] = 'MEDIUM'

    return confidence


'''
Saves rows (list of lists) as a CSV file

Inputs: 
    filename string: The filename
    rows [[]]: The data to save
'''
def save_file(filename, rows):
    with open(filename, 'w', newline='') as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        for row in rows:
            wr.writerow(row)
    print('Saved file', filename)


'''
Gets product info and availability and exports to CSV files
'''
def save_product_availability(products):
    total_price = calc_total_price(products)
    stock_confidence = get_stock_confidence(products)
    # pretty_print(products)

    for store in store_ids:
        rows = []

        rows.append(['Store ID:', store])
        for con in stock_confidence:
            if con['id'] == store:
                confidence = con['confidence']
                break
        rows.append(['In-Stock Confidence', confidence])
        rows.append(['Total Price', total_price])
        rows.append(['\n'])

        rows.append(['Part Number', 'Description', 'Location', 'Qty Needed', 'Qty Available', 'In-Stock Confidence', 'Color', 'Size', 'Unit Price', 'Notes'])

        for prod in products:
            for avail in prod['availability']:
                if avail['store_id'] == store:
                    thisrow = []

                    if not avail['isMultiProduct']:
                        # Not a multi-part product
                        thisrow.append(prod['id'])
                        thisrow.append(prod['info']['description'])
                        thisrow.append(avail['locations'][0]['location'])
                        thisrow.append(avail['locations'][0]['qty'] * prod['qty_needed'])
                        thisrow.append(avail['available'])
                        thisrow.append(avail['probability'])
                        thisrow.append(prod['info']['color'])
                        thisrow.append(prod['info']['size'])
                        thisrow.append(prod['info']['price'])
                        thisrow.append(prod['notes'])
                        rows.append(thisrow)
                    else:
                        # Multi-part product
                        thisrow.append(prod['id'])
                        thisrow.append(prod['info']['description'])
                        thisrow.append('Multi-Part Product. See Below:')
                        thisrow.append(prod['qty_needed'])
                        thisrow.append(avail['available'])
                        thisrow.append(avail['probability'])
                        thisrow.append(prod['info']['color'])
                        thisrow.append(prod['info']['size'])
                        thisrow.append(prod['info']['price'])
                        thisrow.append(prod['notes'])
                        rows.append(thisrow)

                        for loc in avail['locations']:
                            info = get_product_info(loc['partNumber'])
                            avail = get_product_availability(loc['partNumber'])
                            for thisstore in avail:
                                if thisstore['store_id'] == store:
                                    avail = thisstore

                            thisrow = []
                            thisrow.append(loc['partNumber'])
                            thisrow.append(info['description'])
                            thisrow.append(loc['location'])
                            thisrow.append(prod['qty_needed']*int(loc['qty']))
                            thisrow.append(avail['available'])
                            thisrow.append(avail['probability'])
                            thisrow.append(info['color'])
                            thisrow.append(info['size'])
                            thisrow.append(info['price'])
                            thisrow.append('Part of ' + prod['id'])
                            rows.append(thisrow)

        save_file('out_' + str(store) + '.csv', rows)
    print(colored('Done.', 'green'))

products = load_parse_all_products()
save_product_availability(products)
