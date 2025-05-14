import time
import datetime
import cloudscraper

DISCORD_WEBHOOK_URL = "YOUR DISCORD WEBHOOK URL"
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0')

scraper = cloudscraper.create_scraper()

API_SOURCES = {
    'merchants_buy': {
        'url': 'https://merchants.to/fetch/inc/buy_osrs_gold',
        'referer': 'https://merchants.to/currency/buy-osrs-gold',
        'headers': {'Accept': 'application/json, text/javascript, */*; q=0.01'}
    },
    'merchants_sell': {
        'url': 'https://merchants.to/fetch/inc/sell_osrs_gold',
        'referer': 'https://merchants.to/currency/sell-osrs-gold',
        'headers': {'Accept': 'application/json, text/javascript, */*; q=0.01'}
    },
    'eldorado': {
        'urls': [
            ('https://www.eldorado.gg/api/predefinedOffers/augmentedGame/topOffer'
             '?gameId=10&category=Currency'),
            ('https://www.eldorado.gg/api/predefinedOffers/augmentedGame/'
             'remainingOffers?gameId=10&category=Currency&pageIndex=1&pageSize=20')
        ],
        'referer': 'https://www.eldorado.gg/osrs-gold/g/10-0-0',
        'headers': {
            'Accept': 'application/json, text/plain, */*',
            'sec-ch-ua': ('"Chromium";v="136", "Microsoft Edge";v="136", '
                          '"Not.A/Brand";v="99"'),
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
    }
}


def fetch_data(source_name):
    """Fetch data from specified source with proper headers"""
    config = API_SOURCES.get(source_name)
    if not config:
        print(f"Unknown source: {source_name}")
        return None

    urls = config.get('urls') or [config.get('url')]
    urls = [u for u in urls if u]

    all_data = []
    
    for url in urls:
        headers = {
            'User-Agent': USER_AGENT,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': config['referer']
        }
        headers.update(config['headers'])

        try:
            print(f"Fetching {source_name} data from {url}")
            response = scraper.get(url, headers=headers)
            response.raise_for_status()
            all_data.append(response.json())
        except Exception as e:
            print(f"Error fetching {source_name} data: {str(e)}")
            continue
    
    return all_data if len(urls) > 1 else all_data[0] if all_data else None


def parse_merchants(data):
    """Parse merchants.to API response"""
    if not data or not data.get('success') or not isinstance(data.get('data'), list):
        return []
    
    results = []
    for item in data['data']:
        try:
            price_info = item.get('gold', {})
            price = float(price_info.get('price', 0))
            results.append({
                'name': item.get('seller_id', 'Unknown'),
                'price_float': price,
                'price_str': f"${price:.4f}",
                'stock': int(price_info['stock']) if price_info.get('stock') else None,
                'source': 'merchants.to'
            })
        except Exception as e:
            print(f"Error parsing merchant item: {str(e)}")
    return results

def parse_eldorado(data):
    """Parse eldorado.gg API response"""
    if not data:
        return []
    
    offers = data.get('results', [])
    if isinstance(data.get('offer'), dict):
        offers = [data]
    
    results = []
    for offer in offers:
        try:
            details = offer.get('offer', {})
            price = float(details.get('pricePerUnit', {}).get('amount', 0))
            results.append({
                'name': offer.get('user', {}).get('username', 'Unknown'),
                'price_float': price,
                'price_str': f"${price:.4f}",
                'stock': int(details.get('quantity', 0)),
                'source': 'eldorado.gg'
            })
        except Exception as e:
            print(f"Error parsing eldorado offer: {str(e)}")
    return results


def create_embed_field(entries, title, emoji):
    """Create sorted embed field data for Discord"""
    if not entries:
        return None
    
    sorted_entries = sorted(entries, key=lambda x: x['price'])
    best = sorted_entries[0]
    
    return {
        'title': f"{emoji} {title}",
        'best': f"{best['price']:.4f}/M by {best['name']}",
        'entries': sorted_entries[:5]
    }


def send_to_discord(buy_list, sell_list, webhook_url):
    """Sends combined buy and sell data to Discord in a well-formatted embed"""
    embed = {
        "title": "🔍 OSRS Gold Price Tracker",
        "color": 0xDAA520,
        "thumbnail": {
            "url": "https://i.imgur.com/BdvsAq8.png" 
        },
        "fields": [],
        "footer": {
            "text": "Data updated every 30 minutes. From merchants.to & Eldorado.gg APIs"
        },
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    if buy_list:
        buy_list.sort(key=lambda x: x['price_float'])
        best_buy = buy_list[0]
        buy_content = (
            f"**Best Price:** `{best_buy['price_str']}/M` by **{best_buy['name']}**\n"
            + "\n".join(
                f"{i+1}. `{item['price_str']}/M` - {item['name']}"
                + (f" (Stock: {item['stock']}M)" if item.get('stock') else "")
                for i, item in enumerate(buy_list[:5])
            )
        )
        embed['fields'].append({
            "name": "💰 Buy Offers (merchants.to)",
            "value": buy_content,
            "inline": False
        })

    if sell_list:
        mt_sell = [item for item in sell_list if item['source'] == 'merchants.to']
        if mt_sell:
            mt_sell.sort(key=lambda x: x['price_float'], reverse=True)
            best_mt_sell = mt_sell[0]
            mt_content = (
                f"**Best Price:** `{best_mt_sell['price_str']}/M` by **{best_mt_sell['name']}**\n"
                + "\n".join(
                    f"{i+1}. `{item['price_str']}/M` - {item['name']}"
                    + (f" (Stock: {item['stock']}M)" if item.get('stock') else "")
                    for i, item in enumerate(mt_sell[:5])
                )
            )
            embed['fields'].append({
                "name": "💵 Sell Offers (merchants.to)",
                "value": mt_content,
                "inline": False
            })

        ed_sell = [item for item in sell_list if item['source'] == 'eldorado.gg']
        if ed_sell:
            ed_sell.sort(key=lambda x: x['price_float'])
            best_ed_sell = ed_sell[0]
            ed_content = (
                f"**Best Price:** `{best_ed_sell['price_str']}/M` by **{best_ed_sell['name']}**\n"
                + "\n".join(
                    f"{i+1}. `{item['price_str']}/M` - {item['name']}"
                    + (f" (Stock: {item['stock']}M)" if item.get('stock') else "")
                    for i, item in enumerate(ed_sell[:5])
                )
            )
            embed['fields'].append({
                "name": "🥇 Eldorado.gg Offers",
                "value": ed_content,
                "inline": False
            })

    if not embed['fields']:
        embed['description'] = "⚠️ No current price data available - check back later!"

    try:
        response = scraper.post(
            webhook_url,
            json={"embeds": [embed]},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        print("Successfully sent formatted update to Discord")
    except Exception as e:
        print(f"Failed to send Discord message: {str(e)}")


def main():
    """Main execution loop"""
    print("Gold price tracker started. Runs every 30 minutes.")
    
    try:
        while True:
            start_time = time.time()
            print(f"\n{'=' * 40}")
            print(f"Starting new scan at {datetime.datetime.now()}")
            
            all_buy = []
            all_sell = []
            
            for endpoint in ['merchants_buy', 'merchants_sell']:
                data = fetch_data(endpoint)
                if data:
                    parsed = parse_merchants(data)
                    if 'buy' in endpoint:
                        all_buy.extend(parsed)
                    else:
                        all_sell.extend(parsed)

            eldorado_data = fetch_data('eldorado')
            if eldorado_data:
                if isinstance(eldorado_data, list):
                    for data in eldorado_data:
                        all_sell.extend(parse_eldorado(data))
                else:
                    all_sell.extend(parse_eldorado(eldorado_data))
            
            if all_buy or all_sell:
                send_to_discord(all_buy, all_sell, DISCORD_WEBHOOK_URL)
            else:
                print("No valid data found this cycle")
            
            elapsed = time.time() - start_time
            sleep_time = max(1800 - elapsed, 300)
            next_run = datetime.datetime.now() + datetime.timedelta(seconds=sleep_time)
            
            print(f"Cycle completed in {elapsed:.1f}s")
            print(f"Next update at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        print("\nTracker stopped by user")


if __name__ == "__main__":
    main()
