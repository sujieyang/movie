# coding:utf8
from . import home
from flask import render_template, redirect, url_for, flash, session, request, Response
from werkzeug.security import generate_password_hash
from app.models import User, Userlog, Preview, Tag, Movie, Comment, Moviecol
from app.home.forms import RegistForm, LoginForm, UserdetailForm, PwdForm, CommentForm
from app import db, app, rd
import uuid, os, datetime
from werkzeug.utils import secure_filename
from functools import wraps


# 登录装饰器
def user_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("home.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# 修改文件名称
def change_filename(filename):
    fileinfo = os.path.splitext(filename)
    filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4().hex) + fileinfo[-1]
    return filename


# 会员登录
@home.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        data = form.data
        user = User.query.filter_by(name=data['name']).first()
        if not user.check_pwd(data['pwd']):
            flash("密码错误！", "err")
            return redirect(url_for('home.login'))
        # 将登录成功后的用户名以及用户id保存到session会话机制中
        session['user'] = user.name
        session['user_id'] = user.id
        # 将登陆操作保存到会员日志中
        userlog = Userlog(
            user_id=user.id,
            ip=request.remote_addr
        )
        db.session.add(userlog)
        db.session.commit()
        return redirect(url_for('home.user'))  # 跳转到会员中心
    return render_template("home/login.html", form=form)


# 会员退出
@home.route('/logout/')
@user_login_required
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    return redirect(url_for("home.login"))


# 会员注册
@user_login_required
@home.route('/regist/', methods=['GET', 'POST'])
def regist():
    form = RegistForm()
    if form.validate_on_submit():
        data = form.data
        user = User(
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            pwd=generate_password_hash(data["pwd"]),
            uuid=uuid.uuid4().hex
        )
        db.session.add(user)
        db.session.commit()
        flash("会员注册成功", "ok")
    return render_template("home/regist.html", form=form)


# 会员详情
@home.route('/user/', methods=['GET', 'POST'])
@user_login_required
def user():
    form = UserdetailForm()
    form.face.validators = []  # 默认图片为空
    user = User.query.get(int(session['user_id']))
    # 设置表单字段初始值
    if request.method == 'GET':
        form.name.data = user.name
        form.email.data = user.email
        form.phone.data = user.phone
        form.info.data = user.info
    if form.validate_on_submit():
        data = form.data
        file_face = secure_filename(form.face.data.filename)  # 获取上传图片文件名
        if not os.path.exists(app.config["FC_DIR"]):  # 文件夹不存在
            os.makedirs(app.config["FC_DIR"])  # 创建多级目录
            os.chmod(app.config["FC_DIR"], "rw")  # 赋予文件读写的权限
        user.face = change_filename(file_face)  # 返回加密后的图片文件名
        # 将url和logo数据写入到static/uploads/目录的filename文件中
        form.face.data.save(app.config["FC_DIR"] + user.face)
        # 判断用户修改的name email phone是否已经存在
        name_count = User.query.filter_by(name=data["name"]).count()
        if name_count == 1 and user.name != data['name']:
            flash("账号已存在！", "err")
            return redirect(url_for('home.user'))
        email_count = User.query.filter_by(email=data["email"]).count()
        if email_count == 1 and user.email != data['email']:
            flash("邮箱已存在！", "err")
            return redirect(url_for('home.user'))
        phone_count = User.query.filter_by(phone=data["phone"]).count()
        if phone_count == 1 and user.phone != data['phone']:
            flash("号码已存在！", "err")
            return redirect(url_for('home.user'))
        # 更新数据
        user.name = data['name']
        user.email = data['email']
        user.phone = data['phone']
        user.info = data['info']
        db.session.add(user)
        db.session.commit()
        flash("修改会员信息成功", "ok")
        return redirect(url_for('home.user'))
    return render_template("home/user.html", form=form, user=user)


