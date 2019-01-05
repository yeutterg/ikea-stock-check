import sys
import json

# Get the command line argument. Default to 'us' if no parameter specified
try:
    loc = sys.argv[1]
except:
    loc = 'us'

print('Getting stores in:', loc)

#Open the JSON file
with open('stores.json') as f:
    data = json.load(f)

    # Print all stores that match the country code
    count = 0
    for i in data:
        if i['countryCode'] == loc:
            print(i['name'] + ': ' + i['buCode'])
            count = count + 1

    print('Found', count, 'stores')
    if count == 0:
        print('Check your country code by looking at the Ikea URL of your target country')
        print('For example, in the U.S. the URL is https://www.ikea.com/us/en/ and the country code is \'us\'')