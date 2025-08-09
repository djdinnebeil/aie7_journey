# weather_server.py
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import os
from weatherapi import WeatherClient

load_dotenv()

mcp = FastMCP("mcp-server")
weather = WeatherClient()

@mcp.tool()
def get_current_weather(location: str) -> str:
    """Retrieves the current weather for a given city or zip code"""
    return weather.get_current_weather(location)

if __name__ == "__main__":
    print('server started')
    mcp.run(transport="stdio")