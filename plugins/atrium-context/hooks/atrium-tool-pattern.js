// The atrium MCP server's tools, registered directly (`mcp__atrium__...`) or
// through a plugin (`mcp__plugin_<plugin>_atrium__...`, the plugin's name free
// to hold underscores of its own).
export const ATRIUM_TOOL_PATTERN = /^mcp__(plugin_.+_)?atrium__/
