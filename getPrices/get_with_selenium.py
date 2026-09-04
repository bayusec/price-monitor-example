import json
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.common.by import By

import tools.request_tools as request_tools
from classes.store_class import Store
from classes.product_class import Product
from slugify import slugify
from methods.compare_prices import compare_prices
from config.loggin_config import logger
from config.app_config import BYPASS_CONFIG, BYPASS_COOKIE, STORE_MAX_WORKERS
from decimal import Decimal, ROUND_DOWN
from classes.SeleniumSession import SeleniumSession

sesion = requests.session()
headers = request_tools.generic_headers
# PRODUCT INSTANCE
product_instance = Product()
# GETTING THE LINKS FROM ****
store = {"slug": "****"}
store_instance = Store(store)
dbSubcatLinks = store_instance.get_subcategories()
store_id = dbSubcatLinks[0]['store_id']
store["id"] = store_id
URL_BASE = dbSubcatLinks[0]['base_url'].replace('****', '********') #BYPASS
brands = product_instance.get_brands()

if BYPASS_CONFIG[store['slug']]:
    headers["Cookie"] = BYPASS_COOKIE


def parse_price(price):
    return Decimal(price).quantize(Decimal('0.01'), rounding=ROUND_DOWN)


def selenium_request(url, wait_for="****", ajax=False, ajax_url=None):
    with SeleniumSession() as sel_session:
        html_response = sel_session.get_page(url, wait_for=wait_for, by=By.CSS_SELECTOR)
        if not ajax_url:
            return html_response
        else:
            for request in sel_session.get_driver().requests:
                if request.response and ajax_url in request.url:
                    return sel_session.decode_response_body(request.response)
            # logger.info(sel_session.get_driver().requests)
            return None


def get_pages_number(json_response):
    doc = json.loads(json_response)
    try:
        ulPages = int(doc['pagination']['totalPages'])
        return ulPages
    except Exception as e:
        logger.error(f"error al obtener numero de paginas")
        sys.exit()



def fetch_product_details(response, subcat_id):
    full_products = {}
    doc_products = json.loads(response)
    for prod in doc_products["products"]:
        prod_id = prod["***"]
        product = {"product_id": prod_id,
                   "subcat_id": subcat_id,
                   "link": f"{URL_BASE}/{prod_id}",
                   "store_id": store_id}
        parsed_product = parse_product(prod)
        product.update(parsed_product["details"])
        product["attrs"] = parsed_product["attrs"]
        full_products[prod_id] = product

    return full_products


def parse_product(body_product):
    product_detail = {}
    sku = None
    prices = body_product["prices"]
    product_detail['store_price'] = parse_price(prices.get("***", 0))
    product_detail['internet_price'] = parse_price(prices.get("***", 0))
    product_detail['regular_price'] = parse_price(prices.get("***", 0))

    if product_detail['store_price'] == 0:
        if product_detail['internet_price'] == 0:
            product_detail['store_price'] = product_detail['regular_price']
        else:
            product_detail['store_price'] = product_detail['internet_price']

    product_detail['actual_price'] = product_detail['store_price']
    product_detail['payment_store'] = True if product_detail['store_price'] else False
    product_detail['stock'] = True

    product_detail['brand'] = slugify(body_product["***"])
    product_detail['name'] = body_product["***"]
    product_detail['preview_url'] = body_product["***"][0] if body_product["***"][0] else ""
    product_detail['product_link'] = ""

    # get sku from json ("Modelo")
    for attr_modelo in body_product["***"][0]["***"]:
        if attr_modelo["***"] == "modelo":
            sku = attr_modelo["Values"][0]["values"]

    if not sku:
        sku = None
    brand = product_detail['***']
    if brand not in brands:
        brand_id = product_instance.save_brand(brand)
    else:
        brand_id = brands[brand]

    product_detail['brand_id'] = brand_id
    product_detail['sku'] = sku
    parsed_product = {"details": product_detail, "attrs": {}}
    for attr in body_product["***"][0]["***"]:
        parsed_product['attrs'][slugify(attr['identifier'])] = attr["Values"][0]["values"]

    return parsed_product


def process_subcat(subcat_links):
    for link in subcat_links:
        subcat_id = link['subcat_id']
        num_pages = 1
        subcat_link = link['link'].replace('*********', '*********')
        logger.info(subcat_link)

        try:
            first_response = selenium_request(subcat_link, wait_for="*********", ajax=True, ajax_url="api/*********/*********")

            num_pages = get_pages_number(first_response)
            page_urls = [f"{subcat_link}?page={page}&**=**&**=**" for page in range(2, num_pages + 1)]
            print(f"Páginas detectadas: {num_pages}")

            full_products = fetch_product_details(first_response, subcat_id)
            compare_prices(full_products, store, subcat_id)

            if num_pages > 1:
                with ThreadPoolExecutor(max_workers=STORE_MAX_WORKERS.****) as executor:
                    future_to_url = {executor.submit(selenium_request, url, wait_for="**", ajax=True, ajax_url="api/********/******"): url for url in page_urls}
                    for future in as_completed(future_to_url):
                        url = future_to_url[future]
                        try:
                            response = future.result()
                            if response:
                                product_data = fetch_product_details(response, subcat_id)
                                compare_prices(product_data, store, subcat_id)
                        except Exception as e:
                            logger.error(f"Error processing {url}: {e}")
        except Exception as e:
            print(e)


if __name__ == "__main__":    
    store_instance.disable_products(store_id)
    process_subcat(dbSubcatLinks)

    