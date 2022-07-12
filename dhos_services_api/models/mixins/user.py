from typing import Dict, Optional, Union

from neomodel import StringProperty


class UserMixin:
    first_name = StringProperty()
    last_name = StringProperty()
    phone_number = StringProperty()

    def pack_user(
        self,
    ) -> Union[Dict[str, None], Dict[str, Optional[str]], Dict[str, str]]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
        }

    def compack_user(self) -> Union[Dict[str, None], Dict[str, str]]:
        return {"first_name": self.first_name, "last_name": self.last_name}
