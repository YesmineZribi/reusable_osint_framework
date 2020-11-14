# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.social_user import SocialUser
from recon.mixins.social_graph import SocialGraph
# module specific imports
import os
from itertools import combinations
import subprocess

class Module(BaseModule):

    meta = {
        'name': 'Hostname Resolver',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Resolves IP addresses to hosts and updates the database with the results.',
        'dependencies': ['NetworkX'],
        'files': [],
        'required_keys': [],
        'comments': (
            'This module needs matplotlib running on your Linux machine to visualize graphs',
            'ie: sudo apt-get install python3-matplotlib',
            'Then run: sudo apt-get install tcl-dev tk-dev python-tk python3-tk',
            'Some social media platform consider a reshared post a mention of the original post author',
            'such as Twitter which appends an RT @mention to each retweet making a retweet also a mention',
        ),
        'options': (
            ('usernames', '', True, 'Set to list of users to analyse relationship between'),
            ('source_type', 'id', True,'Set the type of the source: user_id or screen_name or id'),
            ('recon_module','twitter_user',True,'Set to the name of the recon module to use (must already be installed)'),
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
        # self.fetch_bulk_account_info()

        #Create graphs
        self.graphs = SocialGraph(self.options['source_type'],self.handles)


    def module_run(self):
        #Create User report class for each user
        #Store measures for that user
        connec_graph = self.graphs.get_graph("connections")
        network = self.graphs.get_successors(connec_graph,self.handles[0])
        # print(self.graphs.closeness(connec_graph,network[3]))
        print(self.graphs.eigenvector_centrality(connec_graph))
        # Get metrics for each users
        # Perform analysis for each pair
        # Identify nodes with highest metrics




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

        # Get all pair combinations from the list of users given - needed later
        self.all_pairs = list(combinations(self.handles,2))




    #Analyze graph method

    def connection_analysis(self):
        # Is there a path from
        pass

    #Generate report: generate txt + output in command line


    def module_thread(self, host, url, headers):
        #Create user call from the username
        #Create graphs
        pass
