all: src/assets/resources.json data/resources.geojson

data/resources.geojson src/assets/resources.json: data/map.kml
	poetry run python scripts/process_map.py

data/map.kml:
	wget -O $@ "https://www.google.com/maps/d/kml?mid=1kZ3FGRuxC4Ou31RQP9JZh5gr___0x_I&forcekml=1"
