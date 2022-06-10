#https://webdeasy.de/en/top-css-buttons-en/
import base64
from functools import wraps
from flask import Flask,render_template,flash,redirect, send_from_directory,url_for,session,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,PasswordField,validators,TextAreaField,SelectField
from passlib.handlers.sha2_crypt import sha256_crypt
import os
import datetime

app = Flask(__name__)

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "Blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
app.secret_key = "MySecret"

mysql = MySQL(app=app)
"Kayıt Form"
class RegisterForm(Form):
    name = StringField("İsim Soyisim:")
    username = StringField("Kullanıcı adı:",validators=[validators.DataRequired(message="Lütfen bir kullanıcı adı belirleyin")])
    email = StringField("Email Adresi:",validators=[validators.Email(message="Lütfen geçerli bir email adresi giriniz")])
    password = PasswordField("Şifreniz:",validators=[validators.DataRequired(message="Lütfen bir parola belirleyin"),validators.EqualTo(message="Parolanız uyuşmuyor",fieldname="confirm")])
    confirm = PasswordField("Parola doğrula")
"Giriş Form"
class LoginForm(Form):
    username = StringField(label="Kullanıcı Adı:",validators=[validators.data_required("Bu alan zorunludur")])
    password = PasswordField(label="Şifreniz:",validators=[validators.data_required("bu alan zorunludur")])
"Makale Form"
class ArticleForm(Form):
    title = StringField("Başlık:",validators=[validators.length(min=5,max=100),validators.DataRequired(message="Lütfen makaleniz için bir başlık belirleyin")])
    content = TextAreaField("İçerik:",validators=[validators.length(min=10)])
class Level():
    def __init__(self,point,currentlevel):
        self.point = point
        self.levelsUP = {"Çırak":"Hırslı","Hırslı":"Yıldız","Yıldız":"Yazar"}
        self.currentLevel = currentlevel
    def UpdatePoint(self,newValue,username):
        print("kerzo")
        self.point = newValue
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE users SET point = %s WHERE username = %s",(newValue,username,))
        cursor.execute("SELECT role FROM users WHERE username = %s",(username,))
        self.currentLevel = cursor.fetchone()["role"]
        mysql.connection.commit()
        self.CheckPoint(username)
    def LevelUp(self,username):
        self.currentLevel = self.levelsUP[self.currentLevel]
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE users SET role = %s WHERE username = %s",(self.currentLevel,username,))
        mysql.connection.commit()
    def CheckPoint(self,username):
        print(self.point,self.currentLevel)
        if self.currentLevel == "Çırak" and self.point >=100:
            self.LevelUp(username)
        elif self.currentLevel == "Hırslı" and self.point >=300:
            self.LevelUp(username)
        elif self.currentLevel == "Yıldız" and self.point >=600:
            self.LevelUp(username)
"Giriş Kontrol decorator"
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Lütfen önce giriş yapın","danger")
            return redirect(url_for("Login"))
    return decorated_function
def CheckUsername(username):
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM users WHERE username = %s",(username,))
    if result >0:
        return True
    else:
        return False
def Showing(role,point):
    if role == "Çırak":
            return point
    elif role == "Hırslı":
        return int((point - 100) / 2)
    elif role == "Yıldız":
        return int((point - 300)/3)
def DetectChanges(oldAverage,newAverage,artid):
    oldData = SelectState(oldAverage)
    newData = SelectState(newAverage)
    if oldData[1] != newData[1]:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = %s",(artid,))
        data = cursor.fetchone()
        author = data["author"]
        cursor.execute("SELECT * FROM users WHERE username = %s",(author,))
        user = cursor.fetchone()
        if data["Bonus"] == "" and data["Bonus"] != "++" and newData[1] == "trend" :
            text="""
Tebrikler {} adlı makalenizin genel yorumu trend seviyesine çıktı
+10 puan hesabınıza eklendi
            
            """.format(data["title"])
            cursor.execute("INSERT INTO news(username,content,Point) VALUES(%s,%s,%s)",(data["author"],text,10))
            cursor.execute("UPDATE articles SET Bonus = '++' WHERE author = %s",(data["author"],))
            level.UpdatePoint(user["point"]+10,data["author"])
        elif newData[1] == "iyi" and data["Bonus"] != "++" and data["Bonus"] !="+":
            text="""
Tebrikler {} adlı makalenizin genel yorumu iyi seviyesine çıktı
+5 puan hesabınıza eklendi
            
            """.format(data["title"])
            cursor.execute("INSERT INTO news(username,content,Point) VALUES(%s,%s,%s)",(data["author"],text,5))
            cursor.execute("UPDATE articles SET Bonus = '+' WHERE author = %s",(data["author"],))
            level.UpdatePoint(user["point"]+5,data["author"])
        mysql.connection.commit()
