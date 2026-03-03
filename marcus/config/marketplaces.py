from dataclasses import dataclass


@dataclass(frozen=True)
class Marketplace:
    name: str
    code: str
    domain: str
    currency: str


AMAZON_FR = Marketplace("Amazon France", "amazon_fr", "amazon.fr", "EUR")
AMAZON_DE = Marketplace("Amazon Allemagne", "amazon_de", "amazon.de", "EUR")
AMAZON_US = Marketplace("Amazon US", "amazon_us", "amazon.com", "USD")
AMAZON_UK = Marketplace("Amazon UK", "amazon_uk", "amazon.co.uk", "GBP")
CDISCOUNT = Marketplace("Cdiscount", "cdiscount", "cdiscount.com", "EUR")
EBAY_FR = Marketplace("eBay France", "ebay_fr", "ebay.fr", "EUR")
FNAC = Marketplace("Fnac", "fnac", "fnac.com", "EUR")
RUE_DU_COMMERCE = Marketplace("Rue du Commerce", "rdc", "rueducommerce.fr", "EUR")

ALL_MARKETPLACES = [
    AMAZON_FR, AMAZON_DE, AMAZON_US, AMAZON_UK,
    CDISCOUNT, EBAY_FR, FNAC, RUE_DU_COMMERCE,
]

AMAZON_MARKETPLACES = [AMAZON_FR, AMAZON_DE, AMAZON_US, AMAZON_UK]
