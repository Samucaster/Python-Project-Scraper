import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
import os
from datetime import datetime

def scrape_product_details(url: str) -> dict:
    """Scrapes product price, available sizes, out-of-stock sizes, and item code from a product webpage.
    Args:
        url: The URL of the product webpage to scrape.
    Returns:
        A dictionary containing the product URL, price, available sizes, out-of-stock sizes, and item code.
    """
    data = {
        'Product URL': url,
        'Price': None,
        'Available Sizes': None,
        'Out of Stock Sizes': None,
        'Item Code': None
    }

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find price div
        price_div = soup.find('div', class_='product-price--original')
        data['Price'] = price_div.text.strip() if price_div else None

        # Find size options within select
        select_tag = soup.find('select')
        size_options = select_tag.find_all('option') if select_tag else []

        available_sizes = []
        out_of_stock_sizes = []
        for option in size_options:
            size = option.text.strip()
            if "/" in size:
                size = size.split("/", 1)[-1].strip()  # Use part after the first "/"
            if "(Out of stock)" in size:
                size = size.replace("(Out of stock)", "").strip()
                out_of_stock_sizes.append(size)
            else:
                available_sizes.append(size)
        
        data['Available Sizes'] = ', '.join(available_sizes)
        data['Out of Stock Sizes'] = ', '.join(out_of_stock_sizes)

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
        
        data['Item Code'] = item_code

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

    return data

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

        # Find <a> tags with href starting with "collections/carhartt-wip/products/"
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith("/collections/carhartt-wip/products/"):
                product_url = base_url + href
                # Scrape product details for each URL
                print(f"Scraping product details from: {product_url}")
                product_data = scrape_product_details(product_url)
                all_product_data.append(product_data)
                print(f"Product URL: {product_url}")
                print(f"Price: {product_data['Price']}")
                print(f"Available Sizes: {product_data['Available Sizes']}")
                print(f"Out of Stock Sizes: {product_data['Out of Stock Sizes']}")
                print(f"Item Code: {product_data['Item Code']}")
                print("-" * 40)

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

    # Ensure output directory exists
    output_dir = 'Output-carhartt'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'product_details_{timestamp}.xlsx')
    
    # Export to Excel
    df = pd.DataFrame(all_product_data)
    df.to_excel(output_file, index=False)

# Example usage:
if __name__ == "__main__":
    main_url = "https://americanrag.ae/collections/carhartt-wip"  # Replace with the actual URL
    scrape_main_page(main_url)