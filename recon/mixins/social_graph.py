from recon.core import framework
from recon.mixins.social_user import SocialUser
from recon.mixins.social_post import *
from collections import defaultdict

import networkx as nx
import matplotlib.pyplot as plt

import json
import os

class SocialGraph(framework.Framework):

    def __init__(self,source_type,usernames):
        framework.Framework.__init__(self,'social_graph')
        self.source_type = source_type
        #Initialize empty graphs
        self.G_connections = nx.DiGraph()
        self.G_reshares = nx.MultiDiGraph()
        self.G_favorites = nx.MultiDiGraph()
        self.G_mentions = nx.MultiDiGraph()

        #For each user create its object, call its get_all (multithread eventually)?
        self.users = [] #SocialUser[]
        self.users_dict = {}
        # TODO: Move this to fecth_bulk_account_info
        for username in usernames:
            user = SocialUser(**{source_type: username})
            user.get_all()
            self.users.append(user)
            self.users_dict[username] = user

        #Create the graphs
        self.create_connections_graph()
        self.create_reshares_graph()
        self.create_favorites_graph()
        self.create_mentions_graph()

        #Extract all found users
        self.map_users()

        self.degree_centrality = {} # Used to store centrality degree of all nodes
        self.nodes = []

    def create_connections_graph(self):
        self.output("Generating connections graph for users...")
        for user in self.users:
            # Add followers
            for follower in user.get_followers():
                self.G_connections.add_edge(follower,user)
            # Add friends
            for friend in user.get_friends():
                self.G_connections.add_edge(user,friend)
        # self.visualize_graph(self.G_connections)


    def create_reshares_graph(self):
        self.output("Generating reshares graph for users...")
        for user in self.users:
            for reshare in user.get_reshares():
                self.G_reshares.add_edge(user,reshare.original_post.author,
                                         original_post=reshare.original_post,
                                         reshared_post=reshare.reshared_post)


    def create_favorites_graph(self):
        self.output("Generating favorites graph for users...")
        for user in self.users:
            for favorite in user.get_favorites():
                self.G_favorites.add_edge(user,favorite.author,favorite=favorite)


    def create_mentions_graph(self):
        self.output("Generating mentions graph for users...")
        for user in self.users:
            for mention in user.get_mentions():
                self.G_mentions.add_edge(user,mention.mentioned,post=mention.post)

# TODO: Use Miguel's library for visualization
    def export_graph(self,graph_name,path,file_name):
        """
        Save the graph to a json file
        """
        # pos = nx.spring_layout(graph)
        # nx.draw_networkx(graph, pos)
        # nx.draw_networkx_edge_labels(graph, pos)
        # plt.show()
        graph = self.get_graph(graph_name)
        # Populate nodes with metrics: centrality, closeness, between, eigen
        # will be used for display
        self.centrality(graph)
        self.closeness(graph)
        self.betweenness_centrality(graph)
        self.eigenvector_centrality(graph)

        # save to json path
        data = nx.readwrite.node_link_data(graph)
        graph_json = os.path.join(path,f'{file_name}.json')
        with open(graph_json,'w') as file:
            json.dump(data,file, indent=4)




