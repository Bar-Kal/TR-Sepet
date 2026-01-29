import datetime
from dataclasses import dataclass

class ScraperCore:
    """
    A core class providing common functionalities for all scraper and all different base classes.
    """

    def __init__(self):
        """
        Initializes the ScraperCore by loading the machine learning model.
        """

    @dataclass
    class ScrapedProductInfo:
        """A class for holding scraped product information"""

        Scrape_Timestamp: datetime
        Display_Name: str
        Shop_ID: int
        Category_ID: int
        Product_ID: int
        Price: float
        Discount_Price: float
        URL: str
        Scraped_Product_ID: str