# 修改密码
@home.route('/pwd/', methods=['GET', 'POST'])
@user_login_required
def pwd():
    form = PwdForm()
    if form.validate_on_submit():
        data = form.data
        user = User.query.filter_by(name=session['user']).first()
        user.pwd = generate_password_hash(data['new_pwd'])
        db.session.add(user)
        db.session.commit()
        flash("修改密码成功，请重新登录", "ok")
        return redirect(url_for('home.logout'))
    return render_template("home/pwd.html", form=form)


# 会员评论记录
@home.route('/comments/<int:page>/')
@user_login_required
def comments(page=None):
    if page == None:
        page = 1
    page_data = Comment.query.join(Movie).join(User).filter(
        Movie.id == Comment.movie_id,
        User.id == session['user_id']
    ).order_by(Comment.addtime.desc()).paginate(page=page, per_page=5)
    return render_template("home/comments.html", page_data=page_data)


# 会员登录日志
@home.route('/loginlog/<int:page>')
@user_login_required
def loginlog(page):
    if page == None:
        page = 1
    page_data = Userlog.query.filter_by(
        user_id=int(session['user_id'])
    ).order_by(Userlog.addtime.desc()).paginate(page=page, per_page=10)
    return render_template("home/loginlog.html", page_data=page_data)


# 电影收藏
@home.route('/moviecol/<int:page>/')
@user_login_required
def moviecol(page=None):
    if page == None:
        page = 1
    page_data = Moviecol.query.join(Movie).join(User).filter(
        Movie.id == Moviecol.movie_id,
        User.id == session['user_id']
    ).order_by(Moviecol.addtime.desc()).paginate(page=page, per_page=10)
    return render_template("home/moviecol.html", page_data=page_data)


# 添加电影收藏
@home.route('/moviecol/add/', methods=['GET'])
@user_login_required
def moviecol_add():
    mid = request.args.get('mid', '')
    uid = request.args.get('uid', '')
    moviecol = Moviecol.query.filter_by(
        movie_id=int(mid),
        user_id=int(uid)
    ).count()
    if moviecol == 1:
        # 已收藏
        data = dict(ok=0)
    if moviecol == 0:
        # 未收藏
        moviecol = Moviecol(
            movie_id=int(mid),
            user_id=int(uid)
        )
        db.session.add(moviecol)
        db.session.commit()
        data = dict(ok=1)
    import json
    return json.dumps(data)


# 首页
@home.route('/<int:page>/', methods=['GET'])
def index(page=None):
    tags = Tag.query.all()
    page_data = Movie.query

    tid = request.args.get('tid', 0)  # 标签
    if int(tid) != 0:
        page_data = page_data.filter_by(tag_id=int(tid))

    star = request.args.get('star', 0)  # 星级
    if int(star) != 0:
        page_data = page_data.filter_by(star=int(star))

    time = request.args.get("time", 0)  # 时间
    if int(time) != 0:
        if int(time) == 1:
            page_data = page_data.order_by(Movie.addtime.desc())
        else:
            page_data = page_data.order_by(Movie.addtime.asc())

    pm = request.args.get("pm", 0)  # 播放量
    if int(pm) != 0:
        if int(pm) == 1:
            page_data = page_data.order_by(Movie.playnum.desc())
        else:
            page_data = page_data.order_by(Movie.playnum.asc())

    cm = request.args.get("cm", 0)  # 评论量
    if int(cm) != 0:
        if int(cm) == 1:
            page_data = page_data.order_by(Movie.commentnum.desc())
        else:
            page_data = page_data.order_by(Movie.commentnum.asc())

    # 分页
    if page is None:
        page = 1
    page_data = page_data.paginate(page=page, per_page=10)

    p = dict(
        tid=tid,
        star=star,
        time=time,
        pm=pm,
        cm=cm
    )
    return render_template("home/index.html", tags=tags, p=p, page_data=page_data)


# 上映预告
@home.route('/animation/')
def animation():
    data = Preview.query.all()
    return render_template("home/animation.html", data=data)


