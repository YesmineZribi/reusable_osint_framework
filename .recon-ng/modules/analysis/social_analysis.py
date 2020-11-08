# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.social_user import SocialUser
#from recon.mixins.social_post import SocialPost
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
            ('nameserver', '8.8.8.8', 'yes', 'ip address of a valid nameserver'),
        ),
    }


    def module_pre(self):
        user1 = SocialUser(screen_name="Jasmine52468952")
        print(user1.get_followers())
        print()
        print(user1.get_friends())
        print()
        print(user1.get_timeline())
        print()
        print(user1.get_reshares())
        print()
        print(user1.get_mentions())




    def module_run(self):

        pass

    def module_thread(self, host, url, headers):
        pass
