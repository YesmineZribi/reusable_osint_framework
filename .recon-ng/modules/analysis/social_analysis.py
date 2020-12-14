# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.social_user import SocialUser
from recon.mixins.social_graph import SocialGraph
from recon.mixins.social_user_report import *
from recon.mixins.graph_report import *
# module specific imports
import os
from itertools import combinations
import subprocess
import sys
import time
from datetime import datetime
import json
import re
import multiprocessing as mp

class Module(BaseModule):

    meta = {
        'name': 'SNA_Analyser',
        'author': 'Yesmine Zribi (@YesmineZribi)',
        'version': '1.0',
        'description': 'Performs social network analysis',
        'dependencies': ['NetworkX', 'python-louvain'],
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
            ('relationship_analysis', True,False,'Set to get pairwise user relationship analysis'),
            ('common_analysis', True,False,'Set to get reports about relevant users in this network'),
            ('connection_analysis',True,False,'Set to True to analyse user connections'),
            ('reshare_analysis',True,False,'Set to True to analyse user\'s post sharing relationship'),
            ('mention_analysis',True,False,'Set to True to analyse users\' mentions relationship'),
            ('favorite_analysis',True,False,'Set to True to analyse user\'s post like relationship'),
            ('comment_analysis',True,False,'Set to True to analyse user\'s post comment relationship'),
            ('save_graphs',True,False,'Saves the graphs to json files to be used by visualization module'),
            ('fetch_account_info',False,False,'Set to True to run recon'),
            ('top',3,False,'Set to the number of prominent nodes to display, default 3, ie: will show top 3 hubs, top 3 brokers, etc.'),
            ('recon_level',1,False,'Set to the level of recon to perform'),
            ('keywords','',False,'Set to keywords to look for in user posts'),
            ('order_by','followers',False,'Order users by highest number of target followers/friends/mentions/reshares'),
        ),
    }


    def module_pre(self):
        # Ensure source_type is valid and usernames are valid
        if self.options['source_type'] not in ['id', 'screen_name']:
            self.error('Illegal source type pick either id or screen_name')

        # Check if user set source_type to legal string
        if self.options['source_type'] in 'id' and not(all(x.isnumeric() for x in self.options['usernames'].split(","))):
            self.error('Illegal values for social network ids')

        if self.options['keywords']:
            self.keywords = [keyword for keyword in self.options['keywords'].split(',')]

        # Split them and convert to ints if necessary or remove the @
        self.handles = [username.strip() for username in self.options['usernames'].split(",")] if not isinstance(self.options['usernames'],int) else [str(self.options['usernames'])]
        self.handles = [int(x) for x in self.handles] if all(x.isnumeric() for x in self.handles) else self.handles
        self.handles = [handle[1:] if handle.startswith('@') else handle for handle in self.handles] if all(isinstance(x,str) for x in self.handles) else self.handles # Clean up the handles

        # Create user objects from usernames
        self.users = []
        for username in self.handles:
            user = SocialUser(**{self.options['source_type']: username})
            self.users.append(user)

        # fetch data about all the users
        if self.options['fetch_account_info']:
            # Keep track of list of users on who recon was done
            # This is so we don't do recon on the same user twice
            self.debug("Performing recon...")
            self.fetch_bulk_account_info(self.options['usernames'])
            self.debug("Recon complete.")

        # Get all pair combinations from the list of users given - needed later
        self.all_pairs = list(combinations(self.handles,2))

        # Append graphs enabled by user
        self.graph_names = []
        if self.options['connection_analysis']:
            self.graph_names.append('connections')
        if self.options['reshare_analysis']:
            self.graph_names.append('reshares')
        if self.options['mention_analysis']:
            self.graph_names.append('mentions')
        if self.options['favorite_analysis']:
            self.graph_names.append('favorites')
        if self.options['comment_analysis']:
            self.graph_names.append('comments')

        self.graph_reports = {}
        # Initialize graph reports for each graph
        for graph_name in self.graph_names:
            self.graph_reports[graph_name] = GraphReport(graph_name)

        #Create graphs
        self.output("Creating graphs...")
        # TODO: add friends/followers if recursive
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

        # Build needed db tables
        self.debug("Building graphs schema...")
        self.create_graph_schema()
        self.debug("Building targets schema...")
        self.create_targets_schema()
        self.debug("Building reports schema...")

        # Keep track of all common friends/followers/mentions etc.
        # used to identify users followed/following the most by the target users
        self.commons = set()

        # Keep track of pair reports
        self.pair_reports = []

    def module_run(self):
        self.output("Initiating analysis...")
        dirname = f"{self.options['recon_module']}_network_reports"
        filename = f"network_report"
        ############# GRAPH  ANALYSIS #################################
        for graph_name, graph_report in self.graph_reports.items():
            # Get important metrics for graphs and store results in graph_report
            self.graph_structure_analysis(graph_name,graph_report)
            self.graph_node_analysis(graph_name,graph_report)
            self.graph_community_analysis(graph_name, graph_report)
            self.generate_report(graph_report,dirname,filename)

        ############ TARGET USERS ANALYSIS #############################

        if self.options['user_analysis']:
            self.single_user_analysis()
        ############### RELATIONSHIP ANALYSIS #####################
        if self.options['relationship_analysis']:
            self.relationship_pair_analysis()

        if self.options['common_analysis']:
            self.network_relationship_analysis()

        if self.options['save_graphs']:
            self.output("Exporting graphs...")
            self.save_graphs()
            self.debug("Finished exporting graphs ")

        self.output("Analysis COMPLETE.")
        self.output(f"results stored in {self.session_path}")

    def get_usernames(self, users):
        usernames = ""
        for i, user in enumerate(users):
            # Call right method to get username (screen_name/id) based on user choice
            get_username = getattr(user,f"get_{self.options['source_type']}")
            # Get the username and add it to the list
            usernames += get_username()
            if i < len(users)-1: # Still did not reach last element
                usernames += ", "
        return usernames

    # TODO: Implement recursive fetching
    def fetch_bulk_account_recursive(self,users, stp_lvl=1, recur_lvl=0):
        usernames = self.get_usernames(users)
        # Do recon on the usernames
        self.fetch_bulk_account_info(usernames)

        # Increment recur_lvl
        recur_lvl += 1
        self.verbose(f" level {recur_lvl} of recon complete")
        # Add to list to avoid fetching user info more than once
        if recur_lvl < stp_lvl: # recon one more level
            for user in users:
                self.debug(f"Getting friends for {user}")
                followers = user.get_followers()
                friends = user.get_friends()
                self.verbose("Sleeping for 1 minutes....")
                time.sleep(1 * 60)
                self.fetch_bulk_account_recursive(followers,stp_lvl,recur_lvl)
                self.verbose("Sleeping for 1 minutes....")
                time.sleep(1 * 60)
                self.fetch_bulk_account_recursive(friends,stp_lvl,recur_lvl)

    def fetch_bulk_account_info(self,usernames):
        if not usernames:
            return
        # Create temp file to store commands
        tmp_file = './cmds.txt'
        workspace = os.path.basename(os.path.normpath(self.workspace))
        with open(tmp_file, 'w+') as file:
            file.write(f"workspaces load {workspace}\n")
            file.write(f"modules load {self.options['recon_module']}\n")
            file.write(f"options set analysis_recon TRUE\n")
            file.write(f"options set source_type {self.options['source_type']}\n")
            file.write(f"options set source {usernames}\n")
            file.write(f"options set optimize True\n")
            file.write(f"run\n")
            file.write(f"exit\n")

        # Open subprocess and run commands
        subprocess.call(f"./recon-ng -r {tmp_file}",shell=True)

        #Delete file
        os.remove(tmp_file)


