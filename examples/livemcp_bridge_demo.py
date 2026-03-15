"""Build the LiveMCP Max-side bridge demo device."""

from m4l_builder import (
    DEFAULT_BRIDGE_PORT,
    build_livemcp_bridge_demo,
    device_output_path,
)


device = build_livemcp_bridge_demo(port=DEFAULT_BRIDGE_PORT)
output = device_output_path("LiveMCP Bridge Demo")
written = device.build(output)

print("Built %s bytes -> %s" % (written, output))