# TODO: account for cases where a username is not part of the dict
# Will need its own recon
    def follows(self,username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        return nx.has_path(self.G_connections,user1,user2)

# TODO: test this
# TODO: get the text of the post to include in report in module
    def reshared(self,username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        reshared = nx.has_path(self.G_reshares,user1,user2)
        if not reshared:
            return False
        posts = []
        reshare_edges = self.G_reshares[user1][user2]
        for key,edge_attr in reshare_edges.items():
            posts.append((edge_attr['original_post'],edge_attr['reshared_post']))

        # original_post = self.G_reshares[user1][user2]['original_post']
        # reshared_post = self.G_reshares[user1][user2]['reshared_post']
        # return (reshared,original_post,reshared_post)
        return (reshared,posts)


    def favored(self,username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        favored = nx.has_path(self.G_favorites,user1,user2)
        if not favored:
            return False

        # Collect all posts liked by user1 that were authored by user2
        favored_posts = []
        favored_edges = self.G_favorites[user1][user2]
        for key, edge_attr in favored_edges.items():
            favored_posts.append(edge_attr['favorite'])

        return favored_posts

    def mentioned(self,username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        mentioned = nx.has_path(self.G_mentions,user1,user2)
        if not mentioned:
            return False

        #Collect all posts in which user1 mentions user2
        mentioned_posts = []
        mentioned_edges = self.G_mentions[user1][user2]
        for key,edge_attr in mentioned_edges.items():
            mentioned_posts.append(edge_attr['post'])
        return mentioned_posts

    def common_friends(self,username1,username2):
        return self.common_out_neighbours(self.G_connections,username1,username2)


    def common_followers(self,username1,username2):
        return self.common_in_neighbours(self.G_connections,username1,username2)


    def common_favorties_nodes(self,username1,username2):
        return self.common_out_neighbours(self.G_favorites,username1,username2)


    def common_mentions_nodes(self,username1,username2):
        return self.common_out_neighbours(self.G_mentions,username1,username2)


    def common_reshare_nodes(self,username1,username2):
        authors = self.common_out_neighbours(self.G_reshares,username1,username2)
        return authors

    def get_all_reshares_from_src(self,username,src):
        user = self.users_dict[username] if not isinstance(username,SocialUser) else username
        src = self.users_dict[src] if not isinstance(src,SocialUser) else src
        # Get all edges from user to src in reshares graph
        edges = self.get_edges_attr("reshares",user,src)
        reshares = []
        for edge,attrs in edges.items():
            reshares.append(Reshare(user,attrs['reshared_post'],attrs['original_post']))
        return reshares


    def get_all_mentions_of_src(self,username,src):
        """
        Get all posts in which username mentions src
        """
        user = self.users_dict[username] if not isinstance(username, SocialUser) else username
        src = self.users_dict[src] if not isinstance(src,SocialUser) else src
        # Get all edges from user to src
        edges = self.get_edges_attr("mentions",user,src)
        mentions = []
        for edge,attrs in edges.items():
            mentions.append(Mention(user,src,post=attrs['post']))
        return mentions

    def get_all_favorites_from_src(self,username,src):
        user = self.users_dict[username] if not isinstance(username, SocialUser) else username
        src = self.users_dict[src] if not isinstance(src,SocialUser) else src
        # Get all edges from user to src
        edges = self.get_edges_attr("favorites",user,src)
        favorites = []
        for edge,attrs in edges.items():
            favorites.append(Favorite(user,src,post=attrs['favorite']))
        return favorites


    def common_out_neighbours(self,graph,username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        common_out_neighbours = set(graph.successors(user1)).intersection(graph.successors(user2))
        return list(common_out_neighbours)

    def common_in_neighbours(self,graph,username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        common_in_neighbours = set(graph.predecessors(user1)).intersection(graph.predecessors(user2))
        return list(common_in_neighbours)

    def shortest_paths(self,graph_name,username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        graph = self.get_graph(graph_name)
        shortest_paths = nx.all_shortest_paths(graph,user1,user2)
        str_repr = ""
        for path in shortest_paths:
            str_repr += "{"
            for i in range(0,len(path)):
                str_repr += f"{path[i]} -> " if i < len(path)-1 else f"{path[i]}"
            str_repr += "}\n"
        return str_repr


    def get_graph(self,graph_name):
        graph = getattr(self,f'G_{graph_name}')
        return graph

    def map_users(self):
        """
        Used to map each user found in the graphs to its username
        """
        #Iterate over nodes of each graph to map users
        connections = list(self.G_connections.nodes)
        reshares = list(self.G_reshares.nodes)
        mentions = list(self.G_mentions.nodes)
        favorites = list(self.G_favorites.nodes)
        all_users = connections + reshares + mentions + favorites
        key = False
        for user in all_users:
            # Map id or screen name as key and user obj as value
            # the key is variable based on what user provided
            # if source_type == screen_name key will be user.screen_name
            # if source_type == id key will be user.id
            key = vars(user)[self.source_type]
            if key not in self.users_dict:
                self.users_dict[key] = user

    def get_node(self,username):
        return self.users_dict[username]

    def get_edges(self,graph_name, username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        graph = self.get_graph(graph_name)
        return graph[user1][user2]

    def get_edges_attr(self,graph_name,username1,username2):
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        graph = self.get_graph(graph_name)
        return graph.get_edge_data(user1,user2,default=0)


    def get_successors(self,graph,username):
        successors = graph.successors(self.users_dict[username])
        return list(successors)

    def get_predecessors(self,graph,username):
        predecessors =  graph.predecessors(self.users_dict[username])
        return list(predecessors)

    def get_all_measures(self,graph,username=None,g_clustering=False):
        metrics = {}
        metrics['centrality'] = self.centrality(graph,username)
        metrics['in_centrality'] = self.in_centrality(graph,username)
        metrics['out_centrality'] = self.out_centrality(graph,username)
        metrics['out_centrality'] = self.out_centrality(graph,username)
        metrics['local_clustering'] = self.local_clustering(graph,username)
        if g_clustering:
            metrics['global_clustering'] = self.global_clustering(graph)
        metrics['closeness'] = self.closeness(graph,username)
        metrics['betweenness_centrality'] = self.betweenness_centrality(graph,username)
        metrics['eigenvector_centrality'] = self.eigenvector_centrality(graph,username)
        # Not yet implemented with directed graphs
        # metrics['current_flow_closenness_centrality'] = self.current_flow_closenness_centrality(graph,username)
        # metrics['current_flow_betweenness_centrality'] = self.current_flow_betweenness_centrality(graph,username)
        return metrics

    def centrality(self,graph,username=None):
        """
        Degree centrality: assigns an importance based on the number of links held by each node.
        Tells us how many 'one hop' connections each node has to other nodes in the network
        Useful for finding connected individuals, popular individuals,individuals who are likely
        to hold most info. or individuals who can quickly connect with the wider network
        """
        # If username is defined return that user centrality else whole graph's
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        # If this function was never called, do calculation
        degree_centrality = nx.degree_centrality(graph)

        # If called on whole graph save measure as node attribute
        # to be used for visualization
        for ix,deg in degree_centrality.items():
            graph.nodes[ix]['centrality'] = deg
        return degree_centrality[user] if username else degree_centrality

    def in_centrality(self,graph,username=None):
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        # If this function was never called, do calculation
        degree_centrality = nx.in_degree_centrality(graph)
        return degree_centrality[user] if username else degree_centrality

    def out_centrality(self,graph,username=None):
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        # If this function was never called, do calculation
        degree_centrality = nx.out_degree_centrality(graph)
        return degree_centrality[user] if username else degree_centrality

    # TODO: Check if nodes = None is the default value for clustering
    def local_clustering(self,graph,username=None):
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        return nx.clustering(graph,nodes=user)

    def global_clustering(self,graph):
        return nx.clustering(graph)


    def closeness(self,graph,username=None,wf_improve=True):
        """
        Scores each node based on their 'closeness' to all other nodes
        in the network. Useful for finding individuals best placed to influence
        the entire network most quickly. Can be similar for a highly connected
        network at which point could be useful to look into Closeness in a single
        cluster
        """
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        graph_closeness = nx.closeness_centrality(graph,user, wf_improved=wf_improve)
        # If called on whole graph save measure as node attribute
        # to be used for visualization
        for ix,clos in graph_closeness.items():
            graph.nodes[ix]['closeness'] = clos
        return graph_closeness

    def betweenness_centrality(self,graph,username=None):
        """
        Measures the number of times a node lies on the shortest path between
        other nodes. This shows which ndoes are 'bridges' between nodes in
        a network. Useful for finding individuals who influence the flow around a
        system and for analyzing communication dynamics, should be used with case,
        a high betweeness count could indicate somoene holds authority over disparate
        clusters in a network, or just that they are on the periphery of both
        clusters
        """
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        graph_betweenness = nx.betweenness_centrality(graph)
        # If called on whole graph save measure as node attribute
        # to be used for visualization
        for ix,btwn in graph_betweenness.items():
            graph.nodes[ix]['btwn_centrality'] = btwn

        return graph_betweenness[user] if username else graph_betweenness

    def eigenvector_centrality(self,graph,username=None):
        """
        This measure can identify nodes with influence over the whole
        network not just those directly connected to it.
        """
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        graph_eigen = nx.eigenvector_centrality(graph)
        # If called on whole graph save measure as node attribute
        # to be used for visualization
        for ix, eig in graph_eigen.items():
            graph.nodes[ix]['eigen_centrality'] = eig

        return graph_eigen[user] if username else graph_eigen

    # # Warning: "Not implemented for directed graphs yet "
    # def current_flow_closenness_centrality(self,graph,username=None):
    #     user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
    #     graph_cf = nx.current_flow_closeness_centrality(graph)
    #     return graph_cf[user] if username else graph_cf
    #
    # # Warning: "Not implemented for directed graphs yet "
    # def current_flow_betweenness_centrality(self,graph,username=None):
    #     user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
    #     graph_cf = nx.current_flow_betweenness_centrality(graph)
    #     return graph_cf[user] if username else graph_cf









