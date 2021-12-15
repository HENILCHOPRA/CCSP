import os
import sys
from datetime import datetime

from data import select_query, insert_query, proc_query

from datetime import timedelta, datetime
from flask import Flask, render_template, request, session, redirect, url_for, Response, jsonify, send_from_directory, flash
import random
import pickle

module_directory = os.path.dirname(os.path.realpath(__file__))
template_folder = os.path.join(module_directory, 'templates')
static_folder = os.path.join(module_directory, 'assets')
application = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

application.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


clusterdict = pickle.load(open("clusterdict.pickle", "rb"))

model = pickle.load(open("model.pkl", "rb"))

cluster_data = pickle.load(open("df.pickle", "rb"))

@application.before_request
def make_session_permanent():
    session.permanent = True
    application.permanent_session_lifetime = timedelta(minutes=30)

def get_recent_act_data():
    start_data = select_query("SELECT userID, endDate,0, instanceType FROM subscription join instance on instance.instanceID = subscription.instanceID order by endDate desc limit 3")
    end_data = select_query("SELECT userID, startDate,1, instanceType FROM subscription join instance on instance.instanceID = subscription.instanceID order by startDate desc limit 3")

    start_data.extend(end_data)
    start_data.sort(key=lambda x: x[2])

    return start_data

