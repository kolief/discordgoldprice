import json
import cloudscraper
import datetime
import time

DISCORD_WEBHOOK_URL = "YOUR DISCORD WEBHOOK URL HERE"

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0'

scraper = cloudscraper.create_scraper()


def fetch_api_data(api_url, original_page_url):
    """Fetches JSON data from the API endpoint using cloudscraper."""
    headers = {
        'User-Agent': DEFAULT_USER_AGENT,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': original_page_url 
    }
    print(f"Fetching API data from: {api_url} with Referer: {original_page_url}")
    try:
        response = scraper.get(api_url, headers=headers)
        response.raise_for_status() 
        return response.json()
    except Exception as e: 
        print(f"Error fetching API data from {api_url}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}...")
        return None

def parse_api_data(json_data, page_type):
    """Parses JSON data to extract merchant names, prices, and stock."""
    if not json_data or not json_data.get("success") or not isinstance(json_data.get("data"), list):
        print(f"Invalid or unsuccessful API response for {page_type}: {str(json_data)[:200]}...")
        return []

    merchants_data = []
    for item in json_data["data"]:
        try:
            merchant_name = item.get('seller_id')
            price_info = item.get('gold')
            price_value_str = None
            stock_value = None 

            if price_info:
                if 'price' in price_info and price_info['price'] is not None:
                    price_value_str = str(price_info['price']) 
                if 'stock' in price_info and price_info['stock'] is not None:
                    try:
                        stock_value = int(price_info['stock'])
                    except (ValueError, TypeError):
                        stock_value = None 

            if merchant_name and price_value_str:
                price_value_float = float(price_value_str)
                formatted_price = f"${price_value_float:.4f}" 
                
                data_entry = {
                    'name': merchant_name, 
                    'price_float': price_value_float, 
                    'price_str': formatted_price, 
                    'type': page_type
                }
                if stock_value is not None:
                    data_entry['stock'] = stock_value
                
                merchants_data.append(data_entry)
            else:
                print(f"Skipping item due to missing merchant_name or price_value_str: Name={merchant_name}, PriceStr={price_value_str}")
        except ValueError:
            print(f"Error converting price/stock for item {str(item)[:100]}... Price string was: '{price_value_str}'")
        except Exception as e:
            print(f"An unexpected error occurred while parsing item {str(item)[:100]}...: {e}")
            
    return merchants_data

