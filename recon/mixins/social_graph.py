from recon.core import framework
from recon.mixins.social_user import SocialUser
from recon.mixins.social_post import *
from networkx.algorithms import community
import community as louvain_community

import networkx as nx
from operator import itemgetter
from typing import List, Union, Tuple

class SocialGraph(framework.Framework):

    def __init__(self,source_type: str,usernames: list):
        """
        A Social graph instance
        Args:
            source_type (str): the type of usernames (ids or screen names)
            usernames (list): list of usernames
        """
        framework.Framework.__init__(self,'social_graph')
        self.source_type = source_type
        # Initialize empty graphs
        self.G_connections = nx.DiGraph()
        # Can have multiple edges between two nodes => if user shares multiple posts, mentions another user multiple times etc.
        self.G_reshares = nx.MultiDiGraph()
        self.G_favorites = nx.MultiDiGraph()
        self.G_mentions = nx.MultiDiGraph()
        self.G_comments = nx.MultiDiGraph()

        # Diagraph equivalents for the multidigraphs
        # Note: some metrics cannot be performed on digraphs
        self.G_reshares_di = nx.DiGraph()
        self.G_favorites_di = nx.DiGraph()
        self.G_mentions_di = nx.DiGraph()
        self.G_comments_di = nx.DiGraph()

        # For each user create its object, call its get_all (multithread eventually)?
        self.users = [] # type: List['SocialUser']
        # Useful mapping for efficient fetching
        self.users_dict = {} # {screen_name: SocialUser}
        # keep track of the number of communities per graph
        self.graph_community_len = {}

        for username in usernames:
            user = SocialUser(**{source_type: username})
            user.get_all()
            self.users.append(user)
            self.users_dict[username] = user

        # Create the graphs

        self.create_connections_graph()
        self.create_reshares_graph()
        self.create_favorites_graph()
        self.create_mentions_graph()
        self.create_comments_graph()

        # Create digraph equivalents
        self.create_reshares_di_graph()
        self.create_favorties_di_graph()
        self.create_mentions_di_graph()
        self.create_comments_di_graph()

        # Extract all found users
        self.map_users()

        # Calculate metrics for graphs
        self.calculate_network_metrics()


    def create_connections_graph(self) -> None:
        """
        Creates the connections digraph
        Returns:
            None
        """
        self.debug("Generating connections graph for users...")
        for user in self.users:
            self.G_connections.add_node(user)
            # Add followers
            for follower in user.get_followers():
                self.G_connections.add_edge(follower,user)
            # Add friends
            for friend in user.get_friends():
                self.G_connections.add_edge(user,friend)


    def create_reshares_graph(self) -> None:
        """
        Creates the reshares multidigraph
        Returns:
            None
        """
        self.debug("Generating reshares graph for users...")
        for user in self.users:
            # start by adding the user
            self.G_reshares.add_node(user)
            for reshare in user.get_reshares():
                self.G_reshares.add_edge(user,reshare.original_post.author,
                                         original_post=reshare.original_post,
                                         reshared_post=reshare.reshared_post)

    def create_reshares_di_graph(self) -> None:
        """
        Creates the reshares digraph equivalent
        Returns:
            None
        """
        self.debug("Generating reshares di_graph...")
        for user in self.users:
            self.G_reshares_di.add_node(user)
            for reshare in user.get_reshares():
                source = user
                target = reshare.original_post.author
                # If user shared multiple posts from same target
                # Use same edge and append attribute
                if self.G_reshares_di.has_edge(source,target):
                    self.G_reshares_di[source][target]['reshares'].append(reshare)
                    # Increment weight if multiple reshares
                    self.G_reshares_di[source][target]['weight'] += 1
                else:
                    self.G_reshares_di.add_edge(source,target,reshares=[reshare],weight=1)

    def create_favorites_graph(self) -> None:
        """
        Creates the favorites multidigraph
        Returns:
            None
        """
        self.verbose("Generating favorites graph for users...")
        for user in self.users:
            # Always add to graph first to account for
            # edge case where user has no favorites
            self.G_favorites.add_node(user)
            for favorite in user.get_favorites():
                if user.screen_name == "data6ase" and favorite.author.screen_name == "LilSimSwapper":
                    self.verbose(favorite)
                self.G_favorites.add_edge(user,favorite.author,favorite=favorite)


    def create_favorties_di_graph(self) -> None:
        """
        Creates the favorites digraph equivalent
        Returns:
            None
        """
        self.debug("Generating favorites digraph...")
        for user in self.users:
            self.G_favorites_di.add_node(user)
            for favorite in user.get_favorites():
                source = user
                target = favorite.author
                # User liked multiple posts from same target
                # Store all in attribute list favorites
                # Increment weight
                if self.G_favorites_di.has_edge(source,target):
                    self.G_favorites_di[source][target]['favorites'].append(favorite)
                    self.G_favorites_di[source][target]['weight'] +=1
                else:
                    self.G_favorites_di.add_edge(source,target,favorites=[favorite],weight=1)


    def create_mentions_graph(self) -> None:
        """
        Creates the mentions multidigraph
        Returns:
            None
        """
        self.debug("Generating mentions graph for users...")
        for user in self.users:
            # Always add user first otherwise if user has no mentions
            # they will not get added to the graph
            self.G_mentions.add_node(user)
            for mention in user.get_mentions():
                self.G_mentions.add_edge(user,mention.mentioned,post=mention.post)


    def create_mentions_di_graph(self) -> None:
        """
        Creates the mentions digraph equivalent
        """
        self.debug("Generating mentions digraph...")
        for user in self.users:
            self.G_mentions_di.add_node(user)
            for mention in user.get_mentions():
                source = user
                target = mention.mentioned
                # User mentioned target multiple times
                # Store all relevant posts in list mentions
                # Increment weight
                if self.G_mentions_di.has_edge(source,target):
                    self.G_mentions_di[source][target]['mentions'].append(mention)
                    self.G_mentions_di[source][target]['weight'] += 1
                else:
                    self.G_mentions_di.add_edge(source,target,mentions=[mention],weight=1)

    def create_comments_graph(self) -> None:
        """
        Creates the comments multidigraph
        Returns:
            None
        """
        self.debug("Generating comments graph for users...")
        for user in self.users:
            # Add user node to graph first and formore to ensure
            # edge case is covered
            self.G_comments.add_node(user)
            for comment in user.get_comments():
                post_author = comment.post.author
                self.G_comments.add_edge(user,post_author,comment=comment)

    def create_comments_di_graph(self) -> None:
        """
        Creates the comments digraph equivalent
        Returns:
            None
        """
        self.debug("Generating comments digraph...")
        for user in self.users:
            self.G_comments_di.add_node(user)
            for comment in user.get_comments():
                source = user
                target = comment.post.author
                if self.G_comments_di.has_edge(source,target):
                    # If multiple comments on same post
                    # Append comment and increment weight
                    self.G_comments_di[source][target]['comments'].append(comment)
                    self.G_comments_di[source][target]['weight'] += 1
                else:
                    self.G_comments_di[source][target].add_edge(source,target,comments=[comment],weight=1)

