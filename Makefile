
BUILD := _build

all:
	mkdir -p $(BUILD)
	meson . $(BUILD)

local:
	meson configure $(BUILD) -Dprefix=$$(pwd)/$(BUILD)/testdir
	ninja -C $(BUILD) install

install:
	ninja -C $(BUILD) install

run:
	ninja -C _build run

test:
	pytest tests/

clean:
	rm -r $(BUILD)