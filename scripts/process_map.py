import requests
from lxml import etree
from lxml.etree import Element
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import csv
import re
from typing import Any, Annotated
from pydantic import (
    BaseModel,
    AliasChoices,
    BeforeValidator,
    AliasPath,
    Field,
    field_validator,
    model_validator,
)


BASE_DIR = Path(__file__).resolve().parent.parent


def parse_bool(value):
    if isinstance(value, str):
        value = value.strip().upper()
        if value == "":
            return None
        if "UNKNOWN" in value:
            return None
        if "TRUE" in value:
            return True
        if "FALSE" in value:
            return False
    return value


OptionalBoolean = Annotated[
    bool | None,
    BeforeValidator(parse_bool),
]


class NeedResource(BaseModel):
    name: str
    category: str
    address: str | None = Field(
        default=None, validation_alias=AliasChoices("address", "Address")
    )
    city: str | None = Field(default=None, validation_alias="City")
    zipcode: str | None = Field(
        default=None, validation_alias=AliasChoices("zipcode", "Zipcode", "Zip Code")
    )
    services: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("Services Provided", "Service Provided"),
    )
    disclaimer: str | None = Field(
        default=None, validation_alias=AliasChoices("Disclaimers", "Disclaimer(s)")
    )
    contact: str = Field(default="")
    phone: str | None = None
    hours: str | None = None
    drop_in: OptionalBoolean = Field(default=None, validation_alias="Drop In Friendly?")
    need_referral: OptionalBoolean = Field(
        default=None, validation_alias="Need Referral?"
    )
    age_restricted: OptionalBoolean = Field(
        default=None, validation_alias="Age Restricted?"
    )
    gendered: OptionalBoolean = Field(default=None, validation_alias="Gendered?")
    languages: list[str] = Field(default_factory=list)
    facility_type: str | None = Field(
        default=None, validation_alias=AliasChoices("Type of Facility or Service", "Type of Service")
    )
    vetted: bool = Field(default=False, validation_alias="Vetted")
    lgbtq_friendly: bool = Field(
        default=False, validation_alias="LGBTQ Friendly?"
    )  # Hide if False, not necessarily bad
    need_appointment: bool = Field(default=False, validation_alias="Need Appointment?")
    need_referral: bool = Field(default=False, validation_alias="Need Referral?")
    need_id: bool = Field(default=False, validation_alias="Need ID?")
    age_restricted: bool = Field(default=False, validation_alias="Age Restricted?")
    family_friendly: bool = Field(default=False, validation_alias="Family Friendly?")
    free: bool = Field(
        default=False, validation_alias=AliasChoices("Free?", "Free Services?")
    )
    drop_in: bool = Field(default=False, validation_alias="Drop In Friendly?")
    accepts_medicaid_medicare: bool = Field(
        default=False, validation_alias="Accepts Medicaid/Medicare?"
    )
    additional_info: str = Field(default="", validation_alias="Additional Info")
    notes: str = Field(default="", validation_alias="Notes")
    description: str = Field(default="", validation_alias="Description")
    disclaimer: str = Field(default="", validation_alias="Disclaimer(s)")
    coordinates: tuple[float, float] | None = Field(default=None)
    # TODO: Split out rentals

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = data.copy()
        data["languages"] = []
        for key, value in data.items():
            if ("speaking" in key.lower()) and (value.strip() == "TRUE"):
                data["languages"].append(key.split(" ")[0])
        return data

    @field_validator("services", mode="before")
    @classmethod
    def split_services(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"(?:,| and )", value) if item.strip()]
        return value

    @field_validator(
        "vetted",
        "lgbtq_friendly",
        "need_appointment",
        "need_referral",
        "need_id",
        "age_restricted",
        "family_friendly",
        "free",
        "drop_in",
        "accepts_medicaid_medicare",
        mode="before",
    )
    @classmethod
    def parse_true_flag(cls, value):
        return value == "TRUE"


NS = {"kml": "http://www.opengis.net/kml/2.2"}