############################### ANALYSIS METHODS ####################################
    def single_user_analysis(self):
        self.debug("Started user analysis....")
        # Name of dir under which to store reports
        dirname = f"{self.options['recon_module']}_single_reports"
        self.user_reports = {}
        for handle in self.handles:
            # Add user in target db
            self.add_target(handle)
            # Get User metrics
            # Stores {graph : {centrality:x,btwnness:y..}..}
            metrics = {}
            for graph_name in self.graph_names:
                metrics[graph_name] = self.graphs.get_all_measures(graph_name,handle)
            # Get node to display in report
            user_obj = self.graphs.get_node(handle)
            # Store in user report
            user_report = UserReport(user_obj, measures=metrics)
            self.user_reports[handle] = user_report  # Store measures for that user
            filename = f"{handle}_report"
            self.generate_report(user_report,dirname,filename)
        self.debug("User analysis complete.")
        self.debug("Generating user reports...")

    def relationship_pair_analysis(self):
        # directory under which to save relationship reports
        dirname = f"{self.options['recon_module']}_relationship_reports"
        # Iterate over each pair of users and analyse relationship
        for pair in self.all_pairs:
            self.debug(f"Analyzing pair: {pair}")
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
                self.connection_pair_analysis(username1, username2, rel_obj)
                self.debug("Connection analysis complete.")
            if self.options['reshare_analysis']:
                self.debug("Started reshare analysis...")
                rel_obj.enable_reshare_analysis()
                self.reshare_pair_analysis(username1, username2, rel_obj)
                self.debug("Reshare analysis complete.")
            if self.options['mention_analysis']:
                self.debug("Started mention analysis...")
                rel_obj.enable_mention_analysis()
                self.mention_pair_analysis(username1, username2, rel_obj)
                self.debug("mention analysis complete")

            if self.options['favorite_analysis']:
                self.debug("Started favorite analysis...")
                rel_obj.enable_favorite_analysis()
                self.favorite_pair_analysis(username1, username2, rel_obj)
                self.debug("favorite analysis complete.")
            if self.options['comment_analysis']:
                self.debug("Started comment analysis...")
                rel_obj.enable_comment_analysis()
                self.comment_pair_analysis(username1, username2, rel_obj)
                self.debug("Comment analysis complete.")

            self.output("Generating report...")
            filename = f'{rel_obj.user1.screen_name}_{rel_obj.user2.screen_name}_relationship_rep'
            # self.generate_rel_report(rel_obj)
            self.generate_report(rel_obj,dirname,filename)
            self.debug(f"Finished generating reports for pair {pair}.")
            # print summary
            self.pair_reports.append(rel_obj)
            rel_obj.print_summary()

    def network_relationship_analysis(self):
        user_reports = []
        for user in self.commons:
            user_report = self.get_user_report(user)
            user_reports.append(user_report)

        # Order based on user input
        if self.options['order_by'] == "followers":
            user_reports.sort(key=lambda x: x.target_followers_num(), reverse=True)

        elif self.options['order_by'] == "friends":
            user_reports.sort(key=lambda x: x.target_friends_num(), reverse=True)

        elif self.options['order_by'] == "mentions":
            user_reports.sort(key=lambda x: x.target_mentions_num(), reverse=True)

        elif self.options['order_by'] == "reshares":
            user_reports.sort(key=lambda x: x.target_reshares_num(), reverse=True)

        dirname = f"{self.options['recon_module']}_common_users_reports"
        filename = "relevant_network_users"
        self.generate_common_reports(user_reports,dirname,filename)
        return user_reports


    def graph_structure_analysis(self,graph_name, graph_report):
        # Get density of the graph
        graph_density = self.graphs.density(graph_name)
        graph_triadic_closure = self.graphs.triadic_closure(graph_name)

        # Add info to report
        graph_report.set_density(graph_density)
        graph_report.set_triadic_closure(graph_triadic_closure)

    def graph_node_analysis(self, graph_name, graph_report):
        self.debug(f"{graph_name} important nodes:")
        # Get hubs -> highest centrality
        graph_report.set_hubs(self.graphs.get_top_nodes(graph_name, "centrality", self.options['top']))
        self.debug(f"Hubs: {graph_report.hubs}")
        # Get brokers --> highest betweeneess
        graph_report.set_brokers(self.graphs.get_top_nodes(graph_name, "betweenness", self.options['top']))
        self.debug(f"Brokers: {graph_report.brokers}")
        # Get influencers --> highest eigenvector value
        graph_report.set_influencers(self.graphs.get_top_nodes(graph_name, "eigenvector", self.options['top']))
        self.debug(f"Influencers: {graph_report.influencers}")

    def graph_community_analysis(self, graph_name, graph_report):
        #self.graphs.graph_modularity("connections")
        num_of_communities = self.graphs.graph_best_partition(graph_name)
        for i in range(0,num_of_communities):
            community_metrics = self.graphs.get_community_metrics(graph_name,i,self.options['top'])
            graph_report.add_community_metrics(community_metrics)