############################# GRAPH GETTERS ########################################################
    def get_graph(self,graph_name: str) -> Union['DiGraph','MultiDiGraph']:
        """
        Getter for graphs based on their name
        Args:
            graph_name (str): name of the graph to get
        Returns:
            A networkX DiGraph or MultiDiGraph with the name graph_name
        """
        graph = getattr(self,f'G_{graph_name}')
        return graph

    def get_di_graph(self,graph_name: str) -> Union['DiGraph']:
        """
        Getter for digraph equivalent of graph with the name graph_name
        Args:
            graph_name (str): name of the graph to get
        Returns:
            A networkX DiGraph with the name graph_name
        """
        if graph_name in 'connections':
            return self.G_connections
        return getattr(self,f'G_{graph_name}_di')

    def get_node(self,username: str) -> 'SocialUser':
        """
        Getter for a node with the username username
        Note: username type is based on source_type
        Args:
            username (str): username of the user node to get
        Returns:
            Social user in the graph with username username
        """
        return self.users_dict[username]

    def get_edges(self,graph_name: str, username1: str,username2: str) -> dict:
        """
        Gets all edges between username1 and username2 in graph with name graph_name
        Args:
            graph_name (str): the name of the graph to get
            username1 (str): username of user1
            username2 (str): username of user2
        Returns:
            Dict of tuples representing edges (source,target,attributes)
        """
        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        graph = self.get_graph(graph_name)
        return graph[user1][user2]

    def get_edges_attr(self,graph_name: str,username1: str,username2: str) -> dict:
        """
        Gets all edge attributes between username1 and username2 in graph with name graph_name
        Args:
            graph_name (str): the name of the graph to get
            username1 (str): username of user1
            username2 (str): username of user2
        Returns:
            Dict of edge attributes
        """
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

