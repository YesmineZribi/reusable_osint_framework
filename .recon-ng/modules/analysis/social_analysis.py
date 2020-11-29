# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.social_user import SocialUser
from recon.mixins.social_graph import SocialGraph
from recon.mixins.social_report import *
# module specific imports
import os
from itertools import combinations
import subprocess
import sys
import time
from datetime import datetime
import json

class Module(BaseModule):

    meta = {
        'name': 'SNA_Analyser',
        'author': 'Yesmine Zribi (@YesmineZribi)',
        'version': '1.0',
        'description': 'Performs social network analysis',
        'dependencies': ['NetworkX'],
        'files': [],
        'required_keys': [],
        'comments': (
            'Some social media platform consider a reshared post a mention of the original post author',
            'such as Twitter which appends an RT @mention to each retweet making a retweet also a mention',
        ),
        'options': (
            ('usernames', '', True, 'Set to list of users to analyse relationship between'),
            ('source_type', 'id', True,'Set the type of the source: user_id or screen_name or id'),
            ('recon_module','twitter_user',True,'Set to the name of the recon module to use (must already be installed)'),
            ('generate_report',True,True,'Set to True to generate reports'),
            ('user_analysis', True,False,'Set to True to get user metrics'),
            ('connection_analysis',True,False,'Set to True to analyse user connections'),
            ('reshare_analysis',True,False,'Set to True to analyse user\'s post sharing relationship'),
            ('mention_analysis',True,False,'Set to True to analyse users\' mentions relationship'),
            ('favorite_analysis',True,False,'Set to True to analyse user\'s post like relationship'),
            ('comment_analysis',True,False,'Set to True to analyse user\'s post comment relationship'),
            ('save_graphs',True,False,'Saves the graphs to json files to be used by visualization module'),
            ('fetch_account_info',False,False,'Set to True to run recon'),
        ),
    }


    def module_pre(self):
        # Ensure source_type is valid and usernames are valid
        if self.options['source_type'] not in ['id', 'screen_name']:
            self.error('Illegal source type pick either id or screen_name')

        # Check if user set source_type to legal string
        if self.options['source_type'] in 'id' and not(all(x.isnumeric() for x in self.options['usernames'].split(","))):
            self.error('Illegal values for social network ids')

        # Split them and convert to ints if necessary or remove the @
        self.handles = [username.strip() for username in self.options['usernames'].split(",")] if not isinstance(self.options['usernames'],int) else [str(self.options['usernames'])]
        self.handles = [int(x) for x in self.handles] if all(x.isnumeric() for x in self.handles) else self.handles
        self.handles = [handle[1:] if handle.startswith('@') else handle for handle in self.handles] if all(isinstance(x,str) for x in self.handles) else self.handles # Clean up the handles

        # fetch data about all the users
        if self.options['fetch_account_info']:
            self.debug("Performing recon...")
            self.fetch_bulk_account_info()
            self.debug("Recon complete.")

        # Get all pair combinations from the list of users given - needed later
        self.all_pairs = list(combinations(self.handles,2))

        #Create graphs
        self.output("Creating graphs...")
        self.graphs = SocialGraph(self.options['source_type'],self.handles)

        # Build result directory
        self.debug("Building required directories...")
        self.root_path = os.path.dirname(os.path.abspath(sys.path[0])) #Get the root directory
        self.analysis_path = os.path.join(self.root_path,self.meta['name']) #directory to store collected data
        now = datetime.now()
        dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
        self.session_path = os.path.join(self.analysis_path,f"session_{dt_string}")

        if not os.path.exists(self.analysis_path):
            os.makedirs(self.analysis_path, mode=0o777)
        if not os.path.exists(self.session_path):
            os.makedirs(self.session_path, mode=0o777)



    def module_run(self):
        # Create User report class for each user
        self.output("Initiating analysis...")
        if self.options['user_analysis']:
            self.debug("Started user analysis....")
            self.user_reports = {}
            for handle in self.handles:
                # Get User metrics
                metrics = self.graphs.get_all_measures(self.graphs.G_connections,handle)
                user_obj = self.graphs.get_node(handle)
                user_report = UserReport(user_obj,metrics)
                self.user_reports[handle] = user_report # Store measures for that user
            self.debug("User analysis complete.")
        #Iterate over each pair of users and analyse relationship
        for pair in self.all_pairs:
            username1 = pair[0]
            username2 = pair[1]
            user_obj1 = self.graphs.get_node(username1)
            user_obj2 = self.graphs.get_node(username2)
            #create relationship report object
            rel_obj = RelationshipReport(user_obj1,user_obj2)
            if self.options['connection_analysis']:
                self.debug("Started connection analysis...")
                rel_obj.enable_connection_analysis()
                # Connections analysis
                self.connection_analysis(username1,username2,rel_obj)
                self.debug("Connection analysis complete.")
            if self.options['reshare_analysis']:
                self.debug("Started reshare analysis...")
                rel_obj.enable_reshare_analysis()
                self.reshare_analysis(username1,username2,rel_obj)
                self.debug("Reshare analysis complete.")
            if self.options['mention_analysis']:
                self.debug("Started mention analysis...")
                rel_obj.enable_mention_analysis()
                self.mention_analysis(username1,username2,rel_obj)
                self.debug("mention analysis complete")

            if self.options['favorite_analysis']:
                self.debug("Started favorite analysis...")
                rel_obj.enable_favorite_analysis()
                self.favorite_analysis(username1,username2,rel_obj)
                self.debug("favorite analysis complete.")
            if self.options['comment_analysis']:
                self.debug("Started comment analysis...")
                rel_obj.enable_comment_analysis()
                self.comment_analysis(username1,username2,rel_obj)
                self.debug("Comment analysis complete.")

            self.output("Generating report...")
            self.generate_report(rel_obj)
            self.debug("Finished generating reports.")


        if self.options['save_graphs']:
            self.output("Exporting graphs...")
            self.save_graphs()
            self.debug("Finished exporting graphs ")

        self.output("Analysis COMPLETE.")
        self.output(f"results stored in {self.session_path}")
        # print summary
        rel_obj.print_summary()


    def fetch_bulk_account_info(self):
        # Create temp file to store commands
        tmp_file = './cmds.txt'
        workspace = os.path.basename(os.path.normpath(self.workspace))
        with open(tmp_file, 'w+') as file:
            file.write(f"workspaces load {workspace}\n")
            file.write(f"modules load {self.options['recon_module']}\n")
            file.write(f"options set source_type {self.options['source_type']}\n")
            file.write(f"options set source {self.options['usernames']}\n")
            file.write(f"run\n")
            file.write(f"exit\n")

        # Open subprocess and run commands
        subprocess.call(f"./recon-ng -r {tmp_file}",shell=True)

        #Delete file
        os.remove(tmp_file)



    #Analyze graph method
    def connection_analysis(self,username1,username2,rel_obj):
        self.friendship_analysis(username1,username2,rel_obj)
        self.commons_conn_analysis(username1, username2, rel_obj)
        self.path_analysis("connections", username1, username2, rel_obj)

    def friendship_analysis(self,username1,username2,rel_obj):
        u1_follows_u2 = self.graphs.follows(username1, username2)
        u2_follows_u1 = self.graphs.follows(username2, username1)
        if u1_follows_u2 and u2_follows_u1:
            rel_obj.set_connection(Connection.BIDIRECTIONAL)
        elif u1_follows_u2:
            rel_obj.set_connection(Connection.UNIDIRECTIONAL,source=username1,target=username2)
        elif u2_follows_u1:
            rel_obj.set_connection(Connection.UNIDIRECTIONAL,source=username2,target=username1)
        else:
            rel_obj.set_connection(Connection.NONE)

    def commons_conn_analysis(self,username1,username2,rel_obj):
        common_friends = self.graphs.common_friends(username1,username2)
        common_followers = self.graphs.common_followers(username1,username2)
        if common_friends:
            rel_obj.set_common_connections(CommonConnections.COMMON_FRIENDS,common_friends)
        if common_followers:
            rel_obj.set_common_connections(CommonConnections.COMMON_FOLLOWERS,common_followers)

    def path_analysis(self,graph_name,username1,username2, rel_obj):
        conn_path = self.graphs.shortest_paths(graph_name,username1,username2)
        conn_path_2 = self.graphs.shortest_paths(graph_name,username2,username1)
        rel_obj.set_connection_path(conn_path)

    def reshare_analysis(self,username1,username2,rel_obj):
        # Get posts that u1 shares from u2 and vice versa
        self.direct_reshare(username1,username2,rel_obj)
        # Get posts u1 and u2 shared from the same source
        self.common_source_reshare(username1,username2,rel_obj)

    def direct_reshare(self,username1,username2,rel_obj):
        u1_reshared_u2 = self.graphs.reshared(username1,username2)
        u2_reshared_u1 = self.graphs.reshared(username2,username1)
        if u1_reshared_u2:
            #Extract the list of reshared posts
            posts = u1_reshared_u2[1]
            rel_obj.set_reshare(username1,username2,posts)
        if u2_reshared_u1:
            posts = u2_reshared_u1[1]
            rel_obj.set_reshare(username2,username1,posts)

    def common_source_reshare(self,username1,username2,rel_obj):
        """
        Gets user reshared by both username1 and username2 along
        with all posts username1 reshared from this user and all
        posts username2 reshared from this user
        """
        # Users both username1 and username2 reshared from
        common_src = self.graphs.common_reshare_nodes(username1,username2)
        # Get the nodes for each user
        users = [self.graphs.get_node(username1),self.graphs.get_node(username2)]

        for user in users:
            for src in common_src:
                #For each user, get the posts user shared from src
                reshares = self.graphs.get_all_reshares_from_src(user,src)
                #Save this to report class
                rel_obj.set_common_src_reshares(user,src,reshares)


    def mention_analysis(self,username1,username2,rel_obj):
        # Get posts in which u1 mentions u2 and vice versa
        self.direct_mention(username1,username2,rel_obj)
        # Get posts where u1 and u2 mention the same user
        self.common_source_mention(username1,username2,rel_obj)

    def direct_mention(self,username1,username2,rel_obj):
        u1_mentioned_u2 = self.graphs.mentioned(username1,username2)
        u2_mentioned_u1 = self.graphs.mentioned(username2,username1)
        if u1_mentioned_u2:
            #Extract the list of reshared posts
            posts = u1_mentioned_u2
            rel_obj.set_mention(username1,username2,posts)
        if u2_mentioned_u1:
            posts = u2_mentioned_u1
            rel_obj.set_mention(username2,username1,posts)

    def common_source_mention(self,username1,username2,rel_obj):
        common_src = self.graphs.common_mentions_nodes(username1,username2)
        # Get the nodes for each user
        users = [self.graphs.get_node(username1),self.graphs.get_node(username2)]

        for user in users:
            for src in common_src:
                #For each user, get the posts user shared from src
                mentions = self.graphs.get_all_mentions_of_src(user,src)
                rel_obj.set_common_src_mentions(user,src,mentions)

    def favorite_analysis(self,username1,username2,rel_obj):
        self.direct_favorite(username1,username2,rel_obj)
        self.common_source_favorite(username1,username2,rel_obj)

    def direct_favorite(self,username1,username2,rel_obj):
        u1_liked_u2 = self.graphs.favored(username1,username2)
        u2_liked_u1 = self.graphs.favored(username2,username1)

        if u1_liked_u2:
            posts = u1_liked_u2
            rel_obj.set_favorite(username1,username2,posts)
        if u2_liked_u1:
            posts = u2_liked_u1
            rel_obj.set_favorite(username2,username1,posts)

    def common_source_favorite(self,username1,username2,rel_obj):
        common_src = self.graphs.common_favorties_nodes(username1,username2)
        # Get the nodes for each user
        users = [self.graphs.get_node(username1),self.graphs.get_node(username2)]
        for user in users:
            for src in common_src:
                #For each user, get the posts user shared from src
                favorites = self.graphs.get_all_favorites_from_src(user,src)
                rel_obj.set_common_src_favorites(user,src,favorites)


    def comment_analysis(self,username1,username2,rel_obj):
        self.direct_comment(username1,username2,rel_obj)
        self.common_source_comment(username1,username2,rel_obj)

    def direct_comment(self,username1,username2,rel_obj):
        u1_comment_u2 = self.graphs.commented(username1,username2)
        u2_comment_u1 = self.graphs.commented(username2,username1)
        if u1_comment_u2:
            comments = u1_comment_u2
            rel_obj.set_comment(username1,username2,comments)
        if u2_comment_u1:
            comments = u2_comment_u1
            rel_obj.set_comment(username2,username1,comments)

    def common_source_comment(self,username1,username2,rel_obj):
        self.debug("Started commmon source comment analysis..")
        common_src = self.graphs.common_comment_nodes(username1,username2)
        # Get the nodes for each user
        users = [self.graphs.get_node(username1),self.graphs.get_node(username2)]
        for user in users:
            for src in common_src:
                # For each user, get the comments user made on post by src
                comments = self.graphs.get_all_comments_from_src(user,src)
                rel_obj.set_common_src_comments(user,src,comments)

        self.debug("Common source comment analysis complete.")

    def generate_report(self,rel_obj):
        reports_path = os.path.join(self.session_path,f"{self.options['recon_module']}_reports")
        if not os.path.exists(reports_path):
            os.makedirs(reports_path,mode=0o777)

        report_file = os.path.join(reports_path,f'{rel_obj.user1.screen_name}_{rel_obj.user2.screen_name}_relationship_rep.txt')
        with open(report_file,'w') as file:
            file.write(rel_obj.summary_report_format())
            file.write(str(rel_obj))

        #TODO: save path of report in DB


    def save_graphs(self):

        graphs_dir = os.path.join(self.session_path,f"{self.options['recon_module']}_graphs")
        if not os.path.exists(graphs_dir):
            os.makedirs(graphs_dir,mode=0o777)
        # For each graph get the date
        for graph_name in ['connections','mentions','reshares','favorites','comments']:
            #Get the graph's json
            graph_data = self.graphs.export_graph(graph_name)
            if not graph_data:
                continue
            #Get the date to append to file name
            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            graph_json = os.path.join(graphs_dir,f'{graph_name}_{dt_string}.json')
            #Write to json
            with open(graph_json, 'w') as file:
                json.dump({'links':graph_data[1],'nodes':graph_data[0]}, file, indent=4)
            self.debug(f"{graph_name} graph saved in {graph_json}")

            #TODO: save path of graphs in db