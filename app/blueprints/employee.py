# -*- coding: utf-8 -*-
"""
従業員マイページ
"""

from flask import Blueprint, render_template
from ..utils import require_roles, ROLES

bp = Blueprint('employee', __name__, url_prefix='/employee')


@bp.route('/mypage')
@require_roles(ROLES["EMPLOYEE"])
def mypage():
    """従業員マイページ"""
    return render_template('employee_mypage.html')
