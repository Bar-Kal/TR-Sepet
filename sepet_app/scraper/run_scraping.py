from .shop_scrapers.scrape_runner import main
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pass shop name to scrape a single shop.")
    parser.add_argument(
        '--shop',
        type = str,
        default=None,
        help="Shop name (e.g. Migros)"
    )
    args = parser.parse_args()
    shop_name = args.shop

    main(shop_name)