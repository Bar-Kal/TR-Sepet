import datetime
from dataclasses import dataclass

class ScraperCore:
    """
    A core class providing common functionalities for all scrapers and all different base classes.
    """

    def __init__(self):
        """
        Initializes the ScraperCore by loading the machine learning models.
        """

    @dataclass
    class ScrapedProductInfo:
        """A class for holding scraped product information"""

        Scrape_Timestamp: datetime
        Display_Name: str
        Shop: str
        category_id: int
        Search_Term: str
        Price: float
        Discount_Price: float
        URL: str
        product_id: str