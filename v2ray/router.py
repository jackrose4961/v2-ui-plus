import json

from flask import Blueprint, render_template, jsonify, request
from flask_babel import gettext
from sqlalchemy import and_

from base.models import Msg, User
from init import common_context, db
from util import config, server_info, v2_util, session_util
from util.v2_jobs import v2_config_change
from v2ray.models import Inbound


v2ray_bp = Blueprint('v2ray', __name__, url_prefix='/v2ray')

__check_interval = config.get_v2_config_check_interval()


@v2ray_bp.before_request
def before():
    common_context['is_admin'] = session_util.is_admin()


@v2ray_bp.route('/', methods=['GET'])
def index():
    # from init import common_context
    status = json.dumps(server_info.get_status(), ensure_ascii=False)
    return render_template('v2ray/index.html', **common_context, status=status)


@v2ray_bp.route('/accounts/', methods=['GET'])
def accounts():
    # from init import common_context
    users = '[' + ','.join([json.dumps(user.to_json(), ensure_ascii=False) for user in User.query.all()]) + ']'
    inbounds = '[' + ','.join([json.dumps(inbound.to_json(), ensure_ascii=False) for inbound in Inbound.query.all()]) + ']'
    return render_template('v2ray/accounts.html', **common_context, users=users, inbounds=inbounds)


@v2ray_bp.route('/clients/', methods=['GET'])
def clients():
    # from init import common_context
    return render_template('v2ray/clients.html', **common_context)


@v2ray_bp.route('/setting/', methods=['GET'])
def setting():
    # from init import common_context
    settings = config.all_settings()
    settings = '[' + ','.join([json.dumps(s.to_json(), ensure_ascii=False) for s in settings]) + ']'
    return render_template('v2ray/setting.html', **common_context, settings=settings,
                           v2ray_version=v2_util.get_v2ray_version())


@v2ray_bp.route('/inbounds', methods=['GET'])
def inbounds():
    return jsonify([inbound.to_json() for inbound in Inbound.query.all()])


@v2ray_bp.route('inbound/add', methods=['POST'])
@v2_config_change
def add_inbound():
    # user_id = int(request.form['user_id'])
    user_id = 1
    port = int(request.form['port'])
    if Inbound.query.filter_by(port=port).count() > 0:
        return jsonify(Msg(False, gettext('port exists')))
    listen = request.form['listen']
    protocol = request.form['protocol']
    settings = request.form['settings']
    stream_settings = request.form['stream_settings']
    sniffing = request.form['sniffing']
    remark = request.form['remark']
    enable = request.form['enable'] == 'true'
    inbound = Inbound(user_id, port, listen, protocol, settings, stream_settings, sniffing, remark, enable)
    db.session.add(inbound)
    db.session.commit()
    return jsonify(
        Msg(True,
            gettext(u'Successfully added, will take effect within %(seconds)d seconds', seconds=__check_interval)
        )
    )


@v2ray_bp.route('inbound/update/<int:in_id>', methods=['POST'])
@v2_config_change
def update_inbound(in_id):
    update = {}
    port = request.form.get('port')
    add_if_not_none(update, 'port', port)
    if port:
        if Inbound.query.filter(and_(Inbound.id != in_id, Inbound.port == port)).count() > 0:
            return jsonify(Msg(False, gettext('port exists')))
        add_if_not_none(update, 'tag', 'inbound-' + port)
    add_if_not_none(update, 'listen', request.form.get('listen'))
    add_if_not_none(update, 'protocol', request.form.get('protocol'))
    add_if_not_none(update, 'settings', request.form.get('settings'))
    add_if_not_none(update, 'stream_settings', request.form.get('stream_settings'))
    add_if_not_none(update, 'sniffing', request.form.get('sniffing'))
    add_if_not_none(update, 'remark', request.form.get('remark'))
    add_if_not_none(update, 'enable', request.form.get('enable') == 'true')
    Inbound.query.filter_by(id=in_id).update(update)
    db.session.commit()
    return jsonify(
        Msg(True,
            gettext(u'Successfully updated, will take effect within %(seconds)d seconds', seconds=__check_interval)
            )
    )


@v2ray_bp.route('inbound/del/<int:in_id>', methods=['POST'])
@v2_config_change
def del_inbound(in_id):
    Inbound.query.filter_by(id=in_id).delete()
    db.session.commit()
    return jsonify(
        Msg(True,
            gettext(u'Successfully deleted, will take effect within %(seconds)d seconds', seconds=__check_interval)
            )
    )


@v2ray_bp.route('reset_traffic/<int:in_id>', methods=['POST'])
def reset_traffic(in_id):
    Inbound.query.filter_by(id=in_id).update({'up': 0, 'down': 0})
    db.session.commit()
    return jsonify(Msg(True, gettext('Reset traffic successfully')))


@v2ray_bp.route('reset_all_traffic', methods=['POST'])
def reset_all_traffic():
    Inbound.query.update({'up': 0, 'down': 0})
    db.session.commit()
    return jsonify(Msg(True, gettext('Reset add traffic successfully')))


def add_if_not_none(d, key, value):
    if value is not None:
        d[key] = value