############################### ENDOF ANALYSIS METHODS ##############################

################## RELATIONSHIP ANALYSIS HELPERS ####################################

    def get_user_report(self,user):
        user.enable_fetch("twitter_user")
        # Get target users this user follows
        target_friends = self.get_target_friends(user)
        # Get target users that follow this user
        target_followers = self.get_target_followers(user)
        # Get target users that mentioned this user
        # mentions_by_targets = self.get_mentions_by_targets(user)
        # # Get target users mentioned by this user
        # target_mentions = self.get_target_mentions(user)
        # # Get target users that shared posts from this user
        # reshares_by_targets = self.get_reshares_by_targets(user)
        # # Get target users whose posts this user shared
        # target_reshares = self.get_target_reshares(user)
        # Get critical posts
        if self.options['keywords']:
            critical_posts = self.search_user_posts(user, self.keywords)
        else:
            critical_posts = []

        user_report = UserReport(user, target_friends=target_friends,
                                 target_followers=target_followers,
                                 # mentions_by_targets=mentions_by_targets,
                                 # target_mentions=target_mentions,
                                 # reshares_by_targets=reshares_by_targets,
                                 # target_reshares=target_reshares,
                                 critical_posts=critical_posts
                                 )


        return user_report


    def get_target_friends(self,user):
        """
        Target users this user is following
        """
        friends = []
        for target in self.users:
            if target.has_follower(user):
                friends.append(target)
        return friends

    def get_target_followers(self,user):
        """
        Target user that follow this user
        """
        followers = []
        for target in self.users:
            if target.has_friend(user):
                followers.append(target)
        return followers


    def get_mentions_by_targets(self,user):
        """
        Get target users that mentioned this user
        """
        # Get all target users that mentioned this user
        mentions_by_targets = {}
        for target in self.users:
            mentioned = target.mentioned(user)
            if mentioned:
                mentions_by_targets[target] = mentioned

        return mentions_by_targets

    def get_target_mentions(self,user):
        """
        Get target users this user mentioned
        """
        target_mentions = {}
        for target in self.users:
            mentioned = user.mentioned(target)
            if mentioned:
                target_mentions[target] = mentioned
        return target_mentions

    def get_reshares_by_targets(self,user):
        """
        Get target users that shared posts from this user
        """
        # Get all target users that mentioned this user
        reshares_by_targets = {}
        for target in self.users:
            reshared = target.reshared(user)
            if reshared:
                reshares_by_targets[target] = reshared
        return reshares_by_targets

    def get_target_reshares(self,user):
        """
        Get target users from which this user reshared posts
        """
        target_reshares = {}
        for target in self.users:
            reshared = user.reshared(target)
            if reshared:
                target_reshares[target] = reshared
        return target_reshares

    def search_user_posts(self,user,keywords):
        """
        Search all user posts that contains any of the strings in keywords
        """
        def find_whole_word(w):
            return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search

        found_posts = []
        user_posts = user.get_timeline()
        for post in user_posts:
            if any(find_whole_word(keyword)(post.text) for keyword in keywords):
                found_posts.append(post.text)

        return found_posts




