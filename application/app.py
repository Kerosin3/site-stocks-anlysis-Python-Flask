from flask import (
    Flask,render_template,request,redirect,jsonify,
    url_for,flash,session,g,abort
)
import hashlib, uuid
from werkzeug.exceptions import BadRequest,InternalServerError,NotAcceptable
from application.views.stocks_main import stocks_main_views
from application.misc.stocks_getter import get_data_historical,get_lastday_data,get_today_price,get_today_prices_several,get_historical_for_graph,get_data_for_plotting
from application.models.db_functions_plotting import get_data_for_plotting_wrap
from os import getenv,environ
import config
from json import dumps
from bokeh.embed import json_item
from application.models.database import db
from application.models import create_index
from datetime import date
from datetime import datetime, timedelta
from application.models.db_functions import filling_indexes_db,remove_indexes
from bokeh.embed import file_html
from bokeh.resources import CDN
from bokeh.plotting import figure
from users.users import User,users_list

app = Flask(__name__)
app.register_blueprint(stocks_main_views)
from flask_migrate import Migrate
db.init_app(app)
migrate = Migrate(app, db)  # откуда он знает про db?

# app.config['SERVER_NAME'] = '0.0.0.0:5000'
environ["FLASK_ENV"] = "development"
environ["FLASK_DEBUG"] = "1"
workmode = getenv("FLASK_ENV", 'development')
if workmode == 'development':
    config_app = config.DevelopmentConfig
elif workmode == 'production':
    config_app = config.ProductionConfig
elif workmode == 'test':
    config_app = config.TestingConfig
else:
    raise EnvironmentError('Not right mode of initialization, aborting')
app.config.from_object(config_app)
# environ["FLASK_DEBUG"] = "1"
app.secret_key = 'super secret key'
# indexes_eft_list = [
#     'SPLG',
#     'QQQM',
#     'DIA',
#     'IWM'
# ]
@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        user =  [user for user in users_list if user.id == session['user_id']][0]
        print('Establishing session for user',user)
        g.user = user
    else:
        g.user = None


@app.route('/login',methods = ['GET','POST'],endpoint='login')
def login():
    if request.method == 'POST':
        session.pop('user_id',None) #removing if already login
        username = request.form.get("username")
        password = request.form.get("password")
        user = [user for user in users_list if user.username == username] # only unique!
        if len(user) == 0:
            return redirect(url_for('index'))
        user = user[0]
        if user and (user.password == hashlib.sha512((password + user.salt).encode('utf-8')  ).hexdigest()): #right password
            print('Right password!')
            session['user_id'] = user.id
            return redirect(url_for('index')) #index page
        print('Wrong password!')
        return redirect(url_for('login'))
    return render_template('users/login.html')

@app.route("/logout")
def logout():
    g.user = None
    session.clear()
    return redirect(url_for('login'))

