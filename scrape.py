import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
import os
from datetime import datetime

def scrape_product_details(url: str, item_name: str) -> list:
    """Scrapes product details from a product webpage and returns separate entries for each color.
    Args:
        url: The URL of the product webpage to scrape.
        item_name: The name of the item extracted from aria-label.
    Returns:
        A list of dictionaries, each containing details for a specific color.
    """
    product_entries = []

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find price div
        price_div = soup.find('div', class_='product-price--original')
        price = price_div.text.strip() if price_div else None

        #Find original price div
        oldprice_div = soup.find('div', class_='product-price--compare')
        oldprice = oldprice_div.text.strip() if oldprice_div else none

        #calculate discount
        oldprice_num = float(oldprice.replace("AED. ", ""))
        price_num = float(price.replace("AED. ", ""))
        calc = (1 - price_num/oldprice_num) * 100
        disc = str(round(calc,2))



        # Find item colors in the page
        color_labels = soup.find_all('label', {'for': lambda x: x and 'main-color' in x})
        item_colors = [label.find('div').text.strip() for label in color_labels] if color_labels else []

        # Find size options within select
        select_tag = soup.find('select')
        size_options = select_tag.find_all('option') if select_tag else []

        for item_color in item_colors:
            available_sizes = []
            out_of_stock_sizes = []

            for option in size_options:
                size = option.text.strip()
                if item_color in size:
                    size = size.replace(item_color, "").strip()  # Remove item color
                    if "/" in size:
                        size = size.split("/", 1)[-1].strip()  # Use part after the first "/"
                
                    if "(Out of stock)" in size:
                        size = size.replace("(Out of stock)", "").strip()
                        out_of_stock_sizes.append(size)
                    else:
                        available_sizes.append(size)

            # Create a dictionary entry for each color
            product_entries.append({
                'Product URL': url,
                'Item Name': item_name,
                'Item Code': None,
                'Item Color': item_color,
                'Price': price,
                'Original Price': oldprice,
                'Discount': disc,
                'Available Sizes': ', '.join(available_sizes),
                'Out of Stock Sizes': ', '.join(out_of_stock_sizes)
            })

        # Find item code in ul within product-page--description div
        item_code = None
        description_div = soup.find('div', class_='product-page--description')
        if description_div:
            ul_tag = description_div.find('ul')
            if ul_tag:
                item_code_element = ul_tag.find('li', string=re.compile(r'\bI\d{6}_[A-Z0-9]+_[A-Z0-9]+\b'))
                item_code = item_code_element.text.strip() if item_code_element else None

        # If item code was not found in the <ul>, check the JSON-LD script
        if not item_code:
            json_ld_script = soup.find('script', type='application/ld+json')
            if json_ld_script:
                try:
                    json_ld_data = json.loads(json_ld_script.string.strip())
                    if isinstance(json_ld_data, list):
                        for item in json_ld_data:
                            if '@type' in item and item['@type'] == 'Product':
                                item_code = item.get('sku')
                                break
                except json.JSONDecodeError:
                    print("Error decoding JSON-LD data.")
        
        # Update all entries with the item code
        for entry in product_entries:
            entry['Item Code'] = item_code

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

    return product_entries

def scrape_main_page(url: str):
    """Scrapes the main page for product URLs and then scrapes each product, exporting data to an Excel file.
    Args:
        url: The URL of the main page to scrape.
    """
    all_product_data = []
    base_url = "https://americanrag.ae"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Parse <a> tags with href containing "collections/carhartt-wip/products/"
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith("/collections/carhartt-wip/products/"):
                product_url = base_url + href
                item_name = a_tag.get('aria-label', 'Unknown Item Name')  # Get aria-label for item name
                # Scrape product details for each URL
                print(f"Scraping product details from: {product_url}")
                product_data_entries = scrape_product_details(product_url, item_name)
                all_product_data.extend(product_data_entries)
                for product_data in product_data_entries:
                    print(f"Product URL: {product_data['Product URL']}")
                    print(f"Item Name: {product_data['Item Name']}")
                    print(f"Item Code: {product_data['Item Code']}")
                    print(f"Item Color: {product_data['Item Color']}")
                    print(f"Price: {product_data['Price']}")
                    print(f"Original Price: {product_data['Original Price']}")
                    print(f"Discount percent:  {product_data['Discount']}")
                    print(f"Available Sizes: {product_data['Available Sizes']}")
                    print(f"Out of Stock Sizes: {product_data['Out of Stock Sizes']}")
                    
                    print("-" * 40)

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

    # Ensure output directory exists
    output_dir = 'Output-Carhartt WIP'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'{timestamp}_CA04830_Carhartt_WIP_stock.xlsx')
    
    # Export to Excel
    df = pd.DataFrame(all_product_data)
    df.to_excel(output_file, index=False)

# Parse collection page for Carhartt in americanrag.ae website
if __name__ == "__main__":
    main_url = "https://americanrag.ae/collections/carhartt-wip"  # current collection page - check for updates
    scrape_main_page(main_url)