################## ENDOF RELATIONSHIP PAIR ANALYSIS HELPERS ##########################

################## RELATIONSHIP PAIR ANALYSIS HELPERS ################################
    def connection_pair_analysis(self, username1, username2, rel_obj):
        self.friendship_pair_analysis(username1, username2, rel_obj)
        self.commons_conn_pair_analysis(username1, username2, rel_obj)
        self.path_pair_analysis("connections", username1, username2, rel_obj)

    def friendship_pair_analysis(self, username1, username2, rel_obj):
        u1_follows_u2 = self.graphs.follows(username1, username2)
        u2_follows_u1 = self.graphs.follows(username2, username1)
        if u1_follows_u2 and u2_follows_u1:
            self.alert(f"bidirection for {username1} and {username2}")
            rel_obj.set_connection(Connection.BIDIRECTIONAL)
        elif u1_follows_u2:
            rel_obj.set_connection(Connection.UNIDIRECTIONAL,source=username1,target=username2)
        elif u2_follows_u1:
            rel_obj.set_connection(Connection.UNIDIRECTIONAL,source=username2,target=username1)
        else:
            rel_obj.set_connection(Connection.NONE)

    def commons_conn_pair_analysis(self, username1, username2, rel_obj):
        common_friends = self.graphs.common_friends(username1,username2)
        common_followers = self.graphs.common_followers(username1,username2)
        if common_friends:

            for friend in common_friends:
                self.commons.add(friend)

            rel_obj.set_common_connections(CommonConnections.COMMON_FRIENDS,common_friends)

        if common_followers:

            for follower in common_followers:
                self.commons.add(follower)

            rel_obj.set_common_connections(CommonConnections.COMMON_FOLLOWERS,common_followers)