# 电影搜索
@home.route('/search/<int:page>/')
def search(page=None):
    if page is None:
        page = 1
    key = request.args.get('key', '')  # 获取请求地址参数中的key值
    page_data = Movie.query.filter(
        Movie.title.ilike("%" + key + "%")
    ).order_by(Movie.addtime.desc()).paginate(page=page, per_page=10)  # 根据获取到的key值在数据库中进行模糊查询
    page_data.key = key
    movie_count = Movie.query.filter(Movie.title.ilike("%" + key + "%")).count()
    return render_template("home/search.html", key=key, page_data=page_data, movie_count=movie_count)


# 电影播放页
@home.route('/play/<int:id>/<int:page>/', methods=['GET', 'POST'])
def play(id=None, page=None):
    movie = Movie.query.join(Tag).filter(
        Tag.id == Movie.tag_id,
        Movie.id == int(id)
    ).first_or_404()
    # 评论数据分页处理
    if page == None:
        page = 1
    page_data = Comment.query.join(Movie).join(User).filter(
        Movie.id == movie.id,
        User.id == Comment.user_id
    ).order_by(Comment.addtime.desc()).paginate(page=page, per_page=5)
    # 播放量+1
    movie.playnum += 1
    form = CommentForm()
    # 保存评论内容信息到数据库
    if 'user' in session and form.validate_on_submit():
        data = form.data
        comment = Comment(
            content=data['content'],
            movie_id=movie.id,
            user_id=session['user_id']
        )
        db.session.add(comment)
        db.session.commit()
        # 评论量需要+1
        movie.commentnum += 1
        db.session.add(movie)
        db.session.commit()
        flash("评论成功", 'ok')
        return redirect(url_for('home.play', id=movie.id, page=1))
    db.session.add(movie)
    db.session.commit()
    return render_template("home/play.html", movie=movie, form=form, page_data=page_data)


# 弹幕播放器
@home.route('/video/<int:id>/<int:page>/', methods=['GET', 'POST'])
def video(id=None, page=None):
    movie = Movie.query.join(Tag).filter(
        Tag.id == Movie.tag_id,
        Movie.id == int(id)
    ).first_or_404()
    # 评论数据分页处理
    if page == None:
        page = 1
    page_data = Comment.query.join(Movie).join(User).filter(
        Movie.id == movie.id,
        User.id == Comment.user_id
    ).order_by(Comment.addtime.desc()).paginate(page=page, per_page=5)
    # 播放量+1
    movie.playnum += 1
    form = CommentForm()
    # 保存评论内容信息到数据库
    if 'user' in session and form.validate_on_submit():
        data = form.data
        comment = Comment(
            content=data['content'],
            movie_id=movie.id,
            user_id=session['user_id']
        )
        db.session.add(comment)
        db.session.commit()
        # 评论量需要+1
        movie.commentnum += 1
        db.session.add(movie)
        db.session.commit()
        flash("评论成功", 'ok')
        return redirect(url_for('home.video', id=movie.id, page=1))
    db.session.add(movie)
    db.session.commit()
    return render_template("home/video.html", movie=movie, form=form, page_data=page_data)


# 弹幕
@home.route("/dm/", methods=["GET", "POST"])
def dm():
    import json
    if request.method == "GET":
        # 获取弹幕消息队列
        id = request.args.get('id')
        key = "movie" + str(id)
        if rd.llen(key):
            msgs = rd.lrange(key, 0, 2999)
            res = {
                "code": 1,
                "danmaku": [json.loads(v).decode('utf-8') for v in msgs]
            }
        else:
            res = {
                "code": 1,
                "danmaku": []
            }
        resp = json.dumps(res)
    if request.method == "POST":
        # 添加弹幕
        data = json.loads(request.get_data())
        msg = {
            "author": data["author"],
            "color": data["color"],
            "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex,
            "text": data["text"],
            "time": data["time"],
            "type": data['type'],
            "ip": request.remote_addr,
            "player": [
                data["player"]
            ]
        }
        res = {
            "code": 1,
            "data": msg
        }
        resp = json.dumps(res)
        rd.lpush("movie{0}".format(str(data["player"])), json.dumps(msg))
    return Response(resp, mimetype='application/json')
