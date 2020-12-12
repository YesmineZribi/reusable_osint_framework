from recon.core import framework


class GraphReport(framework.Framework):

    def __init__(self,graph_name):

        self.graph_name = graph_name

        # Variables for graph structure info
        self.density = None
        self.triadic_closure = None

        # Stores top x nodes with highest degree
        self.hubs = {}
        # Stores top x nodes with highest betweenness
        self.brokers = {}
        # Stores top x nodes with highest eigenvector centr.
        self.influencers = {}

        # index = community number
        # value (dict) = metrics for that community
        # value = {metric: list of tuples} whehre each tuple
        # is (node, its metric value)
        self.communities = []

    def set_density(self,density):
        self.density = density

    def set_triadic_closure(self,triadic_closure):
        self.triadic_closure = triadic_closure

    def set_hubs(self,hubs):
        self.hubs = hubs

    def add_hub(self,hub,degree):
        self.hubs[hub] = degree

    def set_brokers(self,brokers):
        self.brokers = brokers

    def add_broker(self,broker,betweenness):
        self.brokers[broker] = betweenness

    def set_influencers(self,influencers):
        self.influencers = influencers

    def add_influencer(self,influencer,eigenvector):
        self.influencers[influencer] = eigenvector

    def add_community_metrics(self,metrics):
        self.communities.append(metrics)

    def metric_format(self):
        """
        String formatter for graph metrics
        Returns:
            String format for graph metrics
        """
        string_rep = "Graph Metrics:\n"
        string_rep += f"\tDensity: {self.density}\n"
        string_rep += f"\tTriadic Closure: {self.triadic_closure}\n"
        return string_rep

    def important_nodes_format(self):
        """
        String formatter for important nodes
        Returns:
            String format for important nodes
        """
        string_rep = "Important nodes identified: \n"
        string_rep += "Hubs (nodes with most connections) :\n"
        # Format hubs
        for hub,degree in self.hubs.items():
            string_rep += f"\t{hub}: {degree}\n"

        # Format brokers
        string_rep += "Brokers (nodes with most control)\n"
        for broker,btwn in self.brokers.items():
            string_rep += f"\t{broker}: {btwn}\n"

        # Format influencers
        string_rep += "Influencers (nodes with most influence)\n"
        for influencer,eigen in self.influencers.items():
            string_rep += f"\t{influencer}: {eigen}\n"

        return string_rep

    def community_format(self, community, index):
        """
        String formatter for an individual community
        Args:
            community (dict): community to format
            keys = metric
            Values = list of (node,metric)
        Returns:
            String representation of the community
        """
        string_rep = f"\tcommunity_{index}\n"

        for metric, lst in community.items():
            if metric == "centrality":
                string_rep += "\t\tHubs: \n"
            elif metric == "betweenness":
                string_rep += "\t\tBrokers: \n"
            elif metric == "eigenvector":
                string_rep += "\t\tInfluencers: \n"
            for node,value in lst:
                string_rep += f"\t\t{node}: {value}\n"
            string_rep += "\n"
        return string_rep

    def communities_format(self):
        """
        String formatter for communities/clusters, shows
        metrics for each community
        Returns:
            String format for graph communities metrics
        """
        string_rep = "Graph communities:\n"
        for i,community in enumerate(self.communities):
            string_rep += self.community_format(community,i)
            string_rep += "\n"

        return string_rep


    def __repr__(self):
        string_rep = f"{self.graph_name} graph:\n"
        string_rep += self.metric_format()
        string_rep += ""
        string_rep += self.important_nodes_format()
        string_rep += ""
        string_rep += self.communities_format()
        string_rep += "\n\n"
        return string_rep

