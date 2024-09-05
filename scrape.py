import requests
from bs4 import BeautifulSoup
import re
import json

def scrape_product_details(url: str) -> tuple[str | None, list[str], list[str], str | None]:
    """Scrapes product price, available sizes, out-of-stock sizes, and item code from a webpage.
    Args:
        url: The URL of the webpage to scrape.
    Returns:
        A tuple containing the product price, available sizes, out-of-stock sizes, and item code.
    """

    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find current price div
        price_div = soup.find('div', class_='product-price--original')
        price = price_div.text.strip() if price_div else None

        # Find original price div
        oldprice_div = soup.find ('div', class_='product-price--compare')
        oldprice = oldprice_div.text.strip() if oldprice_div else None

        # Find size options within select
        select_tag = soup.find('select')
        size_options = select_tag.find_all('option') if select_tag else []

        available_sizes = []
        out_of_stock_sizes = []
        for option in size_options:
            size = option.text.strip()
            if "/" in size:
                # Extract the part after the "/"
                size = size.split("/")[-1].strip()
            if "(Out of stock)" in size:
                # Remove "(Out of stock)" from the size text
                size = size.replace("(Out of stock)", "").strip()
                out_of_stock_sizes.append(size)
            else:
                available_sizes.append(size)

        # Find item code in ul within div;
        description_div = soup.find('div', class_='product-page--description')
        if description_div:
            ul_tag = description_div.find('ul')
            if ul_tag:
                item_code_element = ul_tag.find('li', string=re.compile(r'\bI\d{6}_[A-Z0-9]+_[A-Z0-9]+\b'))
                item_code = item_code_element.text.strip() if item_code_element else None

        if not item_code:
            json_ld_script = soup.find('script', type='application/ld+json')
            if json_ld_script:
                try:
                    # Parse JSON-LD content
                    json_ld_data = json.loads(json_ld_script.string.strip())
                    # Extract SKU from JSON-LD
                    if isinstance(json_ld_data, list):
                        for item in json_ld_data:
                            if '@type' in item and item['@type'] == 'Product':
                                item_code = item.get('sku')
                                break
                except json.JSONDecodeError:
                    print("Error decoding JSON-LD data.")

        return price, oldprice, available_sizes, out_of_stock_sizes, item_code
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None, [], [], None

# Example usage:
if __name__ == "__main__":
    url = "https://americanrag.ae/collections/carhartt-wip/products/sid-pant-lamar-for-mens"  # Replace with the actual URL
    price, oldprice, available_sizes, out_of_stock_sizes, item_code = scrape_product_details(url)

    if price and (available_sizes or out_of_stock_sizes):
        print("Current price:", price)
        print("Original price:", oldprice)
        print("Available sizes:", available_sizes)
        print("Out of stock sizes:", out_of_stock_sizes)
        print("Item code:", item_code)
    else:
        print("Product details not found.")