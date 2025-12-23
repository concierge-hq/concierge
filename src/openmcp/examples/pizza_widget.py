from starlette.middleware.cors import CORSMiddleware

from openmcp import OpenMCP

PIZZA_LIST_HTML = """<!DOCTYPE html>
<html><head><style>
body { font-family: system-ui; padding: 20px; background: linear-gradient(135deg, #fff5f5, #ffe5e5); }
.card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.topping { color: #e55; font-weight: bold; font-size: 1.5em; }
ul { list-style: none; padding: 0; }
li { padding: 8px 0; border-bottom: 1px solid #eee; }
</style></head><body>
<div class="card">
  <h1>🍕 Pizza Spots</h1>
  <p>Showing spots with: <span class="topping" id="topping">Loading...</span></p>
  <ul>
    <li>Joe's Pizza - ⭐ 4.8</li>
    <li>Di Fara Pizza - ⭐ 4.9</li>
    <li>Lucali - ⭐ 4.7</li>
  </ul>
</div>
<script>
const output = window.openai?.toolOutput;
if (output?.pizzaTopping) document.getElementById('topping').textContent = output.pizzaTopping;
</script>
</body></html>"""

PIZZA_MAP_HTML = """<!DOCTYPE html>
<html><head><style>
body { font-family: system-ui; margin: 0; background: #1a1a2e; color: white; }
.map { width: 100%; height: 250px; background: linear-gradient(45deg, #16213e, #0f3460); 
       display: flex; align-items: center; justify-content: center; flex-direction: column; }
.topping { color: #ff6b6b; font-size: 2em; }
.pin { font-size: 2em; animation: bounce 1s infinite; }
@keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
</style></head><body>
<div class="map">
  <div class="pin">📍</div>
  <h1>Pizza Map</h1>
  <p>Finding <span class="topping" id="topping">...</span> near you</p>
</div>
<script>
const output = window.openai?.toolOutput;
if (output?.pizzaTopping) document.getElementById('topping').textContent = output.pizzaTopping;
</script>
</body></html>"""


mcp = OpenMCP("pizza-openmcp", stateless_http=True)


@mcp.widget(
    uri="ui://widget/pizza-list.html",
    html=PIZZA_LIST_HTML,
    title="Show Pizza List",
    invoking="Hand-tossing a list",
    invoked="Served a fresh list",
)
async def pizza_list(pizzaTopping: str) -> dict:
    """Show a list of pizza spots for a given topping"""
    return {"pizzaTopping": pizzaTopping}


@mcp.widget(
    uri="ui://widget/pizza-map.html",
    html=PIZZA_MAP_HTML,
    title="Show Pizza Map",
    invoking="Hand-tossing a map",
    invoked="Served a fresh map",
)
async def pizza_map(pizzaTopping: str) -> dict:
    """Show a map of pizza spots for a given topping"""
    return {"pizzaTopping": pizzaTopping}


app = mcp.streamable_http_app()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pizza_widget:app", host="0.0.0.0", port=8000)
