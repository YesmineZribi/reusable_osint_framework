# module required for framework integration
from recon.core.module import BaseModule
# module specific imports
import os
from flask import Flask, flash, redirect, render_template, request, session, abort, send_from_directory, send_file, jsonify
import json
from multiprocessing import Process


class Module(BaseModule):

    meta = {
        'name': 'Graph_Visualizer',
        'author': 'Yesmine Zribi (@YesmineZribi)',
        'version': '1.0',
        'description': 'Resolves IP addresses to hosts and updates the database with the results.',
        'dependencies': ['Flask'],
        'files': [],
        'required_keys': [],
        'comments': (
            'Requires D3 installed on your machine',

        ),
        'options': (
            ('nameserver', '8.8.8.8', 'yes', 'ip address of a valid nameserver'),
        ),
    }

    def module_pre(self):
        pass

    def module_run(self):
        # Query database to get paths
        # Put paths in list
        # Pass graphs to render_template(index.html, graphs=graphs)

        conn_graph = "/home/osint/osint_framework/reusable_osint_framework/.recon-ng/modules/result_delivery/connections.json"
        res_graph = "/home/osint/osint_framework/reusable_osint_framework/.recon-ng/modules/result_delivery/reshares.json"
        graphs = ['connections','reshares']
        application = Flask(__name__)

        @application.route("/main", methods=["GET", "POST"])
        @application.route("/", methods=["GET", "POST"])
        def homepage():
            return render_template("index.html",graphs=graphs)

        @application.route("/go-conn", methods=["GET", "POST"])
        def go_conn():
            return render_template("connections.html")

        @application.route("/go-res", methods=["GET", "POST"])
        def go_res():
            return render_template("reshares.html")

        @application.route("/get-conn", methods=["GET", "POST"])
        def return_conn():
            with open(conn_graph,"r") as file:
                data = json.load(file)

            return jsonify(data)

        @application.route("/get-res", methods=["GET", "POST"])
        def return_res():
            with open(res_graph,"r") as file:
                data = json.load(file)

            return jsonify(data)


        # Start new subprocess in which to run the application
        p = Process(target=application.run)
        p.start()
        p.join()



"""
Plan: 
-Get analysis module to add paths to db tables 
-Create Flask application in wrapper 
-in module_run: 
    -query db for all paths + based on user settings 
    -For each graph create link that takes you to eqv html page 
-homepage():
    -Pass links to html 
index.html
    -Render links passed by homepage()
Move D3 code to 4 htmls 
-Call application.run inside module_run 
"""



