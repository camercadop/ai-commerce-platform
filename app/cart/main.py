import uvicorn

from app.cart.app import create_app
from app.shared.auth import AuthSettings
from app.shared.db import DatabaseSettings

app = create_app(
    db_settings=DatabaseSettings.model_validate({}),
    auth_settings=AuthSettings.model_validate({}),
)

if __name__ == "__main__":
    uvicorn.run("app.cart.main:app", host="0.0.0.0", port=8000)
