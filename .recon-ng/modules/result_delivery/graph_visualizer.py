# module required for framework integration
from recon.core.module import BaseModule
# module specific imports
import os
from flask import Flask, flash, redirect, render_template, request, session, abort, send_from_directory, send_file, jsonify
import json
from multiprocessing import Process
from threading import Timer
import webbrowser


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
            ('port', '5000', False, 'port on which to run flask server'),
        ),
    }

    def module_pre(self):
        pass

    def get_graphs(self):
        # Fetch all graphs from db
        response_list = self.query("""
        SELECT graph_name, graph_path from graphs
        """)
        # Store {graph_name:graph_path}
        graph_dict = {}
        for graph_name, graph_path in response_list:
            graph_dict[graph_name] = graph_path

        return graph_dict

    def get_targets(self):
        # Fetch all targets from db
        response_list = self.query("""
        SELECT username from targets
        """)
        target_users = []
        for tup in response_list:
            # Extract username
            username = tup[0]
            target_users.append(username)
        return target_users


    def module_run(self):
        # Query database to get paths
        graph_dict = self.get_graphs()
        # Query db to get target users to display their names in HTML
        targets = self.get_targets()
        # Populate list to pass to index.html
        graphs = []
        for graph_name, graph_path in graph_dict.items():
            graphs.append(graph_name)

        application = Flask(__name__)

        @application.route("/main", methods=["GET", "POST"])
        @application.route("/", methods=["GET", "POST"])
        def homepage():
            return render_template("index.html",graphs=graphs,targets=targets)

        @application.route("/go-conn", methods=["GET", "POST"])
        def go_conn():
            return render_template("connections.html")

        @application.route("/go-res", methods=["GET", "POST"])
        def go_res():
            return render_template("reshares.html")

        @application.route("/go-men", methods=["GET", "POST"])
        def go_men():
            return render_template("mentions.html")

        @application.route("/go-fav", methods=["GET", "POST"])
        def go_fav():
            return render_template("favorites.html")

        @application.route("/go-com", methods=["GET", "POST"])
        def go_com():
            return render_template("comments.html")

        @application.route("/get-conn", methods=["GET", "POST"])
        def return_conn():
            with open(graph_dict['connections'],"r") as file:
                data = json.load(file)

            return jsonify(data)

        @application.route("/get-res", methods=["GET", "POST"])
        def return_res():
            with open(graph_dict['reshares'],"r") as file:
                data = json.load(file)

            return jsonify(data)

        @application.route("/get-men", methods=["GET", "POST"])
        def return_men():
            with open(graph_dict['mentions'],"r") as file:
                data = json.load(file)

            return jsonify(data)

        @application.route("/get-fav", methods=["GET", "POST"])
        def return_fav():
            with open(graph_dict['favorites'],"r") as file:
                data = json.load(file)

            return jsonify(data)

        @application.route("/get-com", methods=["GET", "POST"])
        def return_com():
            with open(graph_dict['comments'],"r") as file:
                data = json.load(file)

            return jsonify(data)

        def open_browser():
            webbrowser.open_new(f"http://127.0.0.1:{self.options['port']}/")


        # Start new subprocess in which to run the application
        # Pass keywrod args to application.run
        port = {"port": self.options['port']}
        p = Process(target=application.run, kwargs=port)
        # Wait for server start before opening browser
        Timer(1, open_browser).start()
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



