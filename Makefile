
BUILD := _build

all:
	mkdir -p $(BUILD)
	meson . $(BUILD)
	meson configure $(BUILD) -Dprefix=$$(pwd)/$(BUILD)/testdir

local:
	ninja -C $(BUILD) install # This will actually install in _build/testdir

install:
	ninja -C $(BUILD) install

run:
	ninja -C _build run

