import importlib
from typing import Dict, Any
from .simple_base import SimpleBaseScraper

def get_scraper(shop_config: Dict[str, Any]) -> SimpleBaseScraper:
    """
    Factory function to dynamically get a scraper instance from its configuration.

    This function reads the module and class names from the config dictionary,
    dynamically imports the module, retrieves the class, and returns an
    instantiated object.

    Args:
        shop_config (Dict[str, Any]): A dictionary containing the shop's configuration,
                                      including 'scraper_module', 'scraper_class',
                                      'shop_name', and 'base_url'.

    Returns:
        An instance of a SimpleBaseScraper subclass.

    Raises:
        ValueError: If the required configuration keys are missing.
        ImportError: If the specified module cannot be found.
        AttributeError: If the specified class does not exist in the module.
    """
    try:
        module_path = shop_config['scraper_module']
        class_name = shop_config['scraper_class']
        shop_name = shop_config['shop_name']
        base_url = shop_config['base_url']
    except KeyError as e:
        raise ValueError(f"Configuration for shop is missing required key: {e}")

    try:
        # Dynamically import the module (e.g., 'scrapers.migros')
        scraper_module = importlib.import_module(module_path)
        # Get the class from the imported module (e.g., MigrosScraper)
        scraper_class = getattr(scraper_module, class_name)

    except ImportError:
        # This error will now only be raised if the module truly doesn't exist,
        # not because of a pathing issue.
        raise ImportError(f"Could not import scraper module: '{module_path}'")
    except AttributeError:
        raise AttributeError(f"Class '{class_name}' not found in module '{module_path}'")

    # Create and return an instance of the correct scraper class
    return scraper_class(shop_name=shop_name, base_url=base_url)