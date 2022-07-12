from typing import Dict, Optional

from flask_batteries_included.sqldb import db


class AddressMixin:

    address_line_1: Optional[str] = db.Column(db.String, nullable=True)
    address_line_2: Optional[str] = db.Column(db.String, nullable=True)
    address_line_3: Optional[str] = db.Column(db.String, nullable=True)
    address_line_4: Optional[str] = db.Column(db.String, nullable=True)
    locality: Optional[str] = db.Column(db.String, nullable=True)
    region: Optional[str] = db.Column(db.String, nullable=True)
    postcode: Optional[str] = db.Column(db.String, nullable=True)
    country: Optional[str] = db.Column(db.String, nullable=True)

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
