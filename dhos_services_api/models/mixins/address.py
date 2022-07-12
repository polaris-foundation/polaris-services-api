from typing import Dict, Optional

from neomodel import StringProperty


class AddressMixin:

    address_line_1: Optional[str] = StringProperty()
    address_line_2: Optional[str] = StringProperty()
    address_line_3: Optional[str] = StringProperty()
    address_line_4: Optional[str] = StringProperty()
    locality: Optional[str] = StringProperty()
    region: Optional[str] = StringProperty()
    postcode: Optional[str] = StringProperty()
    country: Optional[str] = StringProperty()

    def pack_address(self) -> Dict[str, Optional[str]]:

        return {
            "address_line_1": self.address_line_1,
            "address_line_2": self.address_line_2,
            "address_line_3": self.address_line_3,
            "address_line_4": self.address_line_4,
            "locality": self.locality,
            "region": self.region,
            "postcode": self.postcode,
            "country": self.country,
        }
