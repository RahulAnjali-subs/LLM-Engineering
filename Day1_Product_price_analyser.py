#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
import os
import openai
from flask import Flask, request, jsonify
from time import sleep

# Load API key from .env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI Client
openai.api_key = openai_api_key

# Initialize Flask App
app = Flask(__name__)

def scrape_product_prices_with_selenium(product_name):
    """
    Scrapes product prices from major e-commerce websites using Selenium to handle cookie popups.
    """
    ecommerce_sites = {
        "Coolblue": f"https://www.coolblue.be/en/search?query={product_name.replace(' ', '+')}",
        "Bol": f"https://www.bol.com/be/nl/s/?searchtext={product_name.replace(' ', '+')}",
        "Mediamarkt": f"https://www.mediamarkt.be/en/search.html?query={product_name.replace(' ', '+')}",
        "Amazon": f"https://www.amazon.be/s?k={product_name.replace(' ', '+')}",
        "Fnac": f"https://www.fnac.com/SearchResult/ResultList.aspx?Search={product_name.replace(' ', '+')}",
        "VandenBorre": f"https://www.vandenborre.be/fr/search?query={product_name.replace(' ', '+')}",
    }

    # Set up Chrome options to avoid running UI and detect bot
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode (without UI)
    chrome_options.add_argument("--disable-gpu")  # Disable GPU to avoid issues with headless mode

    # Set the path to the ChromeDriver executable
    chrome_driver_path = "path/to/chromedriver"  # Update with your actual ChromeDriver path

    # Create a Service object for the driver
    service = Service(chrome_driver_path)

    # Initialize the WebDriver using the Service object
    driver = webdriver.Chrome(service=service, options=chrome_options)

    results = {}

    for site, url in ecommerce_sites.items():
        try:
            print(f"Scraping {site}: {url}")
            driver.get(url)

            # Wait for the page to load completely
            sleep(3)

            # Handle cookie acceptance if it appears
            try:
                cookie_accept_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept')]")
                cookie_accept_button.click()
                sleep(1)  # Wait for the action to complete
            except Exception as e:
                print(f"No cookie popup for {site} or could not accept: {e}")

            # Scrape the price based on site-specific structure
            if site == "Coolblue":
                price_element = driver.find_element(By.CSS_SELECTOR, ".product-card--price .sales-price__current")
            elif site == "Bol":
                price_element = driver.find_element(By.CSS_SELECTOR, ".promo-price")
            elif site == "Mediamarkt":
                price_element = driver.find_element(By.CSS_SELECTOR, ".product-item__price")
            elif site == "Amazon":
                price_element = driver.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen")
            elif site == "Fnac":
                price_element = driver.find_element(By.CSS_SELECTOR, ".price-box .price")
            elif site == "VandenBorre":
                price_element = driver.find_element(By.CSS_SELECTOR, ".price__value")

            # Extract and store the price
            if price_element:
                price = price_element.text.strip()
                results[site] = {"price": price, "url": url}
            else:
                results[site] = {"price": "Price not found", "url": url}
        except Exception as e:
            print(f"Error scraping {site}: {e}")
            results[site] = {"price": "Site not reachable", "url": url}

    driver.quit()
    return results

def analyze_best_deal(product_name):
    """
    Uses OpenAI API to summarize the best deal from the scraped prices.
    """
    product_prices = scrape_product_prices_with_selenium(product_name)

    price_info_text = "\n".join(
        [f"{site}: {data['price']} ({data['url']})" for site, data in product_prices.items()]
    )

    prompt = f"""
    You are a price comparison assistant. Based on the following scraped data, summarize where the best deal is:

    {price_info_text}

    Recommend the best store to buy the product from.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You help users find the best deals online."},
                  {"role": "user", "content": prompt}]
    )

    return response.choices[0].message['content'], product_prices

@app.route("/get_best_deal", methods=["GET"])
def get_best_deal():
    """
    Flask endpoint to get the best deal for a product.
    Example request: /get_best_deal?product=iphone+15
    """
    product_name = request.args.get("product")
    if not product_name:
        return jsonify({"error": "Please provide a product name"}), 400

    best_deal_summary, product_prices = analyze_best_deal(product_name)

    # Prepare Markdown table for all the prices
    markdown_table = "| Website     | Price      | URL                                                                 |\n|-------------|------------|---------------------------------------------------------------------|\n"
    for site, data in product_prices.items():
        markdown_table += f"| {site} | {data['price']} | {data['url']} |\n"

    return jsonify({
        "product": product_name,
        "best_deal": best_deal_summary,
        "price_comparison_table": markdown_table
    })

if __name__ == "__main__":
    app.run(debug=True)

