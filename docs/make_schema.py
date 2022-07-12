import codecs
import subprocess
from typing import List, Type

import sadisplay

import dhos_services_api.sqlmodels as schema

all_models = [getattr(schema, name) for name in schema.__all__]


def document(models: List[Type], basename: str) -> None:
    desc = sadisplay.describe(models)

    with codecs.open(f"docs/{basename}.plantuml", "w", encoding="utf-8") as f:
        f.write(sadisplay.plantuml(desc).rstrip() + "\n")

    with codecs.open(f"docs/{basename}.dot", "w", encoding="utf-8") as f:
        f.write(sadisplay.dot(desc).rstrip() + "\n")

    my_cmd = ["dot", "-Tsvg", f"docs/{basename}.dot"]
    with open(f"docs/{basename}.svg", "w") as outfile:
        subprocess.run(my_cmd, stdout=outfile)


document(all_models, "dhos_services")
