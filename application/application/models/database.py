from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

# from application.models.stocks import Indexes
# from .stocks import Indexes
# from application.models import Indexes
db = SQLAlchemy()
engine = create_engine('postgresql://USER:PASSWORD@localhost:5432/APPLICATION_DB')


