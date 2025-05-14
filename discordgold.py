import json
import cloudscraper
import datetime
import time

DISCORD_WEBHOOK_URL = "YOUR DISCORD WEBHOOK URL HERE"

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0'

scraper = cloudscraper.create_scraper()


def fetch_api_data(api_url, original_page_url, source_type):
    """Fetches JSON data from the API endpoint using cloudscraper."""
    headers = {
        'User-Agent': DEFAULT_USER_AGENT,
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': original_page_url
    }

    if source_type == "merchants.to":
        headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
    elif source_type == "eldorado.gg":
        headers['Accept'] = 'application/json, text/plain, */*'
        headers['sec-ch-ua'] = '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"'
        headers['sec-ch-ua-mobile'] = '?0'
        headers['sec-ch-ua-platform'] = '"Windows"'
        headers['sec-fetch-dest'] = 'empty'
        headers['sec-fetch-mode'] = 'cors'
        headers['sec-fetch-site'] = 'same-origin'

    print(f"Fetching API data from: {api_url} (Source: {source_type}) with Referer: {original_page_url}")
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

def parse_api_data(json_data, page_type, source_type):
    """Parses JSON data to extract merchant names, prices, and stock based on source."""
    if not json_data:
        print(f"No JSON data received for parsing ({page_type}, {source_type}).")
        return []

    merchants_data = []

    if source_type == "merchants.to":
        if not json_data.get("success") or not isinstance(json_data.get("data"), list):
            print(f"Invalid or unsuccessful API response for {page_type} ({source_type}): {str(json_data)[:200]}...")
            return []
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
                        'type': page_type,
                        'source': source_type
                    }
                    if stock_value is not None:
                        data_entry['stock'] = stock_value
                    
                    merchants_data.append(data_entry)
                else:
                    print(f"Skipping item from {source_type} due to missing merchant_name or price_value_str: Name={merchant_name}, PriceStr={price_value_str}")
            except ValueError:
                print(f"Error converting price/stock for item from {source_type} {str(item)[:100]}... Price string was: '{price_value_str}'")
            except Exception as e:
                print(f"An unexpected error occurred while parsing item from {source_type} {str(item)[:100]}...: {e}")
    
    elif source_type == "eldorado.gg":
        print(f"--- Parsing Eldorado.gg data ({page_type}) ---")
        offers_to_parse = []
        if isinstance(json_data.get("results"), list):
            offers_to_parse = json_data["results"]
            print(f"Found 'results' list, expecting {len(offers_to_parse)} items from Eldorado (remainingOffers).")
        elif isinstance(json_data.get("offer"), dict) and isinstance(json_data.get("user"), dict):
            offers_to_parse = [json_data]
            print("Found single offer structure, expecting 1 item from Eldorado (topOffer).")
        else:
            print(f"Unexpected JSON structure for {page_type} ({source_type}). Neither 'results' list nor direct 'offer'/'user' found: {str(json_data)[:300]}...")
            return []

        if not offers_to_parse:
            print(f"No offers found to parse for Eldorado.gg ({page_type}).")
            return []

        for item in offers_to_parse:
            try:
                merchant_name = item.get('user', {}).get('username')
                offer_info = item.get('offer', {})
                price_per_unit_info = offer_info.get('pricePerUnit', {})
                price_value_float = price_per_unit_info.get('amount')

                stock_value = offer_info.get('quantity')

                if merchant_name and price_value_float is not None:
                    price_value_float = float(price_value_float)
                    formatted_price = f"${price_value_float:.4f}"

                    data_entry = {
                        'name': merchant_name,
                        'price_float': price_value_float,
                        'price_str': formatted_price,
                        'type': page_type,
                        'source': source_type
                    }
                    if stock_value is not None:
                        try:
                            data_entry['stock'] = int(stock_value)
                        except (ValueError, TypeError):
                            print(f"Could not convert stock '{stock_value}' to int for {merchant_name} from Eldorado.")
                            data_entry['stock'] = None
                    
                    merchants_data.append(data_entry)
                else:
                    print(f"Skipping item from {source_type} due to missing merchant_name or price: Name={merchant_name}, Price={price_value_float}")
            except ValueError as e:
                print(f"Error converting data for item from {source_type} {str(item)[:100]}...: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while parsing item from {source_type} {str(item)[:100]}...: {e}")
        print(f"--- Finished parsing {len(merchants_data)} items from Eldorado.gg ({page_type}) ---")

    else:
        print(f"Unknown source_type encountered in parse_api_data: {source_type}")
            
    return merchants_data

