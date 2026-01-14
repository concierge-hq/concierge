# Mini Store (UAIP Demo)

## Run
```bash
python main.py
```

## Call
```bash
# 1) Initialize
curl -X POST http://localhost:8000/initialize \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "mini_store"}'

# 2) Execute
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: <session_id>" \
  -d '{"workflow_name": "mini_store", "action": "method_call", "task": "select_item", "args": {"item_id": "sku-1"}}'
```

Stages: browse -> checkout -> payment
- browse: search_items, select_item
- checkout: set_quantity, set_shipping
- payment: pay
