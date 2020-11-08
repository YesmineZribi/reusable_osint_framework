from recon.core import framework
from recon.mixins.social_user import SocialUser

import networkx as nx
import matplotlib.pyplot as plt


class SocialGraph(framework.Framework):

    def __init__(self,source_type,usernames):
        framework.Framework.__init__(self,'social_graph')

        #Initialize empty graphs
        self.G_connections = nx.DiGraph()
        self.G_reshares = nx.DiGraph()
        self.G_favorites = nx.DiGraph()
        self.G_mentions = nx.DiGraph()

        #For each user create its object, call its get_all (multithread eventually)?
        self.users = [] #SocialUser[]
        for username in usernames:
            user = SocialUser(**{source_type:username})
            user.get_all()
            self.users.append(user)



    def add_edge(self, graph, node1,node2,key,value):
        """
        Populate graph with edge node1 -> node2 with label key:value
        """
        pass