############################# ENDOF GETTERS ########################################################
############################ NODE RELATIONSHIP ANALYSIS #############################################
    def follows(self,username1: str,username2: str) -> bool:
        """
        Checks if username1 follows username2
        Returns:
            True if username1 follows username2 and false otherwise
        """
        if nx.is_empty(self.G_connections):
            return False

        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        try:
            path = nx.has_path(self.G_connections,user1,user2)
            if path:
                # only considred followers if there is a direct link btwn users
                direct_path = nx.shortest_path_length(self.G_connections,user1,user2)
                return direct_path == 1
        except nx.NodeNotFound:
            return False


    def reshared(self,username1: str,username2: str):
        """
        Checks if username1 shared a post by username2
        Returns:
            tuple(bool,(original_post,reshared_post)) where bool = True if username shared at least one post from username2
            and False otherwise
        """
        if nx.is_empty(self.G_reshares):
            return False

        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2

        reshared = nx.has_path(self.G_reshares,user1,user2)

        if not reshared:
            return False

        reshared_path_length = nx.shortest_path_length(self.G_reshares,user1,user2)
        if reshared_path_length > 1:
            # indirect reshare
            return False
        posts = []
        reshare_edges = self.G_reshares[user1][user2]
        for key,edge_attr in reshare_edges.items():
            posts.append((edge_attr['original_post'],edge_attr['reshared_post']))

        return (reshared,posts)


    def favored(self,username1: str,username2: str) -> Union[List['SocialPost'],bool]:
        """
        Checks if username1 liked a post by username2
        Returns:
            Lists of posts authored by username2 and liked by username1 and False otherwise
        """
        if nx.is_empty(self.G_favorites):
            return False

        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2

        favored_path = nx.has_path(self.G_favorites,user1,user2)
        if not favored_path:
            return False

        favorite_path_length = nx.shortest_path_length(self.G_favorites,user1,user2)
        if favorite_path_length > 1:
            # indirect favorite
            return False

        # Collect all posts liked by user1 that were authored by user2
        favored_posts = []
        favored_edges = self.G_favorites[user1][user2]
        for key, edge_attr in favored_edges.items():
            favored_posts.append(edge_attr['favorite'])

        return favored_posts

    def mentioned(self,username1: str,username2: str) -> Union[List['Mention'],bool]:
        """
        Checks if username1 liked mentioned username2 in a post
        Returns:
            List of mentions of username2 by username1 and False otherwise
        """
        if nx.is_empty(self.G_mentions):
            return False

        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2

        mentioned = nx.has_path(self.G_mentions,user1,user2)

        if not mentioned:
            return False

        mentioned_path_length = nx.shortest_path_length(self.G_mentions,user1,user2)
        if mentioned_path_length > 1:
            # indirect reshare
            return False

        # Collect all posts in which user1 mentions user2
        mentioned_posts = []
        mentioned_edges = self.G_mentions[user1][user2]
        for key,edge_attr in mentioned_edges.items():
            mentioned_posts.append(edge_attr['post'])
        return mentioned_posts

    def commented(self,username1: str,username2: str) -> Union[List['Comment'],bool]:
        """
        Checks if username1 commented on a post by username2
        Returns:
            List of Comments of username1 on posts by username2 and False otherwise
        """
        if nx.is_empty(self.G_comments):
            return False

        user1 = self.users_dict[username1] if not isinstance(username1, SocialUser) else username1
        user2 = self.users_dict[username2] if not isinstance(username2, SocialUser) else username2
        commented = nx.has_path(self.G_comments,user1,user2)

        if not commented:
            return False

        commented_path_length = nx.shortest_path_length(self.G_comments,user1,user2)
        if commented_path_length > 1:
            # indirect reshare
            return False

        # Collect all posts in which user1 commented on post from user2
        commented_posts = []
        commented_edges = self.G_comments[user1][user2]
        for key,edge_attr in commented_edges.items():
            commented_posts.append(edge_attr['comment'])

        return commented_posts

    def common_friends(self,username1: str,username2: str) -> Union[List['SocialUser'],bool]:
        """
        Checks if username1 and username have a common friend
        Returns:
            List of common friends if username1 and username have any and False otherwise
        """
        if nx.is_empty(self.G_connections):
            return []
        return self.common_out_neighbours(self.G_connections,username1,username2)


    def common_followers(self,username1: str,username2: str) -> Union[List['SocialUser'], bool]:
        """
        Checks if username1 and username have a common followers
        Returns:
            List of common followers if username1 and username have any and False otherwise
        """
        if nx.is_empty(self.G_connections):
            return []
        return self.common_in_neighbours(self.G_connections,username1,username2)

    def common_favorties_nodes(self,username1,username2):
        if nx.is_empty(self.G_favorites):
            return []

        return self.common_out_neighbours(self.G_favorites,username1,username2)


    def common_mentions_nodes(self,username1,username2):
        if nx.is_empty(self.G_mentions):
            return []
        return self.common_out_neighbours(self.G_mentions,username1,username2)


    def common_reshare_nodes(self,username1,username2):
        if nx.is_empty(self.G_reshares):
            return []
        authors = self.common_out_neighbours(self.G_reshares,username1,username2)
        return authors


    def common_comment_nodes(self,username1,username2):
        if nx.is_empty(self.G_comments):
            return []

        return self.common_out_neighbours(self.G_comments,username1,username2)


    def get_all_reshares_from_src(self,username: str,src: str) -> List['Reshare']:
        """
        Gets all posts that username shared from src
        Returns:
            List of Reshares
        """
        user = self.users_dict[username] if not isinstance(username,SocialUser) else username
        src = self.users_dict[src] if not isinstance(src,SocialUser) else src
        # Get all edges from user to src in reshares graph
        edges = self.get_edges_attr("reshares",user,src)
        reshares = []
        for edge,attrs in edges.items():
            reshares.append(Reshare(user,attrs['reshared_post'],attrs['original_post']))
        return reshares


    def get_all_mentions_of_src(self,username: str,src: str) -> Union[List['Mention'],bool]:
        """
        Gets all posts in which username mentions src
        Returns:
            List of Mentions
        """
        user = self.users_dict[username] if not isinstance(username, SocialUser) else username
        src = self.users_dict[src] if not isinstance(src,SocialUser) else src
        # Get all edges from user to src
        edges = self.get_edges_attr("mentions",user,src)
        mentions = []
        for edge,attrs in edges.items():
            mentions.append(Mention(user,src,post=attrs['post']))
        return mentions

    def get_all_favorites_from_src(self,username: str,src: str) -> Union[List['Favorite'],bool]:
        """
        Gets all posts by src that username liked
        Returns:
            List of Favorites
        """
        user = self.users_dict[username] if not isinstance(username, SocialUser) else username
        src = self.users_dict[src] if not isinstance(src,SocialUser) else src
        # Get all edges from user to src
        edges = self.get_edges_attr("favorites",user,src)
        favorites = []
        for edge,attrs in edges.items():
            favorites.append(Favorite(user,src,post=attrs['favorite']))
        return favorites

    def get_all_comments_from_src(self,username: str,src: str) -> Union[List['Comment'],bool]:
        """
        Gets all comments of username on posts by src
        Returns:
            List of Comments
        """
        user = self.users_dict[username] if not isinstance(username, SocialUser) else username
        src = self.users_dict[src] if not isinstance(src,SocialUser) else src
        # Get all edges from user to src
        edges = self.get_edges_attr("comments",user,src)
        comments = []
        for edge,attrs in edges.items():
            comments.append(attrs['comment'])

        return comments

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
        if nx.is_empty(graph):
            return ""

        if not nx.has_path(graph,user1,user2):
            return "NO PATH\n"

        shortest_paths = nx.all_shortest_paths(graph,user1,user2)

        str_repr = ""
        for path in shortest_paths:
            str_repr += "{"
            for i in range(0,len(path)):
                str_repr += f"{path[i]} -> " if i < len(path)-1 else f"{path[i]}"
            str_repr += "}\n"
        return str_repr