@login_required
def AddComment(id):
    comment = request.form.get("comment")
    rate = request.form.get("rate")
    try:
        rate = int(rate) * "⭐"
    except:
        rate = ""
    
    cursor = mysql.connection.cursor()
    oldAverage = RateAverage(id)
    query = "INSERT INTO comments(author,content,article,rate,authorPP) VALUES(%s,%s,%s,%s,%s)"
    cursor.execute(query,(session["user_name"],comment,id,rate,RequiredFoto()))      
    mysql.connection.commit()
    cursor.close()
    newAverage = RateAverage(id)
    DetectChanges(oldAverage,newAverage=newAverage,artid=id)
    return redirect("/article"+id)  
def SelectState(Average):
    if type(Average) == tuple:
        Average = float(Average[0])
    if Average == 0:
        state = "Puan verilmiş bir yorum yok" 
    elif Average < 1.5:
        state = "kötü"
    elif Average < 4:
        state = "iyi"
    else:
        state = "trend"
    return Average,state
def DailyPointIncreasing(data):
    cursor = mysql.connection.cursor()
    splitter = data["last_entred"].split("-")
    year = int(splitter[0])
    month = int(splitter[1])
    day = int(splitter[2])
    last_entred = datetime.datetime(year,month,day)
    now = datetime.datetime.now().date()
    if last_entred.date() < now and session["role"] != "admin":
        session["point"] += 5
        level.UpdatePoint(session["point"],session["user_name"])
        cursor.execute("UPDATE users SET last_entred = %s WHERE username =%s",(datetime.datetime.now().date(),data["username"],))
        mysql.connection.commit()
        flash("Günlük Giriş Puanınız hesabınıza eklendi +5","success")