def get_aggre_data():
    month = 11 #datetime.now().month
    year = datetime.now().year
    revenue = select_query("SELECT sum(amount) FROM billing where Month(billDate) = %s and Year(billDate) =%s;",(month, year))[0][0]
    sales = select_query("SELECT count(*) FROM subscription where Month(startDate) = %s and Year(startDate) = %s;",(month, year))[0][0]
    terminated = select_query("SELECT count(*) FROM subscription where Month(startDate) = %s and Year(startDate) = %s and endDate != '0000-00-00 00:00:00';",(month, year))[0][0]

    revenue_ = select_query("SELECT sum(amount) FROM billing where Month(billDate) = %s and Year(billDate) =%s;",(month-1, year))[0][0]
    sales_ = select_query("SELECT count(*) FROM subscription where Month(startDate) = %s and Year(startDate) = %s;",(month-1, year))[0][0]
    terminated_ = select_query("SELECT count(*) FROM subscription where Month(startDate) = %s and Year(startDate) = %s and endDate != '0000-00-00 00:00:00';",(month-1, year))[0][0]
    try:
        change_revenue = ((revenue_ - revenue) // revenue )*100
    except:
        change_revenue = 0
    try:
        change_sales = ((sales_ - sales) // sales )*100
    except:
        change_sales = 0
    try:
        change_terminated = ((terminated_ - terminated) // terminated )*100
    except:
        change_terminated = 0
    return [revenue, change_revenue, sales, change_sales, terminated, change_terminated]

def get_report_chart_data():
    year = datetime.now().year
    res = select_query("SELECT count(*) FROM subscription where Year(startDate) = %s GROUP BY MONTH(startDate) order by Month(startDate);",(year,))
    sales = []
    for r in res:
        sales.append(r[0])

    res = select_query("SELECT count(*) FROM subscription where Year(startDate) = %s and endDate != '0000-00-00 00:00:00' GROUP BY MONTH(startDate) order by Month(startDate);",(year,))
    terminations = []
    for r in res:
        terminations.append(r[0])

    res = select_query("SELECT sum(amount) FROM billing where Year(billDate) = %s GROUP BY MONTH(billDate) order by Month(billDate);",(year,))
    revenue = []
    for r in res:
        revenue.append(int(r[0]/1000))

    return [sales, revenue, terminations]

def get_recent_chart_data():
    res = select_query("SELECT subscription.userID, instance.instanceID, instance.instanceType, subscription.startDate FROM subscription join instance on instance.instanceID = subscription.instanceID where endDate = '0000-00-00 00:00:00' order by startDate desc limit 100;")
    return res

def get_top_chart_data():
    computing = select_query("""select * from top5SellingComputing;""")
    storage = select_query("""select * from top5SellingStorage;""")
    return {'computing': computing, 'storage':storage}

def get_spider_data():
    com_query = """select ins.computeID, count(1) from logs lg natural join instance ins where ins.instanceType = "COM" and lg.errorCode = 500 group by ins.computeID order by count(1) desc limit 6;"""
    sto_query = """select ins.storageID, count(1) from logs lg natural join instance ins where ins.instanceType = "STO" and lg.errorCode = 500 group by ins.storageID order by count(1) desc limit 6;"""
    com_data = select_query(com_query)
    sto_data = select_query(sto_query)
    com_indicator = [c[0] for c in com_data]
    sto_indicator = [s[0] for s in sto_data]
    com_data = [c[1] for c in com_data]
    sto_data = [s[1] for s in sto_data]
    return [com_indicator, com_data, sto_indicator, sto_data]
    
def get_userID(authID):
    userId_query = """SELECT userID FROM user usr natural join authorization aut where aut.authID = %s;"""
    return select_query(userId_query, (authID,))[0]

def get_subs(userID):
    subs_query = """SELECT subscriptionID, startDate, endDate FROM subscription where userID = %s order by startDate desc;"""
    return select_query(subs_query, (userID,))

def get_bills(userID, subs):
    bills_query = f"""SELECT billID, amount, billDate, dueDate FROM billing where subscriptionID in {tuple(subs)} order by billDate desc;"""
    return select_query(bills_query.replace("'",'"'))

def get_clusterID(budget):
    return model.predict([[budget]])[0]

def get_cluster_services(clusterID):
    compute_query = f"""SELECT distinct(computeID), coreCount, ram, gpu, price from computesubs where userID in {tuple(clusterdict[clusterID])};"""
    storage_query = f"""SELECT distinct(storageID), size,type, price from storagesubs where userID in {tuple(clusterdict[clusterID])};"""
    compute_data = select_query(compute_query)
    storage_data = select_query(storage_query)
    return compute_data, storage_data

@application.route('/')
@application.route('/login', methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        login_query = 'SELECT * FROM authorization WHERE userName = %s AND password = %s'
        account = select_query(login_query, (username, password, ))

        if account != None and len(account) >0:
            session['loggedin'] = True
            #session['id'] = account['authID']
            session['username'] = account[0][1]
            if username == 'admin':
                return redirect(url_for('dashboard'))
            else:
                session['userID'] = get_userID(account[0][0])[0]
                return redirect(url_for('profile'))
        else:
            msg = 'Incorrect username / password !'
            flash(msg,'error')
    return render_template('pages-login.html')

@application.route('/profile', methods =['GET', 'POST'])
def profile():
    userID = session['userID']
    username = session['username']
    subs_data = get_subs(userID)

    if subs_data == None: subs_data = []
    else:pass
    return render_template('users-profile.html', values = {'username': username, 'subs_data': subs_data},
        unauthorized=False)

@application.route('/cancelsub', methods =['GET'])
def cancelsub():
    subID = request.args['subID']
    proc_query('cancelSubscription', [subID])
    msg = 'error'
    flash(msg,'error')
    return redirect(url_for('profile'))

def profile():
    userID = session['userID']
    username = session['username']
    subs_data = get_subs(userID)
    return render_template('users-profile.html', values = {'username': username, 'subs_data': subs_data},
        unauthorized=False)

@application.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'name' in request.form and 'contact' in request.form and 'paymentMethod' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        contact = request.form['contact']
        paymentMethod = request.form['paymentMethod']

        reg_query = 'SELECT * FROM authorization WHERE userName = %s'
        account = select_query(reg_query, (username, ))
        if account != None and len(account) >1:
            msg = 'Account already exists !'
        else:

            proc_query('generateUserAccount', [username, password, email, name, contact, paymentMethod])            
            msg = 'You have successfully registered !'
            session['loggedin'] = True
            #session['id'] = account['authID']
            session['username'] = username
            return redirect(url_for('login'))
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('pages-register.html', msg = msg)

@application.route('/dashboard')
def dashboard():
    recent_act_data = get_recent_act_data()
    aggre_data = get_aggre_data()
    report_chart_data = get_report_chart_data()
    recent_chart_data = get_recent_chart_data()
    top_chart_data = get_top_chart_data()
    spider_data = get_spider_data()
    return render_template('index.html', values = {'aggre_data': aggre_data,'recent_data': recent_act_data, 
        'report_chart_data': report_chart_data,'recent_chart_data': recent_chart_data, 'top_chart_data': top_chart_data, 
        'spider_data': spider_data, 'cluster_data': cluster_data},
        unauthorized=False)

@application.route('/userDashboard')
def userDashboard():
    recent_act_data = get_recent_act_data()
    aggre_data = get_aggre_data()
    report_chart_data = get_report_chart_data()
    recent_chart_data = get_recent_chart_data()
    top_chart_data = get_top_chart_data()
    spider_data = get_spider_data()
    return render_template('index.html', values = {'aggre_data': aggre_data,'recent_data': recent_act_data, 
        'report_chart_data': report_chart_data,'recent_chart_data': recent_chart_data, 'top_chart_data': top_chart_data, 
        'spider_data': spider_data},
        unauthorized=False)

@application.route('/subscribe')
def subscribe():   
    return render_template('subscribe-page.html')

@application.route('/add_storage', methods =['GET', 'POST'])
def add_storage():
    msg=''
    if request.method=='GET':
        size=request.args['size']
        price=request.args['price']
        type_=request.args['type']

        sub = select_query('SELECT * FROM storage WHERE price = %s', (price, ))
        
        if sub != None and len(sub)>0:
            msg='Service Exists'
            proc_query('addStorage', [session['userID'],size, price, type_])
            msg = 'You have successfully subscribed!'
        else:
            msg = 'Not subscribed'
    else:
        msg='subscription Error'
    return redirect(url_for('storage'))

@application.route('/add_compute', methods =['GET', 'POST'])
def add_compute():
    msg=''
    if request.method=='GET':
        coreCount=request.args['coreCount']
        ram=request.args['ram']
        gpu=request.args['gpu']
        price=request.args['price']


        sub = select_query('SELECT * FROM computing WHERE price = %s', (price, ))
        print(str(session['userID']), coreCount, ram, gpu,price)
        if sub != None and len(sub)>0:
            msg='Service Exists'
            proc_query('addComputing', [str(session['userID']),coreCount, ram, gpu, price])
            msg = 'You have successfully subscribed!'

        else:
            msg = 'Not subscribed'
        print(msg)
    else:
        msg='subscription Error'
    return redirect(url_for('compute'))
             
@application.route('/storage', methods =['GET', 'POST'])
def storage():   
    data = select_query("SELECT size, type, price FROM storage WHERE size <> 0 ORDER BY price ASC")
    return render_template('storage-data.html', data=data)

@application.route('/compute', methods =['GET', 'POST'])
def compute():
    data = select_query("SELECT coreCount, ram, gpu, price FROM computing WHERE ram <> 0 ORDER BY price ASC")
    return render_template('compute-data.html', data=data)

@application.route('/bills', methods =['GET', 'POST'])
def bills():
    userID = session['userID']
    username = session['username']
    subs_data = get_subs(userID)
    subs = [r[0] for r in subs_data]
    bills_data = get_bills(userID, subs)
    return render_template('bills.html', values = {'username': username, 'bills_data': bills_data},
        unauthorized=False)

@application.route('/signout', methods =['GET', 'POST'])
def signout():
    try:
        session.pop('username')
    except:
        pass
    session['loggedin'] = False
    return redirect(url_for('login'))  

@application.route('/getpredicts', methods =['GET'])
def getpredicts():
    userID = session['userID']
    username = session['username']
    budget = int(request.args['budget'])
    suggested_data = get_cluster_services(get_clusterID(budget)) 
    subs_data = get_subs(userID)
    return render_template('users-profile.html', values = {'username': username, 'subs_data': subs_data,
                                                             "suggested_data": suggested_data},
                                                unauthorized=False)

if __name__ == '__main__':
    application.run(host='10.110.9.191', port=80, threaded=True, debug=True)
    