# TODO: fix conn_path2 not being used
    def path_pair_analysis(self, graph_name, username1, username2, rel_obj):
        conn_path = self.graphs.shortest_paths(graph_name,username1,username2)
        conn_path_2 = self.graphs.shortest_paths(graph_name,username2,username1)
        rel_obj.set_connection_path(conn_path)

    def reshare_pair_analysis(self, username1, username2, rel_obj):
        # Get posts that u1 shares from u2 and vice versa
        self.direct_pair_reshare(username1, username2, rel_obj)
        # Get posts u1 and u2 shared from the same source
        self.common_source_pair_reshare(username1, username2, rel_obj)

    def direct_pair_reshare(self, username1, username2, rel_obj):
        u1_reshared_u2 = self.graphs.reshared(username1,username2)
        u2_reshared_u1 = self.graphs.reshared(username2,username1)
        if u1_reshared_u2:
            #Extract the list of reshared posts
            posts = u1_reshared_u2[1]
            rel_obj.set_reshare(username1,username2,posts)
        if u2_reshared_u1:
            posts = u2_reshared_u1[1]
            rel_obj.set_reshare(username2,username1,posts)

    def common_source_pair_reshare(self, username1, username2, rel_obj):
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
                # For each user, get the posts user shared from src
                reshares = self.graphs.get_all_reshares_from_src(user,src)

                #self.commons.add(src)
                # Save this to report class
                rel_obj.set_common_src_reshares(user,src,reshares)

    def mention_pair_analysis(self, username1, username2, rel_obj):
        # Get posts in which u1 mentions u2 and vice versa
        self.direct_pair_mention(username1, username2, rel_obj)
        # Get posts where u1 and u2 mention the same user
        self.common_source_pair_mention(username1, username2, rel_obj)

    def direct_pair_mention(self, username1, username2, rel_obj):
        u1_mentioned_u2 = self.graphs.mentioned(username1,username2)
        u2_mentioned_u1 = self.graphs.mentioned(username2,username1)
        if u1_mentioned_u2:
            #Extract the list of reshared posts
            posts = u1_mentioned_u2
            rel_obj.set_mention(username1,username2,posts)
        if u2_mentioned_u1:
            posts = u2_mentioned_u1
            rel_obj.set_mention(username2,username1,posts)

    def common_source_pair_mention(self, username1, username2, rel_obj):
        common_src = self.graphs.common_mentions_nodes(username1,username2)
        # Get the nodes for each user
        users = [self.graphs.get_node(username1),self.graphs.get_node(username2)]

        for user in users:
            for src in common_src:
                #For each user, get the posts user shared from src
                mentions = self.graphs.get_all_mentions_of_src(user,src)
                #self.commons.add(src)
                rel_obj.set_common_src_mentions(user,src,mentions)

    def favorite_pair_analysis(self, username1, username2, rel_obj):
        self.direct_pair_favorite(username1, username2, rel_obj)
        self.common_source_pair_favorite(username1, username2, rel_obj)

    def direct_pair_favorite(self, username1, username2, rel_obj):
        u1_liked_u2 = self.graphs.favored(username1,username2)
        u2_liked_u1 = self.graphs.favored(username2,username1)

        if u1_liked_u2:
            posts = u1_liked_u2
            rel_obj.set_favorite(username1,username2,posts)
        if u2_liked_u1:
            posts = u2_liked_u1
            rel_obj.set_favorite(username2,username1,posts)

    def common_source_pair_favorite(self, username1, username2, rel_obj):
        common_src = self.graphs.common_favorties_nodes(username1,username2)
        # Get the nodes for each user
        users = [self.graphs.get_node(username1),self.graphs.get_node(username2)]
        for user in users:
            for src in common_src:
                #For each user, get the posts user shared from src
                favorites = self.graphs.get_all_favorites_from_src(user,src)
                rel_obj.set_common_src_favorites(user,src,favorites)

    def comment_pair_analysis(self, username1, username2, rel_obj):
        self.direct_pair_comment(username1, username2, rel_obj)
        self.common_source_pair_comment(username1, username2, rel_obj)

    def direct_pair_comment(self, username1, username2, rel_obj):
        u1_comment_u2 = self.graphs.commented(username1,username2)
        u2_comment_u1 = self.graphs.commented(username2,username1)
        if u1_comment_u2:
            comments = u1_comment_u2
            rel_obj.set_comment(username1,username2,comments)
        if u2_comment_u1:
            comments = u2_comment_u1
            rel_obj.set_comment(username2,username1,comments)

    def common_source_pair_comment(self, username1, username2, rel_obj):
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

