# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.social_user import SocialUser
from recon.mixins.social_graph import SocialGraph
# module specific imports
import os

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
        ),
        'options': (
            ('usernames', '', True, 'Set to list of users to analyse relationship between'),
            ('source_type', 'id', True,'Set the type of the source: user_id or screen_name or id'),
        ),
    }


    def module_pre(self):
        #Process user1, user2,...usern id or screen_name
        #Ensure source_type is valid and usernames are valid
        #Split them and convert to ints if necessary or remove the @

        pass




    def module_run(self):
        #For each uses:
        #Open subprocess, fetch info and populate db
        #Call create_graphs mixin with (user1,user2,...usern)
        #Call analysis methods
        usernames = self.options['usernames'].split(',')
        print(self.options['usernames'])
        graph = SocialGraph(self.options['source_type'],usernames)

    def module_thread(self, host, url, headers):
        #Create user call from the username
        #Create graphs
        pass

    #Visualize graph method

    #Analyze graph method

    #Generate report: generate txt + output in command line