############################ ENDOF NODE RELATIONSHIP ANALYSIS #####################################
############################ GRAPH STRUCTURE METRICS ##############################################

    def density(self,graph_name: str) -> float:
        """
        Calculates density of graph with graph_name
        Args:
            graph_name(str): name of the graph for which to calculate density
        Returns:
            density of graph
        """
        graph = self.get_di_graph(graph_name)
        return nx.density(graph)


    def triadic_closure(self,graph_name: str) -> float:
        """
        Calculates triadic closure of graph with graph_name
        Args:
            graph_name(str): name of the graph for which to calculate density
        Returns:
            triadic closure of graph
        """
        graph = self.get_di_graph(graph_name)
        return nx.transitivity(graph)

############################ ENDOF GRAPH STRUCTURE METRICS ##########################################
########################### NETWORK NODE METRICS ####################################################

    def calculate_network_metrics(self):
        for graph_name in ['connections','reshares','mentions','favorites','comments']:
            graph = self.get_di_graph(graph_name)
            self.debug(f"Calculating centrality for {graph_name}")
            self.calculate_centrality(graph)
            self.debug(f"Calculating btwn for {graph_name}")
            self.calculate_betweenness_centrality(graph)
            self.debug(f"Calculating eigen for {graph_name}")
            self.calculate_eigenvector_centrality(graph)

    def calculate_centrality(self,graph):
        degree_centrality = nx.degree_centrality(graph)
        # Add it as node attribute
        for ix,deg in degree_centrality.items():
            graph.nodes[ix]['centrality'] = deg

    def get_centrality(self, graph_name, username):
        """
        Degree centrality: assigns an importance based on the number of links held by each node.
        Tells us how many 'one hop' connections each node has to other nodes in the network
        Useful for finding connected individuals, popular individuals,individuals who are likely
        to hold most info. or individuals who can quickly connect with the wider network
        """
        # If username is defined return that user centrality else whole graph's
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        graph = self.get_di_graph(graph_name)
        return graph.nodes[user]['centrality']

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

    def calculate_closeness(self,graph):
        graph_closeness = nx.closeness_centrality(graph)
        # Add closeness as node attribute
        for ix, clos in graph_closeness.items():
            graph.nodes[ix]['closeness'] = clos


    def get_closeness(self, graph_name: str, username: str) -> float:
        """
         Gets the centrality of node with screen name or id username in graph_name
         Args:
             graph_name (str): name of the graph from which to get the metric
             username (str): id or screen name of the target user
        Returns:
          centrality degree for username
        """
        user = self.users_dict[username] if not isinstance(username,SocialUser) else username
        graph = self.get_di_graph(graph_name)
        return graph.nodes[user]['closeness']

    def calculate_betweenness_centrality(self,graph):
        # Get number of nodes
        node_num = graph.number_of_nodes()
        # use less nodes if number of nodes is higher than 500
        # 50% less ?
        k = int(node_num / 3)
        graph_betweenness = nx.betweenness_centrality(graph, k=k)
        # If called on whole graph save measure as node attribute
        # to be used for visualization
        for ix,btwn in graph_betweenness.items():
            graph.nodes[ix]['betweenness'] = btwn

    def get_betweenness_centrality(self, graph_name: str, username: str) -> float:
        """
         Gets the betweenness centrality of node with screen name or id username in graph_name
         Args:
             graph_name (str): name of the graph from which to get the metric
             username (str): id or screen name of the target user
        Returns:
          betweenness centrality for username
        """
        user = self.users_dict[username] if username and not isinstance(username,SocialUser) else username
        graph = self.get_di_graph(graph_name)
        return graph.nodes[user]['betweenness']

    def calculate_eigenvector_centrality(self,graph):
        try:
            graph_eigen = nx.eigenvector_centrality_numpy(graph)
        except TypeError as t:
            graph_eigen = nx.eigenvector_centrality(graph)
        # If called on whole graph save measure as node attribute
        # to be used for visualization
        for ix, eig in graph_eigen.items():
            graph.nodes[ix]['eigenvector'] = eig

    def get_eigenvector_centrality(self, graph_name: str, username: str) -> float:
        """
         Gets the eigenvector centrality of node with screen name or id username in graph_name
         Args:
             graph_name (str): name of the graph from which to get the metric
             username (str): id or screen name of the target user
        Returns:
          eigenvector centrality for username
        """
        user = self.users_dict[username] if not isinstance(username,SocialUser) else username
        graph = self.get_di_graph(graph_name)
        return graph.nodes[user]['eigenvector']

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

    def get_metric_attributes(self):
        return ['centrality', 'betweenness', 'eigenvector']
    
    def get_top_nodes(self,graph_name: str,metric: str ="centrality", top: int =1) -> dict:
        """
        Args:
            graph_name (str): name of graph
            metric (str): 'centrality', 'betweenness', or 'eigenvector'
            top (int): number of hubs to return
            ie: top = 3: returns top 3 hubs or brokers or influencers
        Returns:
            ordered dict with key = hub and value = degree
        """
        graph = self.get_di_graph(graph_name)
        if nx.is_empty(graph):
            return {}

        valid_metric = any(m in metric for m in self.get_metric_attributes())
        if not valid_metric:
            self.error(f"Invalid metric {metric}, set to: 'centrality', 'betweenness', or 'eigenvector'")

        if top > graph.number_of_nodes():
            self.alert(f"Top exceeds number of nodes in {graph_name}")
            self.alert(f"Setting top to {graph.number_of_nodes()}")
            top = graph.number_of_nodes()

        # graph.nodes(data="centrality") returns [(node,degree)...]
        # Sort nodes of graph by metric (second value in tuple)
        sorted_nodes = sorted(graph.nodes(data=metric),
                              key = lambda x : x[1], reverse=True)
        # Get top x
        top_x_hubs = sorted_nodes[:top]
        # Store in dict
        top_x_hubs_dict = {}
        for hub,deg in top_x_hubs:
            top_x_hubs_dict[hub] = deg
        return top_x_hubs_dict