def _parse_first_text(element: etree._Element, xpath: str) -> str:
    """
    Helper to perform the common operation for taking the first element of a query and
    returning the inner text if it's present
    """
    results = element.xpath(xpath, namespaces=NS)
    if len(results) == 0:
        return ""
    return (results[0].text or "").strip()


def load_address_cache() -> dict[str, tuple[float, float]]:
    address_cache: dict[str, tuple[float, float]] = {}
    with Path.open(BASE_DIR / "data" / "addresses.csv", "r") as f:
        for row in csv.DictReader(f):
            address_cache[row["address"]] = (
                float(row["longitude"]),
                float(row["latitude"]),
            )
    return address_cache


def clean_address(address: str) -> str:
    if not address.strip():
        return ""

    address_str = re.sub(r"\s+", " ", address.upper()).strip()
    split_address = address_str.split(" ")
    if (
        (len(split_address) < 5)
        and ("DETROIT" not in split_address)
        and (not split_address[-1].isdigit())
    ):
        return f"{address_str} DETROIT MI"
    if (len(split_address) < 3) and (split_address[0] == "DETROIT"):
        # If it's something like "DETROIT 48000" it's probably not worth including
        return ""
    return address_str


def parse_data_attributes(element: etree._Element) -> dict[str, str]:
    data_attributes: dict[str, str] = {}
    for data_attribute in element.xpath(".//kml:Data", namespaces=NS):
        data_attributes[data_attribute.attrib["name"]] = _parse_first_text(
            data_attribute, "./kml:value"
        )
    return data_attributes


def parse_point(placemark: etree._Element) -> tuple[float, float] | None:
    point_results = placemark.xpath("./kml:Point/kml:coordinates", namespaces=NS)
    if len(point_results) == 0:
        return None
    coordinates = [float(c) for c in point_results[0].text.split(",")]
    return (coordinates[0], coordinates[1])


def parse_placemark(element: etree._Element, category: str) -> NeedResource:
    # TODO: Handle rental coords (lat, "long")
    return NeedResource.model_validate(
        {
            "name": _parse_first_text(element, "./kml:name"),
            "category": category,
            "address": _parse_first_text(element, "./kml:address"),
            **parse_data_attributes(element),
            "coordinates": parse_point(element),
        }
    )


def parse_folder(folder: etree) -> list[NeedResource]:
    category = _parse_first_text(folder, "./kml:name")
    resources: list[NeedResource] = []
    for placemark in folder.xpath(".//kml:Placemark", namespaces=NS):
        resources.append(parse_placemark(placemark, category))
    return resources


def main():
    with Path.open(BASE_DIR / "data" / "map.kml", "r") as f:
        tree = etree.fromstring(f.read().encode())
    outputs = []
    for folder in tree.xpath(".//kml:Folder", namespaces=NS):
        outputs.extend(parse_folder(folder))

    resources = []
    resource_features = []
    addresses_to_geocode = set()
    address_cache = load_address_cache()

    for output in outputs:
        output_dict = output.model_dump(mode="json")
        coordinates = output_dict.pop("coordinates", None)
        cleaned_address = clean_address(output.address)
        # Attempt to load from cache if not included
        if coordinates is None:
            coordinates = address_cache.get(cleaned_address)
            output.coordinates = coordinates

        if coordinates:
            resources.append(output.model_dump(mode="json"))
            resource_features.append(
                {
                    "type": "Feature",
                    "properties": output_dict,
                    "geometry": {"type": "Point", "coordinates": coordinates},
                }
            )
        elif cleaned_address:
            # If we don't find an address, add it to a list. Can also throw an error
            addresses_to_geocode.add(cleaned_address)

    with Path.open(BASE_DIR / "data" / "missing-addresses.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=["address"])
        writer.writeheader()
        writer.writerows([{"address": address} for address in addresses_to_geocode])

    with Path.open(BASE_DIR / "src" / "assets" / "resources.json", "w") as f:
        json.dump(resources, f)

    with Path.open(BASE_DIR / "data" / "resources.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": resource_features}, f)


if __name__ == "__main__":
    main()
