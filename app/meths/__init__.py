from flask import Blueprint
meths = Blueprint("meths",__name__)
import app.meths.view_api
import app.meths.annotation_api
import app.meths.gene_api
import app.meths.heatmap_api
import app.meths.track_api
import app.meths.jobs_api
import app.meths.thumbnail_api
import app.meths.project_api
import app.meths.user_api