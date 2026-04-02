import traceback, sys
try:
    import app.schemas.record
except Exception:
    with open("debug_out.txt", "w", encoding="utf-8") as f:
        traceback.print_exc(file=f)
