import requests
from lxml import etree
from lxml.etree import Element
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import csv
import re


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class NeedsResource:
    name: str
    description: str
    category: str
    address: str | None
    attributes: dict[str, str]
    coordinates: tuple[float, float] | None = None


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


def parse_placemark(element: etree._Element, category: str) -> NeedsResource:
    attributes = parse_data_attributes(element)
    address = _parse_first_text(element, "./kml:address")
    coordinates = parse_point(element)

    # Handle rentals which have a different structure
    if "address" in attributes:
        address = attributes.pop("address", "")
    if ("lat" in attributes) and ("long" in attributes):
        lat = attributes.pop("lat", 0)
        lon = attributes.pop("long", 0)
        coordinates = (float(lon), float(lat))

    return NeedsResource(
        name=_parse_first_text(element, "./kml:name"),
        description=_parse_first_text(element, "./kml:description").replace(
            "<br>", "\n"
        ),
        category=category,
        address=_parse_first_text(element, "./kml:address"),
        attributes=parse_data_attributes(element),
        coordinates=parse_point(element),
    )


def parse_folder(folder: etree) -> list[NeedsResource]:
    category = _parse_first_text(folder, "./kml:name")
    resources: list[NeedsResource] = []
    for placemark in folder.xpath(".//kml:Placemark", namespaces=NS):
        resources.append(parse_placemark(placemark, category))
    return resources


def main():
    with Path.open(BASE_DIR / "data" / "map.kml", "r") as f:
        tree = etree.fromstring(f.read().encode())
    outputs = []
    for folder in tree.xpath(".//kml:Folder", namespaces=NS):
        outputs.extend(parse_folder(folder))

    resource_features = []
    addresses_to_geocode = set()
    address_cache = load_address_cache()

    for output in outputs:
        output_dict = asdict(output)
        coordinates = output_dict.pop("coordinates")
        cleaned_address = clean_address(output.address)
        # Attempt to load from cache if not included
        if coordinates is None:
            coordinates = address_cache.get(cleaned_address)

        if coordinates:
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

    with Path.open(BASE_DIR / "data" / "resources.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": resource_features}, f)


if __name__ == "__main__":
    main()
