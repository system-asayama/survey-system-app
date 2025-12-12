#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
survey-system-app エントリーポイント
"""

import os
from app import create_app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
