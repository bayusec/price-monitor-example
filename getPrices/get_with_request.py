import requests
import tools.request_tools as request_tools
from classes.store_class import Store
from classes.product_class import Product
from methods.compare_prices import compare_prices
from config.loggin_config import logger
from config.app_config import BYPASS_CONFIG, BYPASS_COOKIE
from decimal import Decimal
from bs4 import BeautifulSoup

sesion = requests.session()
headers = request_tools.generic_headers

# PRODUCT INSTANCE
product_instance = Product()
# GETTING THE LINKS FROM ***
store = {"slug": "***"}
store_instance = Store(store)
dbSubcatLinks = store_instance.get_subcategories()
store_id = dbSubcatLinks[0]['store_id']
store["id"] = store_id
URL_BASE = dbSubcatLinks[0]['base_url']
brands = product_instance.get_brands()

if store['slug'] in BYPASS_CONFIG:
    headers["Cookie"] = BYPASS_COOKIE


def fetch_products(response, subcat_id):
    full_products = {}
    doc = BeautifulSoup(response.text, "lxml")

    html_products = doc.findAll("div", {"class": "CSS_SELECTOR"})

    try:
        for prod in html_products:
            prod_id = prod["data-pid"]
            product = {"product_id": prod_id,
                       "subcat_id": subcat_id,
                       "link": f"{URL_BASE}{prod_id}.html",
                       "store_id": store_id}
            try:
               parsed_product = parse_product(prod)
            except Exception as e:
                logger.error(f"Error parsing product {prod_id}: {e}")
                continue

            if parsed_product:
                product.update(parsed_product["details"])
                product["attrs"] = parsed_product["attrs"]
                full_products[prod_id] = product
            else:
                continue

        return full_products
    except Exception as e:
        logger.error(f"Error getting grid with products: {e}")
        return False


def parse_product(product):
    product_detail = {}
    sku = None
    id_prod = product['data-pid']

    div_title_link = product.find("a", {"class": "link"})

    if (p := product.select_one("******")) and (span := p.find("span", class_="****")):
        store_price = span.get("data-value", 0)
    else:
        store_price = 0

    if (p := product.select_one("******")) and (span := p.find("span", class_="******")):
        internet_price = span.get("data-value", 0)
    else:
        internet_price = 0

    if (p := product.select_one("******")) and (span := p.find("span", class_="******")):
        regular_price = span.get("data-value", 0)
    else:
        regular_price = 0


    product_detail['store_price'] = Decimal(store_price)
    product_detail['internet_price'] = Decimal(internet_price)
    product_detail['regular_price'] = Decimal(regular_price)

    if product_detail['store_price'] == 0:
        if product_detail['internet_price'] == 0:
            product_detail['store_price'] = product_detail['regular_price']
        else:
            product_detail['store_price'] = product_detail['internet_price']

    if product_detail['store_price'] == 0:
        return False

    product_detail['actual_price'] = Decimal(0)
    product_detail['payment_store'] = ""
    product_detail['stock'] = True
    product_detail['brand'] = "Generic Brand"
    product_detail['name'] = "Product Name Placeholder"
    product_detail['preview_url'] = ""
    product_detail['product_link'] = f"{URL_BASE}{id_prod}.html"
    product_detail['sku'] = id_prod

    brand = product_detail['brand']
    if brand not in brands:
        brand_id = product_instance.save_brand(brand)
    else:
        brand_id = brands[brand]

    product_detail['brand_id'] = brand_id
    parsed_product = {"details": product_detail, "attrs": {}}
    return parsed_product


def request_page(link):
    response = sesion.get(link, headers=headers)
    return response


def process_subcat(subcat_links):
    for link in subcat_links:
        subcat_id = link['subcat_id']
        subcat_link = link['link']

        response = request_page(subcat_link)
        parsed_products = fetch_products(response, subcat_id)
        if parsed_products:
            compare_prices(parsed_products, store, subcat_id)
        else:
            print(subcat_link)
            continue


if __name__ == "__main__":
    store_instance.disable_products(store_id)
    full_products = []
    process_subcat(dbSubcatLinks)
