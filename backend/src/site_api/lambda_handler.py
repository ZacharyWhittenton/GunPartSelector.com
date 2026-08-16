from mangum import Mangum

from site_api.main import app

handler = Mangum(app, lifespan="auto")