################## ENDOF RELATIONSHIP ANALYSIS HELPERS ###############################
################################### REPORT METHOD ###################################
    def generate_report(self,report_obj,dirname,filename):
        """
        Saves the report in a file
        Args:
            report_obj -> Report: report object to save
            dirname -> str: name of directory in which to save report
            filename -> str: name of file under which to save report obj
        Returns:
            None
        """
        reports_path = os.path.join(self.session_path, dirname)
        if not os.path.exists(reports_path):
            os.makedirs(reports_path,mode=0o777)
        report_file = os.path.join(reports_path,f'{filename}.txt')
        with open(report_file, 'a') as file:
            file.write(str(report_obj))

    def generate_common_reports(self,user_reports,dirname,filename):
        reports_path = os.path.join(self.session_path, dirname)
        if not os.path.exists(reports_path):
            os.makedirs(reports_path,mode=0o777)
        report_file = os.path.join(reports_path,f'{filename}.txt')
        with open(report_file, 'a') as file:
            file.write(f"Relevant users ordered by {self.options['order_by']}\n\n")
            for user_report in user_reports:
                file.write(str(user_report))


################################### ENDOF REPORT METHODS ##############################

    def save_graphs(self):

        graphs_dir = os.path.join(self.session_path,f"{self.options['recon_module']}_graphs")
        if not os.path.exists(graphs_dir):
            os.makedirs(graphs_dir,mode=0o777)
        # For each graph get the date
        for graph_name in self.graph_names:
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
            # Add graph to db
            self.add_graph(graph_name,graph_json)

######### DATABASE HELPER METHODS ###############
    def create_graph_schema(self):
        self.query("""
        CREATE TABLE IF NOT EXISTS graphs(
        graph_name TEXT,
        graph_path TEXT,
        PRIMARY KEY(graph_name) )
        """)

    def create_targets_schema(self):
        self.query("""
        CREATE TABLE IF NOT EXISTS targets(
        username TEXT,
        PRIMARY KEY (username)
        ) 
        """)
        # Delete any prior data
        self.query(f"DELETE FROM targets")

    def add_graph(self, graph_name, graph_path):
        self.query(f"INSERT OR REPLACE INTO graphs(graph_name,graph_path) VALUES('{graph_name}','{graph_path}')")

    def add_target(self, username):
        #Empty from any previous data
        self.query(f"INSERT OR REPLACE INTO targets(username) VALUES ('{username}')")
