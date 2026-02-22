import os
from concierge import Concierge

mcp = Concierge("concierge-app", stateless_http=True)


@mcp.widget(
    uri="ui://widget/pizza-map",
    entrypoint="pizzaz.html",
    title="Show Pizza Map",
    invoking="Hand-tossing a map",
    invoked="Served a fresh map",
)
async def pizza_map(pizzaTopping: str) -> dict:
    """Show a map of pizza spots for a given topping"""
    return {"pizzaTopping": pizzaTopping}


@mcp.widget(
    uri="ui://widget/pizza-carousel",
    entrypoint="pizzaz-carousel.html",
    title="Show Pizza Carousel",
    invoking="Carousel some spots",
    invoked="Served a fresh carousel",
)
async def pizza_carousel(pizzaTopping: str) -> dict:
    """Show a carousel of pizza spots"""
    return {"pizzaTopping": pizzaTopping}


@mcp.widget(
    uri="ui://widget/pizza-albums",
    entrypoint="pizzaz-albums.html",
    title="Show Pizza Album",
    invoking="Hand-tossing an album",
    invoked="Served a fresh album",
)
async def pizza_albums(pizzaTopping: str) -> dict:
    """Show a photo album of pizza spots"""
    return {"pizzaTopping": pizzaTopping}


@mcp.widget(
    uri="ui://widget/pizza-list",
    entrypoint="pizzaz-list.html",
    title="Show Pizza List",
    invoking="Hand-tossing a list",
    invoked="Served a fresh list",
)
async def pizza_list(pizzaTopping: str) -> dict:
    """Show a list of pizza spots"""
    return {"pizzaTopping": pizzaTopping}


@mcp.widget(
    uri="ui://widget/pizza-shop",
    entrypoint="pizzaz-shop.html",
    title="Open Pizzaz Shop",
    invoking="Opening the shop",
    invoked="Shop opened",
)
async def pizza_shop(pizzaTopping: str) -> dict:
    """Open the Pizzaz shop"""
    return {"pizzaTopping": pizzaTopping}


app = mcp.streamable_http_app()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on 0.0.0.0:{port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)