########################### ENDOF NETWORK METRICS ###############################################
########################### CLUSTERING NETWORK METHODS ##########################################
    def graph_modularity(self,graph_name: str) -> int:
        """
        Community detection using modularity, sets the
        community/group # as node attribute
        Args:
            graph_name (str): name of the graph
        Returns:
            Number of communities found
        """
        # Modularity is not yet implemented for directed graphs
        # need to convert to undirected
        # Note: loss of information when analyzing
        graph = self.get_di_graph(graph_name)
        # Convert to undirected
        undirected_graph = nx.Graph(graph)
        communities = community.greedy_modularity_communities(undirected_graph)
        # Add community number as group
        modularity_dict = {}
        for i, c in enumerate(communities):
            for user in c:
                # Key = user
                # Value = group # they belong to
                modularity_dict[user] = i

        # Add as node attribute
        nx.set_node_attributes(graph,modularity_dict, 'group')
        # Store value for future reference
        self.graph_community_len[graph_name] = len(communities)
        # Return number of communities
        return self.graph_community_len[graph_name]

    def graph_best_partition(self,graph_name: str) -> int:
        """
        Community detection using louvain algorithm
        Args:
            graph_name (str): name of the graph
        Returns:
            None
        """
        graph = self.get_di_graph(graph_name)
        # Convert to undirected
        undirected_graph = nx.Graph(graph)
        communities = louvain_community.best_partition(undirected_graph)

        # Add as node attribute
        nx.set_node_attributes(graph,communities, 'group')
        # Stores the number of communities found in the graph
        self.graph_community_len[graph_name] = max(communities.values())+1
        # Return number of communities
        return self.graph_community_len[graph_name]

    def get_community_metrics(self,graph_name: str, index: int = 0,top: int = 1) -> dict:
        """
        Returns metrics for the community labelled with index
        Args:
            graph_name -> str: name of the graph
            index -> int: index of the community
        Returns:
            list of nodes beloning to the same community
        """
        # Ensure index < community
        if self.graph_community_len[graph_name] < index:
            self.error("Index out of range")


        # Get digraph
        graph = self.get_di_graph(graph_name)
        # Get all nodes which group == index
        community = [n for n in graph.nodes() if graph.nodes[n]['group'] == index]

        # Ensure top <= number of nodes in the community
        if len(community) < top:
            self.alert(f"Top out of range, community length {len(community)}")
            self.alert(f"Setting top to {len(community)}")
            top = len(community)
        # Get community metrics
        community_metrics = {}
        for metric in self.get_metric_attributes():
            # Get metrics for nodes in the community
            community_metric = {n:graph.nodes[n][metric] for n in community}
            # Sorted in descending order (highest to lowest)
            community_metric_sorted = sorted(community_metric.items(), key=itemgetter(1), reverse=True)
            # Store top x nodes with that metric
            community_metrics[metric] = community_metric_sorted[:top]

        self.debug(community_metrics)
        return community_metrics