@app.route("/",endpoint='index',methods=['GET','POST','DELETE'])
def index_page():
    if not g.user:
        return redirect(url_for('login'))
    today =  date.today()
    current_data = datetime.now() + timedelta(days=0)
    indexes_to_add = []
    indexes_to_delete = []
    all_indexes = {}
    # error = None
    if request.method == 'POST' and request.form.get("delete_pressence") != 'delete': #why cant redirect?????????????????
        index_ticker = request.form.get("index_ticker")
        indexes_to_add.append(index_ticker) #add ticker
        full_data = filling_indexes_db(time0=current_data,
                                                    list_new_indexes=indexes_to_add)

        if full_data == 0: # error  - invalid symbol syntaxis
            error = 'Please enter a valid symbol'
            print('hahahahahahaha')
            # print(error)
            current_day_prices, last_day_prices, \
            count, data_historical = filling_indexes_db(time0=current_data,
                                                     list_new_indexes=[]) #dont add
            return render_template("index.html",
                                   current_day_prices=current_day_prices,
                                   last_day_prices=last_day_prices,
                                   length0=count,
                                   list_indexes=dumps(all_indexes), error=error)
        elif full_data == 1:# error - already added
            error = 'This stock has been already added'
            flash(error)
            current_day_prices, last_day_prices, \
            count, data_historical = filling_indexes_db(time0=current_data,
                                                        list_new_indexes=[])  # dont add
            return render_template("index.html",
                                   current_day_prices=current_day_prices,
                                   last_day_prices=last_day_prices,
                                   length0=count,
                                   list_indexes=dumps(all_indexes), error=error)

        else: # no errors
            current_day_prices, last_day_prices, \
            count, data_historical = full_data#filling_indexes_db(time0=current_data,
                                     #                   list_new_indexes=indexes_to_add)  # dont add
            indexes_to_add.clear()
            for n, (ticker, _) in enumerate(last_day_prices.items()):
                all_indexes[n + 1] = ticker
            error = None
            flash('Successfully added')
            return render_template("index.html",
                                   current_day_prices=current_day_prices,
                                   last_day_prices=last_day_prices,
                                   length0=count,
                                   list_indexes=dumps(all_indexes), error=error)
    elif request.method == 'GET':
        # error = request.args['error']  # counterpart for url_for()
        # if request.args.get('error') is not None:
        #     error = request.args['error']  # counterpart for url_for()
        # else:
        #     error = None
        current_day_prices, last_day_prices, \
        count, data_historical = filling_indexes_db(time0=current_data,
                                                    list_new_indexes=indexes_to_add)
        for n, (ticker,_) in enumerate(last_day_prices.items()):
            all_indexes[n+1] = ticker
        return render_template("index.html",
                               current_day_prices=current_day_prices,
                               last_day_prices = last_day_prices,
                               length0 = count,
                               list_indexes=dumps(all_indexes))


        # return render_template("index.html",
        #                        current_day_prices=current_day_prices,
        #                        last_day_prices=last_day_prices,
        #                        length0=count,
        #                        list_indexes=dumps(all_indexes),error=error)
    elif request.method == 'POST' and request.form.get("delete_pressence") == 'delete':
        index_ticker = request.form.get("index_ticker")

        if remove_indexes(index_ticker):
            # indexes_to_delete.append(index_ticker)
            # indexes_to_delete.clear()
            current_day_prices, last_day_prices, \
            count, data_historical = filling_indexes_db(time0=current_data,
                                                        list_new_indexes=indexes_to_add)
            for n, (ticker,_) in enumerate(last_day_prices.items()):
                all_indexes[n+1] = ticker
            return render_template("index.html",
                                   current_day_prices=current_day_prices,
                                   last_day_prices=last_day_prices,
                                   length0=count,
                                   list_indexes=dumps(all_indexes), error=None)
        else:
            error = 'There is not such stock in database'
            flash(error)
            current_day_prices, last_day_prices, \
            count, data_historical = filling_indexes_db(time0=current_data,
                                                        list_new_indexes=indexes_to_add)
            for n, (ticker, _) in enumerate(last_day_prices.items()):
                all_indexes[n + 1] = ticker
            return render_template("index.html",
                                   current_day_prices=current_day_prices,
                                   last_day_prices=last_day_prices,
                                   length0=count,
                                   list_indexes=dumps(all_indexes), error=error)
                    # return render_template("index.html",
        #                        current_day_prices=current_day_prices,
        #                        last_day_prices=last_day_prices,
        #                        length0=count,
        #                        list_indexes=dumps(all_indexes),error=error)
        #
        # return render_template("index.html",
        #                        current_day_prices=current_day_prices,
        #                        last_day_prices=last_day_prices,
        #                        length0=count,
        #                        list_indexes=dumps(all_indexes), error=None)

# @app.route('/remove',methods=[DELETE])
# def remove():

        # add tic
    #     if get_lastday_data(index_ticker) is None:
    #         raise NotAcceptable('There is no such ticker')
    #     elif index_ticker not in indexes_eft_list:
    #         indexes_eft_list.append(index_ticker)
    #         for index in indexes_eft_list:
    #             data0[index] = get_lastday_data(index)
    #         return redirect('/')
    #         # return render_template("index.html", indexes=data0)
    #     else:
    #         raise BadRequest('This index has been already added')




@app.route('/_add_numbers')
def add_numbers():
    # a = request.args.get('a', 0, type=int)
    # b = request.args.get('b', 0, type=int)
    # return jsonify(result=a + b)
    ticker = request.args.get('ticker')
    price = get_today_price(ticker)
    # return jsonify(
    #     ticker=ticker,
    #     price=price
    # )
    return jsonify(result=price)

@app.route('/plot/<string:index_ticker>/',endpoint='plot')
def plot(index_ticker):
    # index_ticker = 'AAPL'
    p = get_data_for_plotting_wrap(index_ticker)
    # html = file_html(p,CDN,'plot')
    # return html
    return dumps(json_item(p, "myplot"))

# @app.route('/plot')
# def plot():
#     index_ticker = 'AAPL'
#     p = get_data_for_plotting_wrap(index_ticker)
#     # html = file_html(p,CDN,'plot')
#     # return html
#     return dumps(json_item(p, "myplot"))


    # return render_template('test.html')
#
# @app.cli.command(help="create all tables")
# def create_all_tables():
#     with app.app_context():
#         migrate.init_app()
#         migrate.upgrade()


if __name__ == '__main__':
    app.run(use_reloader = True,debug=True, host="0.0.0.0", port="5000") #REQUIRED!