def send_to_discord(buy_list, sell_list, webhook_url):
    """Sends combined buy and sell data to a Discord webhook in a formatted embed.""" 

    if not webhook_url or webhook_url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        print("Discord webhook URL is not configured. Skipping sending message.")
        print("Buy Offers:")
        for item in buy_list: 
            stock_info_str = f" | {item['stock']}M" if 'stock' in item else ""
            print(f"  - {item['name']}: {item['price_str']}/M{stock_info_str}")
        print("Sell Offers:")
        for item in sell_list: 
            stock_info_str = f" | {item['stock']}M" if 'stock' in item else ""
            print(f"  - {item['name']}: {item['price_str']}/M{stock_info_str}")
        return

    embed_fields = []

    # Sort data
    if buy_list:
        buy_list.sort(key=lambda x: x['price_float'])
        best_buy = buy_list[0]
        embed_fields.append({
            "name": "💰 Best Buy Price", 
            "value": f"{best_buy['price_str']}/M by `{best_buy['name']}`", 
            "inline": False
        })

        top_buy_merchants_str = ""
        for i, merchant in enumerate(buy_list[:5]): 
            stock_info_formatted = f" | `{merchant['stock']}M`" if merchant.get('stock') is not None else ""
            top_buy_merchants_str += f"{i+1}) `{merchant['name']}` | `{merchant['price_str']}/M`{stock_info_formatted}\n"
        if top_buy_merchants_str:
            embed_fields.append({"name": "🏪 Top Buy Merchants", "value": top_buy_merchants_str.strip(), "inline": False})

    if sell_list:
        sell_list.sort(key=lambda x: x['price_float'], reverse=True)
        best_sell = sell_list[0]
        embed_fields.append({
            "name": "💵 Best Sell Price", 
            "value": f"{best_sell['price_str']}/M by `{best_sell['name']}`", 
            "inline": False
        })
        
        top_sell_merchants_str = ""
        for i, merchant in enumerate(sell_list[:5]): 
            stock_info_formatted = f" | `{merchant['stock']}M`" if merchant.get('stock') is not None else ""
            top_sell_merchants_str += f"{i+1}) `{merchant['name']}` | `{merchant['price_str']}/M`{stock_info_formatted}\n"
        if top_sell_merchants_str:
            embed_fields.append({"name": "💹 Top Sell Merchants", "value": top_sell_merchants_str.strip(), "inline": False})

    if not embed_fields: 
        print("No data to create Discord embed fields.")
        return

    embed = {
        "title": "🔍 OSRS Gold Price Tracker",
        "fields": embed_fields,
        "color": 0xDAA520,
        "footer": {
            "text": "Data updated every 30 minutes. From merchants.to API"
        },
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    payload = {
        "embeds": [embed]
    }

    response = scraper.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    response.raise_for_status() 
    print("Successfully sent combined data to Discord.")

def main():
    """Main function to orchestrate scraping and posting."""
    print(f"Scraper started at {datetime.datetime.now()}. Will run cycles every 30 minutes.")

    api_info_map = {
        "buy": {
            "original_url": "https://merchants.to/currency/buy-osrs-gold",
            "api_url": "https://merchants.to/fetch/inc/buy_osrs_gold",
        },
        "sell": {
            "original_url": "https://merchants.to/currency/sell-osrs-gold",
            "api_url": "https://merchants.to/fetch/inc/sell_osrs_gold",
        }
    }
    
    while True:
        print(f"\nStarting new scrape cycle at {datetime.datetime.now()}...")
        
        all_buy_data = []
        all_sell_data = []

        buy_endpoint_info = api_info_map["buy"]
        print(f"Processing buy prices from API: {buy_endpoint_info['api_url']} (Ref: {buy_endpoint_info['original_url']})")
        json_buy_data = fetch_api_data(buy_endpoint_info['api_url'], buy_endpoint_info['original_url'])
        if json_buy_data:
            parsed_buy_data = parse_api_data(json_buy_data, "buy")
            if parsed_buy_data:
                all_buy_data.extend(parsed_buy_data)
                print(f"Found {len(all_buy_data)} buy entries via API.")
            else:
                print(f"No buy merchant data parsed from API response ({buy_endpoint_info['api_url']})")
        else:
            print(f"Failed to fetch or parse buy data from API: {buy_endpoint_info['api_url']}")

        sell_endpoint_info = api_info_map["sell"]
        print(f"Processing sell prices from API: {sell_endpoint_info['api_url']} (Ref: {sell_endpoint_info['original_url']})")
        json_sell_data = fetch_api_data(sell_endpoint_info['api_url'], sell_endpoint_info['original_url'])
        if json_sell_data:
            parsed_sell_data = parse_api_data(json_sell_data, "sell")
            if parsed_sell_data:
                all_sell_data.extend(parsed_sell_data)
                print(f"Found {len(all_sell_data)} sell entries via API.")
            else:
                print(f"No sell merchant data parsed from API response ({sell_endpoint_info['api_url']})")
        else:
            print(f"Failed to fetch or parse sell data from API: {sell_endpoint_info['api_url']}")
        
        if all_buy_data or all_sell_data:
            send_to_discord(all_buy_data, all_sell_data, DISCORD_WEBHOOK_URL)
        else:
            print("No buy or sell data found in this cycle to send to Discord.")
        
        next_run_time = datetime.datetime.now() + datetime.timedelta(minutes=30)
        print(f"Cycle complete. Waiting for 30 minutes. Next run at approximately: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}") # Reverted print
        time.sleep(30 * 60)


if __name__ == "__main__":
    main() 