########################### ENDOF CLUSTERING NETWORK METHODS ####################################
########################### NETWORK EXPORT METHDOS ###############################################

    def export_graph(self,graph_name: str) -> tuple:
        """
        Exports graph into a list of nodes and edges
        Args:
            graph_name (str): name of graph to export
        Returns:
            Tuple with list of nodes and list of links (nodes,links(
        """
        # pos = nx.spring_layout(graph)
        # nx.draw_networkx(graph, pos)
        # nx.draw_networkx_edge_labels(graph, pos)
        # plt.show()
        data = (0,0)
        if graph_name in 'connections':
            data = self.serialize_connections_graph()

        elif graph_name in 'reshares':
            data = self.serialize_reshares_graph()

        elif graph_name in 'mentions':
            data = self.serialize_mentions_graph()

        elif graph_name in 'favorites':
            data = self.serialize_favorites_graph()
        elif graph_name in 'comments':
            data = self.serialize_comments_graph()
        else:
            self.error(f"Graph {graph_name} does not exist")

        return data

    def serialize_connections_graph(self):
        """
        Serialize to JSON the connections graph
        Given nodes and edges store custom object default serialization
        does not work
        """
        if nx.is_empty(self.G_connections):
            return

        nodes = []
        nodes_index = {}
        i = 0
        for user in self.G_connections.nodes():
            # Note: groups are used for coloring in D3
            node_dict = {'betweenness':self.G_connections.nodes[user]['betweenness'],
                         'degree': self.G_connections.nodes[user]['centrality'],
                         'eigenvector': self.G_connections.nodes[user]['eigenvector'],
                         'group': self.G_connections.nodes[user]['group'],
                         'id': user.id,
                         'name':user.screen_name,

                         }
            nodes.append(node_dict)

            #Update with index
            nodes_index[user] = i
            i += 1

        links = []
        for users in self.G_connections.edges():
            # each edge will be: {source: index of user 0, target: index of user 1}
            edge_dict = {'source':nodes_index[users[0]], 'target': nodes_index[users[1]],
                         'weight':1}
            links.append(edge_dict)
        return (nodes,links)

    def serialize_reshares_graph(self):
        if nx.is_empty(self.G_reshares):
            return

        # Serialize the nodes
        nodes = []
        nodes_index = {}
        i = 0
        for user in self.G_reshares.nodes():
            node_dict = {'name':user.screen_name,'id':user.id, 'group':self.G_reshares_di.nodes[user]['group'],
                         'degree':self.G_reshares_di.nodes[user]['centrality'],
                         'betweenness':self.G_reshares_di.nodes[user]['betweenness'],
                         'eigenvector':self.G_reshares_di.nodes[user]['eigenvector']
                         }
            nodes.append(node_dict)

            #Update with index
            nodes_index[user] = i
            i += 1

        # Serialize the edges
        links = []
        for users in self.G_reshares.edges(data=True):
            edge_dict = {'source':nodes_index[users[0]], 'target': nodes_index[users[1]],
                         'original_post_id':users[2]['original_post'].post_id,
                         'original_post_text':users[2]['original_post'].text,
                         'reshared_post_id':users[2]['reshared_post'].post_id,
                         'reshared_post_text':users[2]['reshared_post'].text,
                         'weight':self.G_reshares_di[users[0]][users[1]]['weight']}
            links.append(edge_dict)
        return (nodes,links)

    def serialize_mentions_graph(self):
        if nx.is_empty(self.G_mentions):
            return

        # Serialize the nodes
        nodes = []
        nodes_index = {}
        i = 0
        for user in self.G_mentions.nodes():
            node_dict = {'name':user.screen_name,'id':user.id,'group':self.G_mentions_di.nodes[user]['group'],
                         'degree': self.G_mentions_di.nodes[user]['centrality'],
                         'betweenness': self.G_mentions_di.nodes[user]['betweenness'],
                         'eigenvector': self.G_mentions_di.nodes[user]['eigenvector']
                         }
            nodes.append(node_dict)

            #Update with index
            nodes_index[user] = i
            i += 1

        # Serialize the edges
        links = []
        for users in self.G_mentions.edges(data=True):
            edge_dict = {'source':nodes_index[users[0]], 'target': nodes_index[users[1]],
                         'post_id':users[2]['post'].post_id,
                         'post_text':users[2]['post'].text,
                         'weight':self.G_mentions_di[users[0]][users[1]]['weight']}
            links.append(edge_dict)
        return (nodes,links)

    def serialize_favorites_graph(self):
        if nx.is_empty(self.G_favorites):
            return
        # Serialize the nodes
        nodes = []
        nodes_index = {}
        i = 0
        for user in self.G_favorites.nodes():
            node_dict = {'name':user.screen_name,'id':user.id, 'group':self.G_favorites_di.nodes[user]['group'],
                         'degree': self.G_favorites_di.nodes[user]['centrality'],
                         'betweenness': self.G_favorites_di.nodes[user]['betweenness'],
                         'eigenvector': self.G_favorites_di.nodes[user]['eigenvector']
                         }
            node_dict['group'] = 0 if user in self.users else node_dict['group']
            nodes.append(node_dict)

            #Update with index
            nodes_index[user] = i
            i += 1

        # Serialize the edges
        links = []
        for users in self.G_favorites.edges(data=True):
            edge_dict = {'source':nodes_index[users[0]], 'target': nodes_index[users[1]],
                         'post_id':users[2]['favorite'].post_id,
                         'post_text':users[2]['favorite'].text,
                         'weight':self.G_favorites_di[users[0]][users[1]]['weight']}
            links.append(edge_dict)

        return (nodes,links)

    def serialize_comments_graph(self):
        if nx.is_empty(self.G_comments):
            return
        # Serialize the nodes
        nodes = []
        nodes_index = {}
        i = 0
        for user in self.G_comments.nodes():
            node_dict = {'name':user.screen_name,'id':user.id,'group':self.G_comments_di.nodes[user]['group'],
                         'degree': self.G_comments_di.nodes[user]['centrality'],
                         'betweenness': self.G_comments_di.nodes[user]['betweenness'],
                         'eigenvector': self.G_comments_di.nodes[user]['eigenvector']
                         }
            nodes.append(node_dict)
            #Update with index
            nodes_index[user] = i
            i += 1

        # Serialize the edges
        links = []
        for users in self.G_comments.edges(data=True):
            edge_dict = {'source': nodes_index[users[0]], 'target': nodes_index[users[1]],
                             'post_id': users[2]['comment'].post.post_id,
                             'post_text': users[2]['comment'].post.text,
                             'comment': users[2]['comment'].text,
                             'weight':self.G_comments_di[users[0]][users[1]]['weight']}
            links.append(edge_dict)

        return (nodes,links)

########################### ENDOF NETWORK EXPORT METHDOS #################################
############################ HELPER METHODS  #############################################

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


    def get_all_measures(self,graph_name,username):
        metrics = {}
        metrics['centrality'] = self.get_centrality(graph_name, username)
        metrics['betweenness_centrality'] = self.get_betweenness_centrality(graph_name, username)
        metrics['eigenvector_centrality'] = self.get_eigenvector_centrality(graph_name,username)
        return metrics

############################ ENDOF HELPER METHODS  #############################################