def RateAverage(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT rate FROM comments WHERE article = %s",(id,))
    comments = cursor.fetchall()
    totalStar = 0
    num = 0
    for dicte in comments:
        if len(dicte["rate"]):
            totalStar += int(len(dicte["rate"]))
            num +=1
    try:
        Average = totalStar / num
    except ZeroDivisionError:
        Average = 0
    cursor.execute("UPDATE articles set rateAverage = %s where id = %s",(Average,id))
    mysql.connection.commit()
    return SelectState(Average)
def Check(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM comments WHERE article = %s and author = %s"
    result = cursor.execute(query,(id,session["user_name"]))
    if result == 0:
        return True
    else:
        return False
def AddFoto():
    cursor = mysql.connection.cursor()
    Foto = request.files["image"]
    Foto_64 = base64.b64encode(Foto.read()).decode("utf-8")
    cursor.execute("UPDATE users SET pp = %s WHERE username = %s",(Foto_64,session["user_name"],))
    cursor.execute("UPDATE comments set authorPP = %s WHERE author = %s",(Foto_64,session["user_name"],))
    mysql.connection.commit()
    return Foto_64
def RequiredFoto():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT pp FROM users WHERE username = %s",(session["user_name"],))
    data = cursor.fetchone()
    pp = data["pp"]
    return pp
def News():
    cursor = mysql.connection.cursor()
    Banned = cursor.execute("SELECT * FROM warnban WHERE receiver = %s and Type = 'Ban'",(session["user_name"],))
    if Banned > 0:
        Ban = cursor.fetchone()
        BanLastDay = str(Ban["BanLastDay"])
        splitter = BanLastDay.split("-")
        try:
            year = int(splitter[0])
            month = int(splitter[1])
            day = int(splitter[2])
            BanDate = datetime.datetime(year,month,day)
            today = datetime.datetime.now()
            if BanDate <= today:
                cursor.execute("DELETE from warnban WHERE receiver = %s and Type = 'Ban'",(session["user_name"],))
                mysql.connection.commit()
                return render_template("index.html")
        except ValueError:
            return render_template("index.html",Ban=Ban)
    Warned = cursor.execute("SELECT * FROM warnban WHERE receiver = %s and warnState = %s",(session["user_name"],"False"))
    warns = cursor.fetchall()
    rereportedNew = cursor.execute("SELECT * FROM rereports WHERE receiver = %s and readState = %s",(session["user_name"],False))
    rereports = cursor.fetchall()
    newsS = cursor.execute("SELECT * FROM news WHERE username = %s and readState = %s",(session["user_name"],False))
    news = cursor.fetchall()
    Bonus = cursor.execute("SELECT * FROM news WHERE username = 'all'")
    added = cursor.fetchall()
    added = list(added)
    added.append(news)
    news = added
    if Warned == 0 and rereportedNew == 0 and newsS == 0 and Bonus == 0 :
        return render_template("index.html")

    elif len(warns) != 0 and len(rereports) == 0 and len(news) == 0:
        return render_template("index.html",warns=warns)

    elif len(rereports) != 0 and len(warns) == 0 and len(news) == 0:
        return render_template("index.html",rereports=rereports)

    elif len(news) != 0 and len(warns) == 0 and len(rereports) == 0:
        return render_template("index.html",news=news)

    elif len(rereports) != 0 and len(warns) != 0 and len(news) == 0:
        return render_template("index.html",rereports=rereports,warns=warns)

    elif len(news) != 0 and len(warns) == 0 and len(rereports) != 0:
        return render_template("index.html",news=news,rereports=rereports)

    elif len(rereports) == 0 and len(warns) != 0 and len(news) != 0:
        return render_template("index.html",news=news,warns=warns)

    else:
        
        return render_template("index.html",rereports=rereports,warns=warns)
def RoleGenerator(role):
    letters = list()
    if role == "admin":
        for string in role:
            if string == role[0]:
                string = '<h5 style="font-size:24px;color:#DC143C;">'+string
            letters.append(string)
        role = ""
        for letter in letters:
            role +=letter
        role+="</h5>"
    elif role == "Çırak":
        for string in role:
            if string == role[0]:
                string = '<h5 style="font-size:24px;color:#1BCE45;">'+string
            letters.append(string)
        role = ""
        for letter in letters:
            role +=letter
        role+="</h5>"
    elif role=="Hırslı":
        for string in role:
            if string == role[0]:
                string = '<h5 style="font-size:24px;color:#ff8700;">'+string
            letters.append(string)
        role = ""
        for letter in letters:
            role +=letter
        role+="</h5>"
    elif role=="Yıldız":
        for string in role:
            if string == role[0]:
                string = '<h5 style="font-size:24px;color:#02ada9;">'+string
            letters.append(string)
        role = ""
        for letter in letters:
            role +=letter
        role+="</h5>"
    elif role=="Yazar":
        for string in role:
            if string == role[0]:
                string = '<h5 style="font-size:24px;color:#870000;">'+string
            letters.append(string)
        role = ""
        for letter in letters:
            role +=letter
        role+="</h5>"
    return role 
@app.route("/",methods=["GET","POST"])
def index():
    cursor = mysql.connection.cursor()
    if request.method == "GET":
        try:
            return News()
        except KeyError:
            return render_template("index.html")
    else:
        cursor.execute("UPDATE warnban SET warnState = True  WHERE receiver = %s and warnState = False ",(session["user_name"],))
        cursor.execute("UPDATE rereports SET readState = True WHERE receiver = %s and readState = False",(session["user_name"],))
        cursor.execute("UPDATE news SET readState = True WHERE username = %s and readState = False",(session["user_name"],))
        mysql.connection.commit()
        return render_template("index.html")
        
@app.route("/about")
def about():
    return render_template("about.html")
@app.route("/register",methods=["GET","POST"])
def Register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        if CheckUsername(username):
            cursor.close()
            flash("Bu kullanıcı adı daha önceden alınmış Başka bir ad deneyin","danger")
            return redirect(url_for("Register"))
        sorgu = "INSERT INTO users(name,username,email,password,role) VALUES(%s,%s,%s,%s,'Çırak')"
        cursor.execute(sorgu,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla kayıt oldunuz","success")
        return redirect(url_for("Login"))
    else:
        return render_template("register.html",form=form)
@app.route("/login",methods=["GET","POST"])
def Login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password = form.password.data
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(query,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password,real_password):
                session["logged_in"] = True
                session["user_name"] = username
                session["role"] = data["role"]
                session["point"] = data["point"]
                session["about"] = data["about"]
                global level
                level = Level(data["point"],data["role"])
                #Daily Point increasing
                DailyPointIncreasing(data)
                return redirect(url_for("index"))

            else:
                flash("Kullanıcı adıyla şifre uyuşmuyor tekrar deneyiniz","danger")
                return redirect(url_for("Login"))
        else:
            flash("Böyle bir kullanıcı yok!","danger")
            return redirect(url_for("Login")) 
    else:
        return render_template("login.html",form=form)
@app.route("/dashbord",methods=["GET","POST"])
@login_required
def DashBord():
    if session["role"] != "admin":
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s",(session["user_name"],))
        user = cursor.fetchone()
        img64 = user["pp"]
        if request.method == "POST":
            img64 = AddFoto()
        result = cursor.execute("SELECT * FROM articles WHERE author = %s",(session["user_name"],))
        articles = cursor.fetchall()
        point = Showing(point=session["point"],role=session["role"])
        conc = RoleGenerator(user["role"])
        if result >0:
            return render_template("dashbord.html",articles=articles,image=img64,point=point,conc=conc)
        else:
            return render_template("dashbord.html",image=img64,point=point,conc=conc)
    else:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT pp FROM users WHERE username = %s",(session["user_name"],))
        pp = cursor.fetchone()
        img64 = pp["pp"]
        if request.method == "POST":
            img64 = AddFoto()
        result = cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        result2 = cursor.execute("SELECT * FROM reports")
        reports = cursor.fetchall()
        result3 = cursor.execute("SELECT * FROM warnban")
        warnban = cursor.fetchall()
        result4 = cursor.execute("SELECT * FROM news WHERE username = 'all'")
        news = cursor.fetchall()
        if result <0 and result2 <0 and result3<0 and result4<0 :
            return render_template("dashbord.html",image=img64)
        else:
            return render_template("dashbord.html",anoncts=news,users=users,reports=reports,warnban=warnban,image=img64)
@app.route("/addarticle",methods=["GET","POST"])
def Addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        query = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(query,(title,session["user_name"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla eklendi","success")
        return redirect(url_for("DashBord"))
    else:
        return render_template("addarticle.html",form=form)
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles ORDER BY rateAverage DESC"
    result = cursor.execute(query)
    if result > 0:
        articles = cursor.fetchall() 
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")
@app.route("/article<string:id>",methods=["GET","POST"])
def Article(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE id = %s"
        result = cursor.execute(query,(id,))
        #Makale Varsa
        if result > 0:
            article = cursor.fetchone()
            query2 = "SELECT * FROM comments WHERE article = %s ORDER BY rate"
            result = cursor.execute(query2,(id,))
            #Yorum Varsa
            if result >0:
                try:
                    commentState = Check(id)
                except KeyError:
                    commentState = True
                finally:
                    comments = cursor.fetchall()
                    data = RateAverage(id)
                    Average = data[0]
                    state = data[1]
                    return render_template("article.html",article=article,comments=comments,state=state,Average=Average,commentState=commentState)
            else:
                commentState = True
                state = "Yorum Yok"
                Average = "Yorum Yok"
                return render_template("article.html",state=state,Average=Average,article=article,commentState=commentState)    
        else:
            return render_template("article.html")
    else:
        return AddComment(id)
@app.route("/delete/<string:id>")
def DeleteArticle(id):
    cursor = mysql.connection.cursor()
    query = "DELETE FROM articles WHERE id = %s"
    cursor.execute(query,(id,))
    cursor.execute("DELETE FROM comments WHERE article = %s",(id,))
    mysql.connection.commit()
    cursor.close()
    flash("Makale Başarıyla silindi","success")
    return redirect(url_for("DashBord"))
@app.route("/edit/<string:id>",methods=["GET","POST"])
def EditAritcle(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE id = %s and author = %s"
        result = cursor.execute(query,(id,session["user_name"]))
        if result == 0:
            flash("Böyle bir makale yok veya Bu işleme yetkiniz yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form)
    else:
        cursor = mysql.connection.cursor()
        form = ArticleForm(request.form)
        title = form.title.data
        content = form.content.data
        query = "UPDATE articles set title=%s,content=%s Where id = %s"
        cursor.execute(query,(title,content,id))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("DashBord"))
@app.route("/search",methods=["GET","POST"])
def Search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE title like '%"+keyword+"%'"
        result = cursor.execute(query)
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)
#Profiles
@app.route("/user/<string:username>")
def Profile(username):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM users WHERE username = %s"
    result = cursor.execute(query,(username,))
    if result < 0:
        return render_template("profile.html")
    else:
        user = cursor.fetchone()
        Conc = RoleGenerator(user["role"])
        cursor.execute("SELECT about FROM users WHERE username = %s",(username,))
        about = cursor.fetchone()
        result = cursor.execute("SELECT * FROM articles WHERE author = %s",(username,))
        point = Showing(point=user["point"],role=user["role"])
        if result >0:
            articles = cursor.fetchall()
            return render_template("profile.html",user=user,articles=articles,about=about["about"],point=point,conc=Conc)
        else:
            return render_template("profile.html",user=user,about=about["about"],point=point,conc=Conc)
@app.route("/deleteComment<comid>/<artid>")
def DeleteComment(comid,artid):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM comments WHERE id = %s",(comid,))
    data = cursor.fetchone()
    if data["author"] == session["user_name"]:
        cursor.execute("DELETE FROM comments WHERE  id = %s",(comid,))
        mysql.connection.commit()
        flash("Yorum Silme işlemi Başarılı","success")
        return redirect("/article"+artid)
    else:
        flash("Üzgünüm bu işleme yetkiniz yok")
        return redirect(url_for("DashBord"))
@app.route("/reportcomment<comid><artid>",methods=["GET","POST"])
@login_required
def ReportComment(comid,artid):
    if request.method == "GET":    
        reason = request.args.get("reason")
        attachment = request.args.get("attachment")
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT content FROM comments WHERE id = %s",(comid,))
        comment = cursor.fetchone()
        cursor.execute("INSERT INTO reports(sender,reported,reportType,reason,attachment) VALUES(%s,%s,%s,%s,%s)",(session["user_name"],comment["content"],"yorum",reason,attachment))
        mysql.connection.commit()
        flash("Bu Yorum başarıyla raporlandı","success")
        return redirect("/article"+artid)
@app.route("/warn/<username>")
@login_required
def WarnUser(username):
    if session["role"] == "admin":
        reason = request.args.get("reason")
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO warnBan(admin,receiver,Type,reason) VALUES(%s,%s,%s,%s)",(session["user_name"],username,"Warn",reason))
        mysql.connection.commit()
        flash("Uyarı Başarı ile yapıldı","success")
        return redirect(url_for("DashBord"))
    else:
        flash("Bu işleme yetkiniz Yok","danger")
        return redirect("/dashbord")
@app.route("/ban/<string:username>",methods=["GET","POST"])
@login_required
def BanUser(username):
    if session["role"] == "admin":
        cursor = mysql.connection.cursor()
        result = cursor.execute("SELECT * FROM warnban WHERE receiver = %s and Type = %s",(username,"Ban"))
        if result >0:
            flash("Bu kullanıcı zaten yasaklı","danger")
            return redirect("/dashbord")
        inf = request.args.get("inf")
        inf = bool(inf)
        lastDay = request.args.get("lastDay")
        reason = request.args.get("attachment")
        if inf:
            query = "INSERT warnban(admin,receiver,Type,reason,BanLastDay) VALUES(%s,%s,'Ban',%s,'perma')"
            cursor.execute(query,(session["user_name"],username,reason))
            mysql.connection.commit()
        else:
            lastDayr = ""
            for i in lastDay:
                if i != "":
                    lastDayr +=i
                else:
                    break
            query = "INSERT warnban(admin,receiver,Type,reason,BanLastDay) VALUES(%s,%s,'Ban',%s,%s)"
            cursor.execute(query,(session["user_name"],username,reason,lastDayr))
            mysql.connection.commit()
        flash("İşleminiz Başarılı","success")
        return redirect("/dashbord")
    else:
        flash("Bu işleme yetkiniz Yok","danger")
        return redirect("/dashbord")
@app.route("/deletereport<id>")
def DeleteReport(id):
    if session["role"] == "admin":
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM reports WHERE id = %s",(id,))
        mysql.connection.commit()
        flash("Şikayet Silme Başarı ile tamamlandı")
        return redirect("/dashbord")
    else:
        flash("Bu işleme yetkiniz Yok","danger")
        return redirect("/dashbord")
@app.route("/SendRereport<id>")
def SendRereport(id):
    if session["role"] == "admin":
        cursor = mysql.connection.cursor()
        result = cursor.execute("SELECT * FROM reports WHERE id = %s",(id,))
        if result <0:
            flash("Böyle bir şikayet bulunamadı","danger")
            return redirect(url_for("dashbord"))
        else:
            reported = cursor.fetchone()
            content = """
        Sayın {0}
        {1} tarihinde yaptığınız 
        şikayet incelenmiştir ve topluluk kurallarına uyumsuzluk tespit edilmiştir.
        Yardımlarınız için teşekkür ederiz\n           
            
            Admin {2}
            """.format(reported["sender"],reported["reported_date"],session["user_name"])
            cursor.execute("INSERT INTO rereports(admin,receiver,content,reportedid) VALUES(%s,%s,%s,%s)",(session["user_name"],reported["sender"],content,id))
            cursor.execute("DELETE FROM reports WHERE id = %s",(id,))
            mysql.connection.commit()
            cursor.close()

            flash("geri bildirim başarı ile gönderildi","success")
            return redirect("/dashbord")
    else:
        flash("Bu işleme yetkiniz Yok","danger")
        return redirect("/dashbord")
@app.route("/deletereport<id>")
def DelReport():
    if session["role"] == "admin":
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM reports WHERE id = %s",(id,))
        mysql.connection.commit()
        flash("Rapor silme işlemi başarılı","success")
        return redirect("/dashbord")
    else:
        flash("Bu işleme yetkiniz Yok","danger")
        return redirect("/dashbord")
@app.route("/deleteWarn<id>")
def DelWarn(id):
    if session["role"] == "admin":
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM warnban WHERE id = %s",(id,))
        mysql.connection.commit()
        flash("Uyarı başarı ile silindi","success")
        cursor.close()
        return redirect(url_for("index"))
    else:
        flash("Bu işleme yetkiniz Yok","danger")
        return redirect("/dashbord")
@app.route("/deleteBan<id>")
def DelBan(id):
    if session["role"] == "admin":
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM warnban WHERE id = %s",(id,))
        mysql.connection.commit()
        flash("Ban başarı ile kaldırıldı","success")
        cursor.close()
        return redirect(url_for("DashBord"))
    else:
        flash("Bu işleme yetkiniz Yok","danger")
        return redirect("/dashbord")
@app.route("/addabout")
@login_required
def AddAbout():
    about = request.args.get("about")
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE users set about = %s WHERE username =%s",(about,session["user_name"]))
    mysql.connection.commit()
    session["about"] = about
    return redirect("/dashbord")
@app.route("/makeAnonct")
def Anonct():
    if session["role"] == "admin":
        cursor = mysql.connection.cursor()
        content = request.args.get("anonct")
        cursor.execute("INSERT INTO news(username,content) VALUES(%s,%s)",("all",content))
        mysql.connection.commit()
        flash("Duyuru Başarı ile Yapıldı","success")
        return redirect(url_for("DashBord"))
    else:
        flash("Üzgünüm Bu işleme yetkiniz Yok","danger")
        return redirect(url_for("DashBord"))
@app.route("/deleteAnonct<id>")
def DelAnonct(id):
    if session["role"] == "admin":
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM news WHERE id = %s",(id,))
        mysql.connection.commit()
        flash("Duyuru Başarı ile silindi","success")
        return redirect(url_for("DashBord"))
        
    else:
        flash("Üzgünüm Bu işleme yetkiniz yok","danger")
        return redirect(url_for("DashBord"))
@app.route("/logout")
def Logout():
    session.clear()
    return redirect(url_for("index"))
if __name__ == "__main__":
    app.run(debug=False)