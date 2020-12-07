from app import app
from flask import Blueprint,redirect,url_for,render_template
from flask_user import current_user
mev_bp = Blueprint("mev",__name__)

@mev_bp.route("/home")
def comabat_home():
    return render_template("combat_home.html")


def before_request():
    if not current_user.is_authenticated or not current_user.has_permission("view_module","multi_experiment_view"):
        return redirect(url_for('main.home_page') )
    
mev_bp.before_request(before_request)
app.register_blueprint(mev_bp,url_prefix="/combat")