# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
# module specific imports
import tweepy
import os, sys
import json
import time
from datetime import datetime


class Module(BaseModule):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions

    meta = {
        'name': 'Twitter User Recon',
        'author': 'Yesmine Zribi',
        'version': '1.0',
        'description': 'Collect recon about a twitter user: their information, followers, friends, or timeline',
        'dependencies': ['tweepy'],
        'required_keys': ['twitter_api', 'twitter_secret'],
        'comments': (
            'Add any user you want to run recon on in the profiles table through the db insert profiles command',
            'Set usource type to user_id to run the source(s) as a user_id. Recommended if need to disambiguate when a valid user ID is also a valid screen name.',
            'Set source type to screen_name to run the source(s) as a screen_name. Recommended if need to disambiguate when a valid user ID is also a valid screen name.',
            'Set source type to id to run as either (user_id/screen_name)',
            'Can only fetch the 20 most recent statuses of a user',
            'Twitter limits api calls to 15/15 min window',

        ),
        'query': "SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL AND resource LIKE 'Twitter' COLLATE NOCASE",
        'options': (
            ('user_info', True, False, 'Set to true to enable collection of user account info'),
            ('user_followers', False, False, 'Set to true to enable collection of user followers'),
            ('user_friends', False, False, 'Set to true to enable collection of user friends'),
            ('user_timeline', False, False, 'Set to true to enable collection of user timeline'),
            ('source_type', 'id', True, 'Set the type of the source: user_id or screen_name or id'),
            ('sleep_time', 2, False, 'Set how much time to sleep if rate limit is reached, default is 2 minutes, max is 15'),
            ('cursor', -1, False, 'Breaks result into pages, -1 to start from first page'),
            ('count', 200, False, 'The number of results to try and retrive per page. Default is 200 (not applicable to user info)'),
            ('skip_status', False, False, 'Boolean indicating whether statuses will not be included in the returned objects. Default to false'),
            ('include_user_entities', True, False, 'User object entities node will not be included when set to false. Defaults to true'),
        ),
    }


    def module_pre(self):
        # Authentication
        auth = tweepy.AppAuthHandler(self.get_key('twitter_api'), self.get_key('twitter_secret'))
        self.api = tweepy.API(auth)

        #Build result directory structure
        root_path = os.path.dirname(os.path.abspath(sys.path[0])) #Get the root directory
        self.twitter_recon_path = os.path.join(root_path,'twitter_recon') #directory to store collected data
        if not os.path.exists(self.twitter_recon_path):
            os.makedirs(self.twitter_recon_path,mode=0o777)
        self.users_path = os.path.join(self.twitter_recon_path, 'users') #directory to store data collected about twitter users
        if not os.path.exists(self.users_path):
            os.makedirs(self.users_path,mode=0o777)


        #Check if user set source_type to legal string
        if self.options['source_type'] not in ['id','user_id','screen_name']:
            self.error('Illegal source type pick either id, user_id or screen_name')

        #Check if user set sleep_time correctly
        if not(isinstance(self.options['sleep_time'],int)) and not(isinstance(self.options['sleep_time'],float)):
            self.error('Illegal value for sleep_time (floats or ints only)')

        #Check if cursor and counts are ints
        for key in ['cursor','count']:
            if not(isinstance(self.options[key],int)):
                self.error(f'Illegal value for {key} (ints only)')

        return self.api

    def module_run(self, handles, api):
        # user = api.get_user(self.options['screen_name'])
        # user_info = user.parse(api,user._json)
        # print(user_info)
        for handle in handles:
            handle = handle if isinstance(handle, int) or not(handle.startswith('@')) else handle[1:]
            #create specific user directory <user>_<date>
            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            user_path = os.path.join(self.users_path, f'{str(handle)}_{dt_string}')
            os.makedirs(user_path,mode=0o777)
            fetched_data = {}
            #fetch info enabled by user
            for key in ['user_info', 'user_followers', 'user_friends', 'user_timeline']:
                if self.options[key]:
                    fetch_to_call = getattr(self, f'fetch_{key}')
                    fetched_data[key] = fetch_to_call(handle,user_path) #Call the right method based on the options set by the user

            print(fetched_data)


    # optional method
    # Use to parse the data objects returned from any helper methods for some useful work
    def module_thread(self, data_object):
        # never catch KeyboardInterrupt exceptions in the "module_thread" method as threads don't see them
        # do something leveraging the api methods discussed below
        pass

# -- Helper methods --
    def fetch_user_info(self,username, user_path):
        try:
            #Fetch the info using the api
            results = self.api.get_user(**{self.options['source_type']:username})
            #Create the file in which to dump the results
            user_info_file = os.path.join(user_path,'info.json')
            with open(user_info_file,'w') as file:
                file.write(json.dumps(results._json, indent=3, sort_keys=True)) #write the json result in a file
            return results._json
        except tweepy.RateLimitError:
            self.alert(f'Rate limit reached, sleeping for {sleep_time} minutes') #report limit reached
            time.sleep(sleep_time*60)


    def fetch_user_followers(self,username, user_path):
        #Create the file in which to dump the results
        user_followers_file = os.path.join(user_path,'followers.json')
        result = []
        self.verbose(f'Retrieving followers for {username}...')
        for follower in self.limit_handled(tweepy.Cursor(self.api.followers,**{self.options['source_type']:username},cursor=self.options['cursor'],
        count=self.options['count'],skip_status=self.options['skip_status'], include_user_entities=self.options['include_user_entities']).items()):
            result.append(follower._json) #Append results of each page

        with open(user_followers_file,'w') as file:
            file.write(json.dumps(result, indent=3,sort_keys=True)) #write the json result in a file

    def fetch_user_friends(self,username, user_path):
        #Create the file in which to dump the results
        user_friends_file = os.path.join(user_path,'friends.json')
        result = []
        self.verbose(f'Retrieving friends of {username}...')
        for friend in self.limit_handled(tweepy.Cursor(self.api.friends,**{self.options['source_type']:username},cursor=self.options['cursor'],
        count=self.options['count'],skip_status=self.options['skip_status'], include_user_entities=self.options['include_user_entities']).items()):
            result.append(friend._json) #Append results of each page

        with open(user_friends_file,'w') as file:
            file.write(json.dumps(result, indent=3,sort_keys=True)) #write the json result in a file

    def fetch_user_timeline(self,username, user_path):
        #Create the file in which to dump the results
        user_timeline_file = os.path.join(user_path,'timeline.json')
        result = []
        self.verbose(f'Retrieving timeline of {username}...')
        for status in self.limit_handled(tweepy.Cursor(self.api.user_timeline,**{self.options['source_type']:username}, count=self.options['count']).items()):
            result.append(status._json) #Append results of each page

        with open(user_timeline_file,'w') as file:
            file.write(json.dumps(result, indent=3,sort_keys=True)) #write the json result in a file

    def limit_handled(self,cursor):
        while True:
            try:
                yield cursor.next()
            except tweepy.RateLimitError:
                self.alert(f'Rate limit reached, sleeping for {sleep_time} minutes') #report limit reached
                time.sleep(self.options['sleep_time'] * 60)
            except StopIteration:
                return