def send_to_discord(buy_list, sell_list, webhook_url):
    """Sends combined buy and sell data to a Discord webhook in a formatted embed.""" 

    if not webhook_url or webhook_url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        print("Discord webhook URL is not configured. Skipping sending message.")
        print("Merchants.to Buy Offers:")
        for item in buy_list: 
            stock_info_str = f" | {item['stock']}M" if 'stock' in item else ""
            print(f"  - {item['name']}: {item['price_str']}/M{stock_info_str}")
        
        merchants_to_sell_fallback = [item for item in sell_list if item.get('source') == 'merchants.to']
        eldorado_sell_fallback = [item for item in sell_list if item.get('source') == 'eldorado.gg']

        print("Merchants.to Sell Offers:")
        for item in merchants_to_sell_fallback:
            stock_info_str = f" | {item['stock']}M" if 'stock' in item else ""
            print(f"  - {item['name']}: {item['price_str']}/M{stock_info_str}")

        print("Eldorado.gg Sell Offers:")
        for item in eldorado_sell_fallback:
            stock_info_str = f" | {item['stock']}M" if 'stock' in item else ""
            print(f"  - {item['name']}: {item['price_str']}/M{stock_info_str}")
        return

    embed_fields = []

    merchants_to_buy_list = [item for item in buy_list if item.get('source') == 'merchants.to']
    merchants_to_sell_list = [item for item in sell_list if item.get('source') == 'merchants.to']
    eldorado_sell_list = [item for item in sell_list if item.get('source') == 'eldorado.gg']

    if merchants_to_buy_list:
        merchants_to_buy_list.sort(key=lambda x: x['price_float'])
        best_buy_mt = merchants_to_buy_list[0]
        embed_fields.append({
            "name": "💰 Best Merchants.to Buy Price", 
            "value": f"{best_buy_mt['price_str']}/M by `{best_buy_mt['name']}`", 
            "inline": False
        })
        top_buy_merchants_mt_str = ""
        for i, merchant in enumerate(merchants_to_buy_list[:5]): 
            stock_info_formatted = f" | `{merchant['stock']}M`" if merchant.get('stock') is not None else ""
            top_buy_merchants_mt_str += f"{i+1}) `{merchant['name']}` | `{merchant['price_str']}/M`{stock_info_formatted}\n"
        if top_buy_merchants_mt_str:
            embed_fields.append({"name": "🏪 Top Merchants.to Buy Merchants", "value": top_buy_merchants_mt_str.strip(), "inline": False})

    if merchants_to_sell_list:
        merchants_to_sell_list.sort(key=lambda x: x['price_float'], reverse=True)
        best_sell_mt = merchants_to_sell_list[0]
        embed_fields.append({
            "name": "💵 Best Merchants.to Sell Price", 
            "value": f"{best_sell_mt['price_str']}/M by `{best_sell_mt['name']}`", 
            "inline": False
        })
        top_sell_merchants_mt_str = ""
        for i, merchant in enumerate(merchants_to_sell_list[:5]): 
            stock_info_formatted = f" | `{merchant['stock']}M`" if merchant.get('stock') is not None else ""
            top_sell_merchants_mt_str += f"{i+1}) `{merchant['name']}` | `{merchant['price_str']}/M`{stock_info_formatted}\n"
        if top_sell_merchants_mt_str:
            embed_fields.append({"name": "💹 Top Merchants.to Sell Merchants", "value": top_sell_merchants_mt_str.strip(), "inline": False})

    if eldorado_sell_list:
        eldorado_sell_list.sort(key=lambda x: x['price_float'])
        best_sell_eldorado = eldorado_sell_list[0]
        embed_fields.append({
            "name": "🥇 Best Eldorado.gg Price (User Buys Gold)", 
            "value": f"{best_sell_eldorado['price_str']}/M by `{best_sell_eldorado['name']}`", 
            "inline": False
        })
        top_sell_merchants_eldorado_str = ""
        for i, merchant in enumerate(eldorado_sell_list[:5]): 
            stock_info_formatted = f" | `{merchant['stock']}M`" if merchant.get('stock') is not None else ""
            top_sell_merchants_eldorado_str += f"{i+1}) `{merchant['name']}` | `{merchant['price_str']}/M`{stock_info_formatted}\n"
        if top_sell_merchants_eldorado_str:
            embed_fields.append({"name": "👑 Top Eldorado.gg Sellers", "value": top_sell_merchants_eldorado_str.strip(), "inline": False})

    if not embed_fields: 
        print("No data to create Discord embed fields.")
        return

    embed = {
        "title": "🔍 OSRS Gold Price Tracker",
        "fields": embed_fields,
        "color": 0xDAA520,
        "footer": {
            "text": "Data updated every 30 minutes. From merchants.to & Eldorado.gg APIs" # Updated footer
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
        "merchants_buy": {
            "original_url": "https://merchants.to/currency/buy-osrs-gold",
            "api_url": "https://merchants.to/fetch/inc/buy_osrs_gold",
            "source_type": "merchants.to",
            "page_type": "buy"
        },
        "merchants_sell": {
            "original_url": "https://merchants.to/currency/sell-osrs-gold",
            "api_url": "https://merchants.to/fetch/inc/sell_osrs_gold",
            "source_type": "merchants.to",
            "page_type": "sell"
        },
        "eldorado_sell_top": {
            "original_url": "https://www.eldorado.gg/osrs-gold/g/10-0-0",
            "api_url": "https://www.eldorado.gg/api/predefinedOffers/augmentedGame/topOffer?gameId=10&category=Currency",
            "source_type": "eldorado.gg",
            "page_type": "sell"
        },
        "eldorado_sell_remaining": {
            "original_url": "https://www.eldorado.gg/osrs-gold/g/10-0-0",
            "api_url": "https://www.eldorado.gg/api/predefinedOffers/augmentedGame/remainingOffers?gameId=10&category=Currency&pageIndex=1&pageSize=20",
            "source_type": "eldorado.gg",
            "page_type": "sell"
        }
    }
    
    while True:
        print(f"\nStarting new scrape cycle at {datetime.datetime.now()}...")
        
        all_buy_data = []
        all_sell_data = []

        for key, endpoint_info in api_info_map.items():
            print(f"Processing {key} from source: {endpoint_info['source_type']}")
            print(f"  API URL: {endpoint_info['api_url']}")
            print(f"  Referer: {endpoint_info['original_url']}")
            print(f"  Page Type: {endpoint_info['page_type']}")

            json_data = fetch_api_data(endpoint_info['api_url'], 
                                       endpoint_info['original_url'], 
                                       endpoint_info['source_type'])
            if json_data:
                parsed_data = parse_api_data(json_data, 
                                             endpoint_info['page_type'], 
                                             endpoint_info['source_type'])
                if parsed_data:
                    if endpoint_info['page_type'] == 'buy':
                        all_buy_data.extend(parsed_data)
                    elif endpoint_info['page_type'] == 'sell':
                        all_sell_data.extend(parsed_data)
                    print(f"Found {len(parsed_data)} entries for {key} ({endpoint_info['page_type']} from {endpoint_info['source_type']}).")
                else:
                    print(f"No merchant data parsed from API response for {key} ({endpoint_info['api_url']})")
            else:
                print(f"Failed to fetch or parse data for {key} from API: {endpoint_info['api_url']}")

        if all_buy_data or all_sell_data:
            send_to_discord(all_buy_data, all_sell_data, DISCORD_WEBHOOK_URL)
        else:
            print("No buy or sell data found in this cycle to send to Discord.")
        
        next_run_time = datetime.datetime.now() + datetime.timedelta(minutes=30)
        print(f"Cycle complete. Waiting for 30 minutes. Next run at approximately: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}") # Reverted print
        time.sleep(30 * 60)


if __name__ == "__main__":
    main() 
